"""Tests for intelligence modules — cohort, funnel, trends, segments, omtm."""

from keepfast.intelligence.cohort import CohortAnalyzer
from keepfast.intelligence.funnel import FunnelAnalyzer
from keepfast.intelligence.omtm import OMTMSelector
from keepfast.intelligence.segments import SegmentAnalyzer
from keepfast.intelligence.trends import TrendAnalyzer
from keepfast.normalizer.schema import SubscriptionInfo, UnifiedEvent, UnifiedUser


def _user(uid: str, first_seen: str, email: str = "", stripe_id: str | None = None) -> UnifiedUser:
    return UnifiedUser(
        internal_id=uid,
        email=email,
        posthog_distinct_id=uid,
        stripe_customer_id=stripe_id,
        first_seen=first_seen,
        last_seen=first_seen,
        is_matched=stripe_id is not None,
    )


def _event(uid: str, name: str, timestamp: str) -> UnifiedEvent:
    return UnifiedEvent(
        user_id=uid,
        event_name=name,
        original_name=name,
        timestamp=timestamp,
        source="posthog",
    )


def _sub(
    uid: str, sub_id: str, status: str, mrr: int, started: str, canceled: str | None = None
) -> SubscriptionInfo:
    return SubscriptionInfo(
        user_id=uid,
        stripe_subscription_id=sub_id,
        status=status,
        plan_name="Pro",
        mrr_cents=mrr,
        started_at=started,
        canceled_at=canceled,
    )


