"""Sandbox (fake) connectors that return fixture JSON — for testing MCP tools without real API keys."""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FakePostHogConnector:
    """Returns fixture data instead of calling PostHog API."""

    def __init__(self):
        self._events = json.loads((FIXTURES_DIR / "posthog_events.json").read_text())
        self._persons = json.loads((FIXTURES_DIR / "posthog_persons.json").read_text())

    def get_events(self, event_name=None, date_from="", date_to=""):
        if event_name:
            return [e for e in self._events if e["event"] == event_name]
        return self._events

    def get_persons(self, search=None):
        return self._persons

    def get_insights(self, insight_type, params=None):
        return {"results": []}

    def get_cohorts(self):
        return []


class FakeStripeConnector:
    """Returns fixture data instead of calling Stripe API."""

    def __init__(self):
        self._customers = json.loads((FIXTURES_DIR / "stripe_customers.json").read_text())
        self._subscriptions = json.loads((FIXTURES_DIR / "stripe_subscriptions.json").read_text())

    def get_customers(self, limit=100):
        return self._customers

    def get_subscriptions(self, status="all"):
        if status != "all":
            return [s for s in self._subscriptions if s["status"] == status]
        return self._subscriptions

    def get_invoices(self, customer_id=None):
        return []

    def get_subscription_events(self, sub_id):
        return []
