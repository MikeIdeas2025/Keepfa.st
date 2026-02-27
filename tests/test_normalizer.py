"""Tests for normalizer — schema, cleaner, mapper."""

import pytest

from keepfast.normalizer.cleaner import DataCleaner
from keepfast.normalizer.mapper import UserMapper
from keepfast.normalizer.schema import UnifiedEvent


class TestEventNameNormalization:
    """TC-003/TC-004: Event name normalization rules."""

    @pytest.fixture()
    def cleaner(self):
        return DataCleaner()

    def test_camel_case(self, cleaner):
        assert cleaner.normalize_event_name("pageView") == "page_view"

    def test_pascal_case(self, cleaner):
        assert cleaner.normalize_event_name("PageView") == "page_view"

    def test_spaces(self, cleaner):
        assert cleaner.normalize_event_name("page view") == "page_view"

    def test_kebab_case(self, cleaner):
        assert cleaner.normalize_event_name("page-view") == "page_view"

    def test_dollar_prefix_preserved(self, cleaner):
        assert cleaner.normalize_event_name("$pageview") == "$pageview"

    def test_multiple_underscores_collapsed(self, cleaner):
        assert cleaner.normalize_event_name("page__view") == "page_view"

    def test_empty_string(self, cleaner):
        assert cleaner.normalize_event_name("") == ""

    def test_mixed_case_with_spaces(self, cleaner):
        assert cleaner.normalize_event_name("My Custom Event") == "my_custom_event"

    def test_complex_camel_case(self, cleaner):
        assert cleaner.normalize_event_name("onboardingComplete") == "onboarding_complete"

    def test_already_snake_case(self, cleaner):
        assert cleaner.normalize_event_name("page_view") == "page_view"

    def test_uppercase_acronym(self, cleaner):
        assert cleaner.normalize_event_name("APIRequest") == "api_request"

    def test_unicode_chars(self, cleaner):
        # Should not crash on unicode
        result = cleaner.normalize_event_name("événement_créé")
        assert isinstance(result, str)

    def test_very_long_name(self, cleaner):
        long_name = "a" * 300
        result = cleaner.normalize_event_name(long_name)
        assert len(result) == 300

    def test_kebab_with_camel(self, cleaner):
        assert cleaner.normalize_event_name("onboarding-complete") == "onboarding_complete"

    def test_signUp(self, cleaner):
        assert cleaner.normalize_event_name("signUp") == "sign_up"

    def test_Onboarding_Started(self, cleaner):
        assert cleaner.normalize_event_name("Onboarding Started") == "onboarding_started"

    def test_first__action(self, cleaner):
        assert cleaner.normalize_event_name("first__action") == "first_action"

    def test_featureUsed(self, cleaner):
        assert cleaner.normalize_event_name("featureUsed") == "feature_used"


class TestCleanEvents:
    """Clean raw dicts into UnifiedEvent."""

    @pytest.fixture()
    def cleaner(self):
        return DataCleaner()

    def test_basic_cleaning(self, cleaner):
        raw = [
            {
                "event": "signUp",
                "distinct_id": "user_001",
                "timestamp": "2025-12-01T10:00:00Z",
                "properties": {"plan": "free"},
            }
        ]
        result = cleaner.clean_events(raw)
        assert len(result) == 1
        assert result[0].event_name == "sign_up"
        assert result[0].original_name == "signUp"
        assert result[0].source == "posthog"

    def test_skips_event_without_name(self, cleaner):
        raw = [{"event": "", "distinct_id": "u1", "timestamp": "2025-12-01T10:00:00Z"}]
        result = cleaner.clean_events(raw)
        assert len(result) == 0

    def test_skips_event_without_timestamp(self, cleaner):
        raw = [{"event": "click", "distinct_id": "u1", "timestamp": ""}]
        result = cleaner.clean_events(raw)
        assert len(result) == 0

    def test_uses_provided_user_id(self, cleaner):
        raw = [{"event": "click", "distinct_id": "u1", "timestamp": "2025-12-01T10:00:00Z"}]
        result = cleaner.clean_events(raw, user_id="internal_123")
        assert result[0].user_id == "internal_123"

    def test_malformed_event_skipped(self, cleaner):
        raw = [None, {"event": "click", "distinct_id": "u1", "timestamp": "2025-12-01T10:00:00Z"}]
        result = cleaner.clean_events(raw)
        assert len(result) == 1


