"""Tests for AuthManager — TC-001 and TC-002."""

import pytest

from keepfast.auth import AuthManager


class TestAuthManagerInit:
    """TC-001: Valid keys create instance, empty keys raise ValueError."""

    def test_valid_keys(self):
        auth = AuthManager(
            posthog_api_key="phx_test123",
            posthog_project_id="12345",
            stripe_api_key="sk_test_abc",
        )
        assert auth._posthog_api_key == "phx_test123"
        assert auth._posthog_project_id == "12345"
        assert auth._stripe_api_key == "sk_test_abc"

    def test_default_posthog_host(self):
        auth = AuthManager(
            posthog_api_key="phx_test123",
            posthog_project_id="12345",
            stripe_api_key="sk_test_abc",
        )
        assert auth._posthog_host == "https://app.posthog.com"

    def test_custom_posthog_host(self):
        auth = AuthManager(
            posthog_api_key="phx_test123",
            posthog_project_id="12345",
            stripe_api_key="sk_test_abc",
            posthog_host="https://eu.posthog.com/",
        )
        assert auth._posthog_host == "https://eu.posthog.com"

    def test_empty_posthog_api_key_raises(self):
        with pytest.raises(ValueError, match="PostHog API key"):
            AuthManager(
                posthog_api_key="",
                posthog_project_id="12345",
                stripe_api_key="sk_test_abc",
            )

    def test_whitespace_posthog_api_key_raises(self):
        with pytest.raises(ValueError, match="PostHog API key"):
            AuthManager(
                posthog_api_key="   ",
                posthog_project_id="12345",
                stripe_api_key="sk_test_abc",
            )

    def test_empty_posthog_project_id_raises(self):
        with pytest.raises(ValueError, match="PostHog project ID"):
            AuthManager(
                posthog_api_key="phx_test123",
                posthog_project_id="",
                stripe_api_key="sk_test_abc",
            )

    def test_empty_stripe_api_key_raises(self):
        with pytest.raises(ValueError, match="Stripe API key"):
            AuthManager(
                posthog_api_key="phx_test123",
                posthog_project_id="12345",
                stripe_api_key="",
            )

    def test_strips_whitespace_from_keys(self):
        auth = AuthManager(
            posthog_api_key="  phx_test123  ",
            posthog_project_id="  12345  ",
            stripe_api_key="  sk_test_abc  ",
        )
        assert auth._posthog_api_key == "phx_test123"
        assert auth._posthog_project_id == "12345"
        assert auth._stripe_api_key == "sk_test_abc"


class TestAuthManagerHeaders:
    """TC-002: Headers and URLs are correct."""

    @pytest.fixture()
    def auth(self):
        return AuthManager(
            posthog_api_key="phx_test123",
            posthog_project_id="12345",
            stripe_api_key="sk_test_abc",
        )

    def test_posthog_headers(self, auth):
        assert auth.posthog_headers == {"Authorization": "Bearer phx_test123"}

    def test_stripe_headers(self, auth):
        assert auth.stripe_headers == {"Authorization": "Bearer sk_test_abc"}

    def test_posthog_base_url(self, auth):
        assert auth.posthog_base_url == "https://app.posthog.com/api/projects/12345"

    def test_stripe_base_url(self, auth):
        assert auth.stripe_base_url == "https://api.stripe.com"
