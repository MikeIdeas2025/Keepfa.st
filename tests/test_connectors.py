"""Tests for PostHog and Stripe connectors."""

import httpx
import pytest

from keepfast.connectors.base import ConnectorError
from keepfast.connectors.posthog import PostHogConnector
from keepfast.connectors.stripe import StripeConnector


def _make_response(status_code: int, json_data: dict, headers: dict | None = None):
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {},
        request=httpx.Request("GET", "https://test.com"),
    )


class TestPostHogConnector:
    def test_get_events_single_page(self, auth_manager, monkeypatch, posthog_events):
        connector = PostHogConnector(auth_manager)
        response_data = {"results": posthog_events[:5], "next": None}

        def mock_get(self, url, **kwargs):
            return _make_response(200, response_data)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        events = connector.get_events()
        assert len(events) == 5

    def test_get_events_with_pagination(self, auth_manager, monkeypatch, posthog_events):
        connector = PostHogConnector(auth_manager)
        call_count = 0

        def mock_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(
                    200,
                    {"results": posthog_events[:3], "next": "https://app.posthog.com/api/next"},
                )
            return _make_response(200, {"results": posthog_events[3:6], "next": None})

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        events = connector.get_events()
        assert len(events) == 6
        assert call_count == 2

    def test_get_persons(self, auth_manager, monkeypatch, posthog_persons):
        connector = PostHogConnector(auth_manager)
        response_data = {"results": posthog_persons, "next": None}

        def mock_get(self, url, **kwargs):
            return _make_response(200, response_data)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        persons = connector.get_persons()
        assert len(persons) == 10

    def test_get_cohorts(self, auth_manager, monkeypatch):
        connector = PostHogConnector(auth_manager)
        response_data = {"results": [{"id": 1, "name": "Power Users"}], "next": None}

        def mock_get(self, url, **kwargs):
            return _make_response(200, response_data)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        cohorts = connector.get_cohorts()
        assert len(cohorts) == 1

    def test_401_raises_connector_error(self, auth_manager, monkeypatch):
        connector = PostHogConnector(auth_manager)

        def mock_get(self, url, **kwargs):
            return _make_response(401, {"detail": "Authentication credentials were not provided."})

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        with pytest.raises(ConnectorError, match="Authentication failed"):
            connector.get_events()

    def test_timeout_retries(self, auth_manager, monkeypatch):
        connector = PostHogConnector(auth_manager)
        call_count = 0

        def mock_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        # Patch time.sleep to avoid actual waiting
        monkeypatch.setattr("time.sleep", lambda _: None)

        with pytest.raises(ConnectorError, match="timed out"):
            connector.get_events()
        assert call_count == 3  # initial + 2 retries


class TestStripeConnector:
    def test_get_customers_single_page(self, auth_manager, monkeypatch, stripe_customers):
        connector = StripeConnector(auth_manager)
        response_data = {"data": stripe_customers, "has_more": False}

        def mock_get(self, url, **kwargs):
            return _make_response(200, response_data)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        customers = connector.get_customers()
        assert len(customers) == 10

    def test_get_subscriptions_with_pagination(
        self, auth_manager, monkeypatch, stripe_subscriptions
    ):
        connector = StripeConnector(auth_manager)
        call_count = 0

        def mock_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(
                    200,
                    {"data": stripe_subscriptions[:4], "has_more": True},
                )
            return _make_response(
                200,
                {"data": stripe_subscriptions[4:], "has_more": False},
            )

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        subs = connector.get_subscriptions()
        assert len(subs) == 8
        assert call_count == 2

    def test_get_invoices(self, auth_manager, monkeypatch):
        connector = StripeConnector(auth_manager)
        invoices = [{"id": "in_001", "amount_paid": 2900, "status": "paid"}]
        response_data = {"data": invoices, "has_more": False}

        def mock_get(self, url, **kwargs):
            return _make_response(200, response_data)

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        result = connector.get_invoices(customer_id="cus_001")
        assert len(result) == 1

    def test_401_raises_connector_error(self, auth_manager, monkeypatch):
        connector = StripeConnector(auth_manager)

        def mock_get(self, url, **kwargs):
            return _make_response(401, {"error": {"message": "Invalid API Key"}})

        monkeypatch.setattr(httpx.Client, "get", mock_get)
        with pytest.raises(ConnectorError, match="Authentication failed"):
            connector.get_customers()


class TestCacheBehavior:
    """IT-005: Cache hit verification."""

    def test_cache_hit_no_second_request(self, auth_manager, monkeypatch, posthog_persons):
        connector = PostHogConnector(auth_manager)
        call_count = 0

        def mock_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_response(200, {"results": posthog_persons, "next": None})

        monkeypatch.setattr(httpx.Client, "get", mock_get)

        # First call — hits API
        result1 = connector.get_persons()
        assert call_count == 1

        # Second call — should use cache
        result2 = connector.get_persons()
        assert call_count == 1  # no new HTTP call
        assert result1 == result2