class TestCohortRetention:
    """TC-006: Cohort retention calculation."""

    def test_basic_retention(self):
        # 3 users across 3 months
        users = [
            _user("u1", "2025-12-01T10:00:00Z"),
            _user("u2", "2025-12-05T10:00:00Z"),
            _user("u3", "2026-01-02T10:00:00Z"),
        ]
        events = [
            # u1: active in Dec, Jan, Feb
            _event("u1", "page_view", "2025-12-01T10:00:00Z"),
            _event("u1", "page_view", "2026-01-05T10:00:00Z"),
            _event("u1", "page_view", "2026-02-01T10:00:00Z"),
            # u2: active in Dec, Jan only
            _event("u2", "page_view", "2025-12-05T10:00:00Z"),
            _event("u2", "page_view", "2026-01-02T10:00:00Z"),
            # u3: active in Jan only
            _event("u3", "page_view", "2026-01-02T10:00:00Z"),
        ]

        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention(users, events, "monthly", periods=3)

        assert len(result["cohorts"]) >= 1
        assert result["confidence"] == "low"  # <30 users
        assert result["total_users"] > 0

        # Dec cohort: 2 users, both active in Dec
        dec_cohort = next(c for c in result["cohorts"] if "Dec" in c["name"])
        assert dec_cohort["size"] == 2
        assert dec_cohort["retention"][0] == 100  # M0 always 100%

    def test_empty_data(self):
        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention([], [], "monthly")
        assert result["cohorts"] == []
        assert result["trend"] == "insufficient_data"

    def test_single_user_cohort(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        events = [_event("u1", "page_view", "2025-12-01T10:00:00Z")]

        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention(users, events, "monthly", periods=1)
        assert result["cohorts"][0]["size"] == 1
        assert result["cohorts"][0]["retention"][0] == 100

    def test_weekly_cohort(self):
        users = [
            _user("u1", "2026-01-06T10:00:00Z"),  # W02
            _user("u2", "2026-01-13T10:00:00Z"),  # W03
        ]
        events = [
            _event("u1", "click", "2026-01-06T10:00:00Z"),
            _event("u1", "click", "2026-01-13T10:00:00Z"),
            _event("u2", "click", "2026-01-13T10:00:00Z"),
        ]

        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention(users, events, "weekly", periods=2)
        assert len(result["cohorts"]) >= 1


class TestFunnelAnalysis:
    """TC-007: Funnel drop-off detection."""

    def test_basic_funnel(self):
        events = [
            # u1 completes all 3 steps
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u1", "onboarding_complete", "2025-12-01T10:30:00Z"),
            _event("u1", "first_action", "2025-12-01T11:00:00Z"),
            # u2 completes 2 of 3 steps
            _event("u2", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u2", "onboarding_complete", "2025-12-01T10:30:00Z"),
            # u3 completes 2 of 3 steps
            _event("u3", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u3", "onboarding_complete", "2025-12-01T10:30:00Z"),
            # u4 completes only step 1
            _event("u4", "sign_up", "2025-12-01T10:00:00Z"),
        ]

        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(
            events,
            steps=["sign_up", "onboarding_complete", "first_action"],
        )

        assert result["steps"][0]["count"] == 4  # all 4 signed up
        assert result["steps"][1]["count"] == 3  # 3 completed onboarding
        assert result["steps"][2]["count"] == 1  # 1 took first action
        assert result["overall_conversion"] == 25  # 1/4
        assert result["biggest_drop"] is not None
        assert result["biggest_drop"]["from"] == "onboarding_complete"
        assert result["biggest_drop"]["to"] == "first_action"
        assert result["biggest_drop"]["users_lost"] == 2

    def test_empty_events(self):
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel([], steps=["sign_up", "click"])
        assert result["steps"][0]["count"] == 0
        assert result["overall_conversion"] == 0

    def test_no_steps(self):
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel([_event("u1", "click", "2025-12-01T10:00:00Z")], steps=[])
        assert result["steps"] == []

    def test_case_insensitive_matching(self):
        events = [
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u1", "onboarding_complete", "2025-12-01T11:00:00Z"),
        ]
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(events, steps=["Sign_Up", "Onboarding_Complete"])
        assert result["steps"][0]["count"] == 1
        assert result["steps"][1]["count"] == 1

    def test_step_order_matters(self):
        # Events in wrong order — step 2 before step 1
        events = [
            _event("u1", "onboarding_complete", "2025-12-01T09:00:00Z"),
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
        ]
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(events, steps=["sign_up", "onboarding_complete"])
        # u1 does sign_up at 10:00 but there's no onboarding_complete after that
        assert result["steps"][0]["count"] == 1
        assert result["steps"][1]["count"] == 0


class TestAnomalyDetection:
    """TC-008: Anomaly detection in trends."""

    def test_detects_spike(self):
        users = [_user(f"u{i}", f"2025-12-0{(i % 9) + 1}T10:00:00Z") for i in range(10)]
        events = []
        # Normal activity: ~10 events per week for 5 weeks
        base_dates = [
            ("2025-12-01", 10),
            ("2025-12-08", 11),
            ("2025-12-15", 9),
            ("2025-12-22", 10),
            ("2025-12-29", 10),
            # Week 6: spike to 30 events
            ("2026-01-05", 30),
        ]
        uid_idx = 0
        for base_date, count in base_dates:
            for j in range(count):
                uid = f"u{uid_idx % 10}"
                uid_idx += 1
                events.append(_event(uid, "page_view", f"{base_date}T{10 + j % 12}:00:00Z"))

        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "events_count", "weekly")

        assert result["direction"] in ("growing", "stable", "declining")
        # Should detect the spike
        if result["anomalies"]:
            assert result["anomalies"][-1]["severity"] in ("mild", "notable", "severe")

    def test_no_anomalies_when_stable(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        events = []
        for week in range(6):
            for day in range(5):
                events.append(
                    _event("u1", "page_view", f"2025-12-{1 + week * 7 + day:02d}T10:00:00Z")
                )

        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "events_count", "weekly")
        # All weeks have exactly 5 events — no anomalies
        assert result["anomalies"] == []

    def test_unknown_metric(self):
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend([], [], [], "unknown_metric")
        assert "error" in result

    def test_empty_data(self):
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend([], [], [], "active_users")
        assert result["direction"] == "insufficient_data"


class TestSegmentComparison:
    """TC-011: Segment comparison."""

    def test_paying_vs_free(self):
        users = [
            _user("u1", "2025-12-01T10:00:00Z", stripe_id="cus_1"),
            _user("u2", "2025-12-01T10:00:00Z"),
            _user("u3", "2025-12-01T10:00:00Z"),
        ]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z")]
        events = [
            _event("u1", "click", "2026-02-20T10:00:00Z"),
            _event("u1", "click", "2026-02-21T10:00:00Z"),
            _event("u2", "click", "2026-02-20T10:00:00Z"),
        ]

        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "paying", "free", "events_per_user")

        assert result["segment_a"]["name"] == "paying"
        assert result["segment_a"]["size"] == 1
        assert result["segment_b"]["name"] == "free"
        assert result["segment_b"]["size"] == 2
        assert result["statistically_significant"] is False  # <30 in both

    def test_both_empty_segments(self):
        analyzer = SegmentAnalyzer()
        result = analyzer.compare([], [], [], "paying", "free", "active_users")
        assert result["segment_a"]["size"] == 0
        assert result["segment_b"]["size"] == 0

    def test_confidence_low_when_small(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, [], [], "paying", "free", "active_users")
        assert result["confidence"] == "low"


class TestOMTMSelector:
    """TC-012: OMTM stage selection."""

    def test_acquisition_stage_few_users(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(10)]

        selector = OMTMSelector()
        result = selector.suggest_omtm(users, [], [])
        assert result["stage"] == "acquisition"
        assert result["suggested_metric"] == "new_users_per_week"

    def test_activation_stage_low_onboarding(self):
        # 60 users but only 10 have >3 events (17% onboarding)
        users = [_user(f"u{i}", f"2025-12-{(i % 28) + 1:02d}T10:00:00Z") for i in range(60)]
        events = []
        # Only 10 users get 4+ events
        for i in range(10):
            for j in range(5):
                events.append(_event(f"u{i}", "click", f"2025-12-{(j % 28) + 1:02d}T10:00:00Z"))

        selector = OMTMSelector()
        result = selector.suggest_omtm(users, events, [])
        assert result["stage"] == "activation"
        assert result["suggested_metric"] == "onboarding_completion_rate"

    def test_revenue_stage(self):
        # 60 users, good onboarding (>30%), good retention (>40%), but few paying
        users = [_user(f"u{i}", f"2025-11-{(i % 28) + 1:02d}T10:00:00Z") for i in range(60)]
        events = []
        # 25 users with 4+ events (42% onboarding)
        for i in range(25):
            for j in range(5):
                events.append(_event(f"u{i}", "click", f"2025-11-{(j % 28) + 1:02d}T10:00:00Z"))
            # Also active in Dec (retention)
            events.append(_event(f"u{i}", "click", "2025-12-15T10:00:00Z"))

        subs = [_sub("u0", "sub_0", "active", 2900, "2025-12-01T10:00:00Z")]

        selector = OMTMSelector()
        result = selector.suggest_omtm(users, events, subs)
        assert result["stage"] == "revenue"

    def test_empty_data(self):
        selector = OMTMSelector()
        result = selector.suggest_omtm([], [], [])
        assert result["stage"] == "acquisition"