class TestDetectOnboardingEvents:
    """Detect events that occur in first 24h for >60% of users."""

    @pytest.fixture()
    def cleaner(self):
        return DataCleaner()

    def test_detects_common_early_events(self, cleaner):
        events = [
            # User A — signs up and onboards within 24h
            UnifiedEvent("u1", "sign_up", "signUp", "2025-12-01T10:00:00Z", "posthog"),
            UnifiedEvent(
                "u1", "onboarding_started", "Onboarding Started", "2025-12-01T10:10:00Z", "posthog"
            ),
            UnifiedEvent(
                "u1", "feature_used", "featureUsed", "2025-12-10T10:00:00Z", "posthog"
            ),  # later
            # User B — signs up and onboards within 24h
            UnifiedEvent("u2", "sign_up", "signUp", "2025-12-03T08:00:00Z", "posthog"),
            UnifiedEvent(
                "u2", "onboarding_started", "Onboarding Started", "2025-12-03T08:15:00Z", "posthog"
            ),
            # User C — signs up and onboards within 24h
            UnifiedEvent("u3", "sign_up", "signUp", "2025-12-05T12:00:00Z", "posthog"),
            UnifiedEvent(
                "u3", "onboarding_started", "Onboarding Started", "2025-12-05T12:10:00Z", "posthog"
            ),
        ]
        onboarding = cleaner.detect_likely_onboarding_events(events)
        assert "sign_up" in onboarding
        assert "onboarding_started" in onboarding
        assert "feature_used" not in onboarding  # only 1 user fired it early

    def test_empty_events(self, cleaner):
        assert cleaner.detect_likely_onboarding_events([]) == []


class TestUserMapper:
    """TC-005: User mapping cross-platform."""

    @pytest.fixture()
    def mapper(self):
        return UserMapper()

    def test_match_by_email(self, mapper, posthog_persons, stripe_customers):
        users = mapper.map_users(posthog_persons, stripe_customers)

        # alice@example.com exists in both
        alice = next(u for u in users if u.email == "alice@example.com")
        assert alice.posthog_distinct_id == "user_001"
        assert alice.stripe_customer_id == "cus_001"
        assert alice.is_matched is True

    def test_unmatched_posthog_user(self, mapper, posthog_persons, stripe_customers):
        users = mapper.map_users(posthog_persons, stripe_customers)

        # user_009 (Ivan NoEmail) has no email — can't match
        ivan = next(u for u in users if u.posthog_distinct_id == "user_009")
        assert ivan.stripe_customer_id is None
        assert ivan.is_matched is False

    def test_unmatched_stripe_customer(self, mapper, posthog_persons, stripe_customers):
        users = mapper.map_users(posthog_persons, stripe_customers)

        # cus_009 (unknown@stripe.com) has no PostHog match
        stripe_only = next(u for u in users if u.stripe_customer_id == "cus_009")
        assert stripe_only.posthog_distinct_id is None
        assert stripe_only.is_matched is False

    def test_total_user_count(self, mapper, posthog_persons, stripe_customers):
        users = mapper.map_users(posthog_persons, stripe_customers)
        # 10 PostHog persons + 2 unmatched Stripe customers (cus_009, cus_010)
        assert len(users) == 12

    def test_empty_inputs(self, mapper):
        users = mapper.map_users([], [])
        assert users == []

    def test_posthog_only(self, mapper, posthog_persons):
        users = mapper.map_users(posthog_persons, [])
        assert len(users) == 10
        assert all(u.stripe_customer_id is None for u in users)

    def test_stripe_only(self, mapper, stripe_customers):
        users = mapper.map_users([], stripe_customers)
        assert len(users) == 10
        assert all(u.posthog_distinct_id is None for u in users)


class TestSubscriptionMapping:
    """Map Stripe subscriptions to UnifiedUsers."""

    @pytest.fixture()
    def mapper(self):
        return UserMapper()

    def test_maps_subscriptions(
        self, mapper, posthog_persons, stripe_customers, stripe_subscriptions
    ):
        users = mapper.map_users(posthog_persons, stripe_customers)
        subs = mapper.map_subscriptions(users, stripe_subscriptions)

        assert len(subs) > 0
        # All subs should have a valid user_id
        user_ids = {u.internal_id for u in users}
        for sub in subs:
            assert sub.user_id in user_ids

    def test_subscription_fields(
        self, mapper, posthog_persons, stripe_customers, stripe_subscriptions
    ):
        users = mapper.map_users(posthog_persons, stripe_customers)
        subs = mapper.map_subscriptions(users, stripe_subscriptions)

        active_subs = [s for s in subs if s.status == "active"]
        assert len(active_subs) >= 1

        first = active_subs[0]
        assert first.mrr_cents > 0
        assert first.started_at != ""
        assert first.canceled_at is None

    def test_canceled_subscription_has_reason(
        self, mapper, posthog_persons, stripe_customers, stripe_subscriptions
    ):
        users = mapper.map_users(posthog_persons, stripe_customers)
        subs = mapper.map_subscriptions(users, stripe_subscriptions)

        canceled = [s for s in subs if s.status == "canceled"]
        assert len(canceled) >= 1
        # At least one should have a cancel reason
        reasons = [s.cancel_reason for s in canceled if s.cancel_reason]
        assert len(reasons) >= 1
