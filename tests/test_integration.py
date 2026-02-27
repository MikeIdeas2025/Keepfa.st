"""Integration tests — full pipeline from fixture data to translated output."""

import pytest

from keepfast.intelligence.cohort import CohortAnalyzer
from keepfast.intelligence.funnel import FunnelAnalyzer
from keepfast.intelligence.trends import TrendAnalyzer
from keepfast.normalizer.cleaner import DataCleaner
from keepfast.normalizer.mapper import UserMapper
from keepfast.translation.plain_language import TranslationLayer
from tests.stubs import FakePostHogConnector, FakeStripeConnector


@pytest.fixture()
def pipeline():
    """Set up the full pipeline: connectors → normalizer → ready for intelligence."""
    posthog = FakePostHogConnector()
    stripe = FakeStripeConnector()

    raw_events = posthog.get_events()
    raw_persons = posthog.get_persons()
    raw_customers = stripe.get_customers()
    raw_subscriptions = stripe.get_subscriptions()

    cleaner = DataCleaner()
    mapper = UserMapper()

    users = mapper.map_users(raw_persons, raw_customers)
    subscriptions = mapper.map_subscriptions(users, raw_subscriptions)

    # Build user_id lookup: posthog distinct_id → internal_id
    ph_to_internal = {}
    for user in users:
        if user.posthog_distinct_id:
            ph_to_internal[user.posthog_distinct_id] = user.internal_id

    # Clean events and remap user_ids to internal_ids
    all_events = []
    for raw in raw_events:
        distinct_id = raw.get("distinct_id", "")
        internal_id = ph_to_internal.get(distinct_id, distinct_id)
        cleaned = cleaner.clean_events([raw], user_id=internal_id)
        all_events.extend(cleaned)

    return {
        "users": users,
        "events": all_events,
        "subscriptions": subscriptions,
        "translator": TranslationLayer(),
    }


class TestFullFlowCohort:
    """IT-001: Full tool flow for get_cohort_retention."""

    def test_cohort_returns_translated_string(self, pipeline):
        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention(
            pipeline["users"],
            pipeline["events"],
            "monthly",
            periods=3,
        )

        translated = pipeline["translator"].translate("cohort", result, language="en")

        assert isinstance(translated, str)
        assert len(translated) > 50  # non-trivial output
        assert "users" in translated.lower() or "came back" in translated.lower()

    def test_cohort_italian(self, pipeline):
        analyzer = CohortAnalyzer()
        result = analyzer.calculate_retention(
            pipeline["users"],
            pipeline["events"],
            "monthly",
            periods=3,
        )

        translated = pipeline["translator"].translate("cohort", result, language="it")
        assert "utenti" in translated.lower() or "tornato" in translated.lower()


class TestFullFlowFunnel:
    """IT-002: Full tool flow for get_funnel_analysis."""

    def test_funnel_returns_translated_string(self, pipeline):
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(
            pipeline["events"],
            steps=["sign_up", "onboarding_complete", "first_action"],
        )

        translated = pipeline["translator"].translate("funnel", result, language="en")

        assert isinstance(translated, str)
        assert len(translated) > 30
        # Should have step counts or conversion info
        assert "%" in translated or "users" in translated.lower()


class TestZeroDataNoCrash:
    """IT-003: Full tool flow with zero data — should not crash."""

    def test_zero_events(self):
        translator = TranslationLayer()
        analyzer = CohortAnalyzer()

        result = analyzer.calculate_retention([], [], "monthly")
        translated = translator.translate("cohort", result, language="en")

        assert isinstance(translated, str)
        assert (
            "don't have" in translated.lower()
            or "no" in translated.lower()
            or "tracking" in translated.lower()
        )

    def test_zero_funnel(self):
        translator = TranslationLayer()
        analyzer = FunnelAnalyzer()

        result = analyzer.analyze_funnel([], steps=["signup", "purchase"])
        translated = translator.translate("funnel", result, language="en")

        assert isinstance(translated, str)
        assert len(translated) > 10

    def test_zero_trend(self):
        translator = TranslationLayer()
        analyzer = TrendAnalyzer()

        result = analyzer.get_trend([], [], [], "active_users")
        translated = translator.translate("trend", result, language="en")

        assert isinstance(translated, str)


class TestUserMappingCrossPlatform:
    """IT-004: User mapping across PostHog + Stripe."""

    def test_matched_users_have_both_ids(self, pipeline):
        users = pipeline["users"]

        matched = [u for u in users if u.is_matched]
        assert len(matched) >= 5  # At least 5 email matches in our fixtures

        for user in matched:
            assert user.posthog_distinct_id is not None
            assert user.stripe_customer_id is not None

    def test_subscriptions_linked_to_users(self, pipeline):
        subs = pipeline["subscriptions"]
        user_ids = {u.internal_id for u in pipeline["users"]}

        assert len(subs) >= 1
        for sub in subs:
            assert sub.user_id in user_ids

    def test_unmatched_users_flagged(self, pipeline):
        users = pipeline["users"]
        unmatched = [u for u in users if not u.is_matched]
        assert len(unmatched) >= 1  # At least some unmatched


class TestEventCleaning:
    """Verify that messy fixture event names get properly normalized."""

    def test_events_are_normalized(self, pipeline):
        events = pipeline["events"]
        event_names = {e.event_name for e in events}

        # These should be normalized from the messy fixture data
        assert "sign_up" in event_names  # from "signUp"
        assert "onboarding_started" in event_names  # from "Onboarding Started"
        assert "onboarding_complete" in event_names  # from "onboarding-complete"
        assert "first_action" in event_names  # from "first__action"
        assert "feature_used" in event_names  # from "featureUsed"
        assert "$pageview" in event_names  # preserved with $ prefix
