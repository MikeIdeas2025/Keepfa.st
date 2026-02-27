"""Tests for CLVAnalyzer."""

from keepfast.intelligence.clv import CLVAnalyzer
from keepfast.normalizer.schema import SubscriptionInfo, UnifiedEvent, UnifiedUser


def _user(uid, first_seen, email="", stripe_id=None):
    return UnifiedUser(
        internal_id=uid,
        email=email,
        posthog_distinct_id=uid,
        stripe_customer_id=stripe_id,
        first_seen=first_seen,
        last_seen=first_seen,
        is_matched=stripe_id is not None,
    )


def _event(uid, name, timestamp):
    return UnifiedEvent(
        user_id=uid,
        event_name=name,
        original_name=name,
        timestamp=timestamp,
        source="posthog",
    )


def _sub(uid, sub_id, status, mrr, started, canceled=None):
    return SubscriptionInfo(
        user_id=uid,
        stripe_subscription_id=sub_id,
        status=status,
        plan_name="Pro",
        mrr_cents=mrr,
        started_at=started,
        canceled_at=canceled,
    )


class TestCLVFormula:
    def test_basic_clv(self):
        analyzer = CLVAnalyzer()
        # margin=20, retention=0.8, discount=0.1
        # CLV = (20 * 0.8) / (1 + 0.1 - 0.8) = 16 / 0.3 = 53.33
        clv = analyzer._calculate_clv(margin=20, retention=0.8, discount=0.1)
        assert abs(clv - 53.33) < 0.1

    def test_zero_margin(self):
        analyzer = CLVAnalyzer()
        clv = analyzer._calculate_clv(margin=0, retention=0.8, discount=0.1)
        assert clv == 0

    def test_high_retention_caps(self):
        analyzer = CLVAnalyzer()
        # retention > 1+discount → denominator would be <= 0
        clv = analyzer._calculate_clv(margin=10, retention=1.2, discount=0.1)
        assert clv == 10 * 120  # capped

    def test_discount_rate_affects_clv(self):
        analyzer = CLVAnalyzer()
        clv_low_discount = analyzer._calculate_clv(margin=20, retention=0.8, discount=0.05)
        clv_high_discount = analyzer._calculate_clv(margin=20, retention=0.8, discount=0.2)
        assert clv_low_discount > clv_high_discount


class TestKumarSegments:
    def test_champions_high_clv_high_engagement(self):
        users = [_user("u1", "2025-10-01T10:00:00Z", email="a@t.com", stripe_id="cus_1")]
        events = [
            _event("u1", f"action_{i}", f"2025-{10 + i // 10}-%02dT10:00:00Z" % ((i % 28) + 1))
            for i in range(20)
        ]
        subs = [_sub("u1", "sub_1", "active", 9900, "2025-10-01T10:00:00Z")]

        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, events, subs)

        c = result["customers"][0]
        # Single user is always in top quartile
        assert c["segment"] in ("Champions", "Advocates")

    def test_misers_low_clv(self):
        users = [
            _user("u1", "2025-12-01T10:00:00Z", email="a@t.com", stripe_id="cus_1"),
            _user("u2", "2025-12-01T10:00:00Z", email="b@t.com", stripe_id="cus_2"),
            _user("u3", "2025-12-01T10:00:00Z", email="c@t.com"),  # no sub
        ]
        events = [_event("u3", "click", "2026-02-27T10:00:00Z")]
        subs = [
            _sub("u1", "sub_1", "active", 9900, "2025-12-01T10:00:00Z"),
            _sub("u2", "sub_2", "active", 4900, "2025-12-01T10:00:00Z"),
        ]

        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, events, subs)

        # User without subscription should be Misers (low CLV)
        u3 = next(c for c in result["customers"] if c["email"] == "c@t.com")
        assert u3["segment"] == "Misers"

    def test_all_segments_in_output(self):
        analyzer = CLVAnalyzer()
        result = analyzer.analyze([], [], [])
        for seg in ["Champions", "Advocates", "Affluents", "Misers"]:
            assert seg in result["segments"]


class TestLoyaltyPlan:
    def test_plan_has_five_steps(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com", stripe_id="cus_1")]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z")]

        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, [], subs)

        assert len(result["loyalty_plan"]) == 5
        assert all(step.startswith("Step") for step in result["loyalty_plan"])


class TestCLVZeroData:
    def test_empty_users(self):
        analyzer = CLVAnalyzer()
        result = analyzer.analyze([], [], [])

        assert result["customers"] == []
        assert result["total_portfolio_clv"] == 0
        assert result["confidence"] == "low"

    def test_zero_subscriptions_clv_zero(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [_event("u1", "click", "2026-02-27T10:00:00Z")]

        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, events, [])

        c = result["customers"][0]
        assert c["clv"] == 0
        assert c["mrr"] == 0


class TestCLVDiscountRate:
    def test_custom_discount_rate(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com", stripe_id="cus_1")]
        events = [_event("u1", "click", "2026-02-27T10:00:00Z")]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z")]

        analyzer = CLVAnalyzer()
        result_low = analyzer.analyze(users, events, subs, discount_rate=0.05)
        result_high = analyzer.analyze(users, events, subs, discount_rate=0.3)

        assert result_low["customers"][0]["clv"] > result_high["customers"][0]["clv"]


class TestCLVConfidence:
    def test_low_confidence(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(5)]
        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, [], [])
        assert result["confidence"] == "low"

    def test_medium_confidence(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(50)]
        analyzer = CLVAnalyzer()
        result = analyzer.analyze(users, [], [])
        assert result["confidence"] == "medium"
