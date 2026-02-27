"""Shared fixtures for tests."""

import json
from pathlib import Path

import pytest

from keepfast.auth import AuthManager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def auth_manager():
    return AuthManager(
        posthog_api_key="phx_test_key",
        posthog_project_id="12345",
        stripe_api_key="sk_test_key",
    )


@pytest.fixture()
def posthog_events():
    return json.loads((FIXTURES_DIR / "posthog_events.json").read_text())


@pytest.fixture()
def posthog_persons():
    return json.loads((FIXTURES_DIR / "posthog_persons.json").read_text())


@pytest.fixture()
def stripe_customers():
    return json.loads((FIXTURES_DIR / "stripe_customers.json").read_text())


@pytest.fixture()
def stripe_subscriptions():
    return json.loads((FIXTURES_DIR / "stripe_subscriptions.json").read_text())
