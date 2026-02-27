"""Tests for DataPipeline orchestrator."""

from keepfast.pipeline import DataPipeline, NormalizedData
from tests.stubs import FakePostHogConnector, FakeStripeConnector


class TestDataPipeline:
    def test_fetch_and_normalize_returns_normalized_data(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        assert isinstance(result, NormalizedData)
        assert len(result.users) > 0
        assert len(result.events) > 0
        assert len(result.subscriptions) > 0

    def test_users_have_internal_ids(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        for user in result.users:
            assert user.internal_id
            assert isinstance(user.internal_id, str)

    def test_events_remapped_to_internal_ids(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        user_ids = {u.internal_id for u in result.users}
        # At least some events should have internal_ids matching users
        remapped = [e for e in result.events if e.user_id in user_ids]
        assert len(remapped) > 0

    def test_subscriptions_linked_to_users(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        user_ids = {u.internal_id for u in result.users}
        for sub in result.subscriptions:
            assert sub.user_id in user_ids

    def test_events_are_cleaned(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        event_names = {e.event_name for e in result.events}
        # Fixture events include "signUp" -> should be normalized to "sign_up"
        assert "sign_up" in event_names

    def test_matched_users_exist(self):
        pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
        result = pipeline.fetch_and_normalize()

        matched = [u for u in result.users if u.is_matched]
        assert len(matched) >= 5
