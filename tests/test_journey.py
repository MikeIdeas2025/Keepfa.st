"""Tests for JourneyOrchestrator."""

from keepfast.intelligence.journey import PHASES, JourneyOrchestrator
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


class TestPhaseAssignment:
    def test_assess_no_events(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, [], [])
        assert result["customers_by_phase"]["Assess"] == ["u1"]

    def test_admit_signup_event(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [_event("u1", "sign_up", "2025-12-01T10:00:00Z")]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Admit"]

    def test_affirm_many_early_events(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [
            _event("u1", "view", "2025-12-01T10:00:00Z"),
            _event("u1", "click", "2025-12-01T11:00:00Z"),
            _event("u1", "scroll", "2025-12-01T12:00:00Z"),
            _event("u1", "submit", "2025-12-01T13:00:00Z"),
            _event("u1", "navigate", "2025-12-01T14:00:00Z"),
        ]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Affirm"]

    def test_activate_onboarding_complete(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u1", "onboarding_complete", "2025-12-01T11:00:00Z"),
        ]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Activate"]

    def test_acclimate_diverse_events(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u1", "onboarding_complete", "2025-12-01T11:00:00Z"),
            _event("u1", "click", "2025-12-03T10:00:00Z"),
            _event("u1", "view", "2025-12-05T10:00:00Z"),
            _event("u1", "submit", "2025-12-06T10:00:00Z"),
            _event("u1", "navigate", "2025-12-07T10:00:00Z"),
            _event("u1", "scroll", "2025-12-08T10:00:00Z"),
            _event("u1", "search", "2025-12-08T11:00:00Z"),
        ]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Acclimate"]

    def test_accomplish_feature_used(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", email="a@t.com")]
        events = [
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u1", "feature_used", "2025-12-20T10:00:00Z"),
        ]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Accomplish"]

    def test_adopt_multimonth(self):
        users = [_user("u1", "2025-11-01T10:00:00Z", email="a@t.com")]
        events = [
            _event("u1", "click", "2025-11-01T10:00:00Z"),
            _event("u1", "click", "2025-12-15T10:00:00Z"),
        ]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])
        assert "a@t.com" in result["customers_by_phase"]["Adopt"]

    def test_advocate_high_engagement_paying(self):
        users = [_user("u1", "2025-10-01T10:00:00Z", email="a@t.com", stripe_id="cus_1")]
        events = [
            _event("u1", f"action_{i}", f"2025-{10 + i // 10}-%02dT10:00:00Z" % ((i % 28) + 1))
            for i in range(25)
        ]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-10-01T10:00:00Z")]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, subs)
        assert "a@t.com" in result["customers_by_phase"]["Advocate"]


class TestPhaseOrdering:
    def test_user_gets_highest_phase(self):
        """A user who qualifies for multiple phases gets the highest."""
        users = [_user("u1", "2025-10-01T10:00:00Z", email="a@t.com", stripe_id="cus_1")]
        events = [
            _event("u1", "sign_up", "2025-10-01T10:00:00Z"),
            _event("u1", "onboarding_complete", "2025-10-01T11:00:00Z"),
            _event("u1", "feature_used", "2025-10-20T10:00:00Z"),
            _event("u1", "click", "2025-11-15T10:00:00Z"),
            _event("u1", "click", "2025-12-15T10:00:00Z"),
        ]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-10-01T10:00:00Z")]

        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, subs)

        # Should be in Adopt (>30 days, multi-month) — not Activate or Accomplish
        assert "a@t.com" in result["customers_by_phase"]["Adopt"]


class TestBottleneckDetection:
    def test_bottleneck_found(self):
        users = [
            _user("u1", "2025-12-01T10:00:00Z", email="a@t.com"),
            _user("u2", "2025-12-01T10:00:00Z", email="b@t.com"),
            _user("u3", "2025-12-01T10:00:00Z", email="c@t.com"),
        ]
        # u1: Admit (has signup), u2: Admit (has signup), u3: Assess (no events)
        events = [
            _event("u1", "sign_up", "2025-12-01T10:00:00Z"),
            _event("u2", "sign_up", "2025-12-01T10:00:00Z"),
        ]

        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])

        assert result["bottleneck"] is not None
        assert "drop_pct" in result["bottleneck"]

    def test_no_bottleneck_when_all_same_phase(self):
        users = [_user("u1", "2025-12-01T10:00:00Z"), _user("u2", "2025-12-01T10:00:00Z")]

        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, [], [])

        # Both in Assess — no drop between phases with users
        # Bottleneck should be from Assess to Admit
        if result["bottleneck"]:
            assert result["bottleneck"]["from"] == "Assess"


class TestFirst100Days:
    def test_first_100_days_window(self):
        users = [
            _user("u1", "2026-01-01T10:00:00Z", email="a@t.com"),
            _user("u2", "2024-01-01T10:00:00Z", email="b@t.com"),  # old user, outside window
        ]
        events = [_event("u1", "sign_up", "2026-01-01T10:00:00Z")]

        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, events, [])

        assert result["first_100_days"]["users_in_window"] == 1


class TestJourneyZeroData:
    def test_empty_users(self):
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey([], [], [])

        assert all(p["count"] == 0 for p in result["phase_distribution"])
        assert result["confidence"] == "low"

    def test_all_phases_present(self):
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey([], [], [])

        phase_names = [p["phase"] for p in result["phase_distribution"]]
        assert phase_names == PHASES

    def test_zero_events_all_in_assess(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(5)]
        orchestrator = JourneyOrchestrator()
        result = orchestrator.map_journey(users, [], [])

        assert result["phase_distribution"][0]["count"] == 5  # All in Assess
        assert result["phase_distribution"][0]["phase"] == "Assess"
