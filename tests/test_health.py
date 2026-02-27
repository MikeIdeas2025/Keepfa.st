"""Tests for CustomerHealthAnalyzer."""

from keepfast.intelligence.health import CustomerHealthAnalyzer
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


class TestHealthScoreCalculation:
    def test_healthy_user(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="alice@test.com", stripe_id="cus_1")]
        events = [
            _event("u1", "click", "2026-02-25T10:00:00Z"),
            _event("u1", "click", "2026-02-26T10:00:00Z"),
            _event("u1", "click", "2026-02-27T10:00:00Z"),
        ]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, subs)

        assert len(result["customers"]) == 1
        c = result["customers"][0]
        assert c["health_score"] > 50
        assert c["risk_level"] == "healthy"
        assert c["email"] == "alice@test.com"

    def test_critical_user_no_events(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="bob@test.com")]
        events = []
        subs = []

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, subs)

        c = result["customers"][0]
        assert c["health_score"] < 40
        assert c["risk_level"] == "critical"

    def test_at_risk_user(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="charlie@test.com", stripe_id="cus_1")]
        events = [_event("u1", "click", "2026-01-15T10:00:00Z")]  # old event
        subs = [_sub("u1", "sub_1", "active", 1000, "2025-12-01T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, subs)

        c = result["customers"][0]
        # Should be at_risk or critical due to low recency
        assert c["risk_level"] in ("at_risk", "critical")


class TestRiskLevelThresholds:
    def test_healthy_threshold(self):
        analyzer = CustomerHealthAnalyzer()
        assert analyzer._risk_level(71) == "healthy"
        assert analyzer._risk_level(100) == "healthy"

    def test_at_risk_threshold(self):
        analyzer = CustomerHealthAnalyzer()
        assert analyzer._risk_level(70) == "at_risk"
        assert analyzer._risk_level(40) == "at_risk"

    def test_critical_threshold(self):
        analyzer = CustomerHealthAnalyzer()
        assert analyzer._risk_level(39) == "critical"
        assert analyzer._risk_level(0) == "critical"


class TestRiskFactors:
    def test_no_events_factor(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, [], [])

        factors = result["customers"][0]["risk_factors"]
        assert "No events recorded" in factors

    def test_no_subscription_factor(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        events = [_event("u1", "click", "2026-02-27T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, [])

        factors = result["customers"][0]["risk_factors"]
        assert "No active subscription" in factors


class TestHealthSummary:
    def test_summary_aggregation(self):
        users = [
            _user("u1", "2025-12-01T10:00:00Z", email="a@t.com", stripe_id="cus_1"),
            _user("u2", "2025-12-01T10:00:00Z", email="b@t.com"),
            _user("u3", "2025-12-01T10:00:00Z", email="c@t.com"),
        ]
        events = [
            _event("u1", "click", "2026-02-27T10:00:00Z"),
            _event("u1", "click", "2026-02-26T10:00:00Z"),
        ]
        subs = [_sub("u1", "sub_1", "active", 5000, "2025-12-01T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, subs)

        summary = result["summary"]
        assert summary["total"] == 3
        assert summary["healthy"] + summary["at_risk"] + summary["critical"] == 3

    def test_mrr_at_risk_calculation(self):
        users = [
            _user("u1", "2025-12-01T10:00:00Z", email="a@t.com", stripe_id="cus_1"),
            _user("u2", "2025-12-01T10:00:00Z", email="b@t.com", stripe_id="cus_2"),
        ]
        events = []  # no events -> all critical
        subs = [
            _sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z"),
            _sub("u2", "sub_2", "active", 4900, "2025-12-01T10:00:00Z"),
        ]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, subs)

        assert result["summary"]["total_mrr_at_risk"] == 7800  # 2900 + 4900


class TestHealthZeroData:
    def test_empty_users(self):
        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose([], [], [])

        assert result["customers"] == []
        assert result["summary"]["total"] == 0
        assert result["confidence"] == "low"

    def test_zero_subscriptions(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        events = [_event("u1", "click", "2026-02-27T10:00:00Z")]

        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, events, [])

        c = result["customers"][0]
        assert c["monetary_score"] == 0


class TestHealthConfidence:
    def test_low_confidence(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(5)]
        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, [], [])
        assert result["confidence"] == "low"

    def test_medium_confidence(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(50)]
        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, [], [])
        assert result["confidence"] == "medium"

    def test_high_confidence(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(101)]
        analyzer = CustomerHealthAnalyzer()
        result = analyzer.diagnose(users, [], [])
        assert result["confidence"] == "high"
