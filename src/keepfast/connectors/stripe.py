"""Stripe API connector."""

import logging

from keepfast.auth import AuthManager
from keepfast.connectors.base import MAX_PAGES, BaseConnector

logger = logging.getLogger(__name__)


class StripeConnector(BaseConnector):
    """Fetches customers, subscriptions, invoices, and events from Stripe API."""

    def __init__(self, auth: AuthManager, cache_ttl: int = 300):
        super().__init__(auth, cache_ttl)
        self._base_url = auth.stripe_base_url
        self._headers = auth.stripe_headers

    def get_customers(self, limit: int = 100) -> list[dict]:
        return self._paginate_stripe(f"{self._base_url}/v1/customers", {"limit": limit})

    def get_subscriptions(self, status: str = "all") -> list[dict]:
        params: dict = {"limit": 100}
        if status != "all":
            params["status"] = status
        return self._paginate_stripe(f"{self._base_url}/v1/subscriptions", params)

    def get_invoices(self, customer_id: str | None = None) -> list[dict]:
        params: dict = {"limit": 100}
        if customer_id:
            params["customer"] = customer_id
        return self._paginate_stripe(f"{self._base_url}/v1/invoices", params)

    def get_subscription_events(self, sub_id: str) -> list[dict]:
        params: dict = {"limit": 100, "type": "customer.subscription.*"}
        if sub_id:
            params["object_id"] = sub_id  # filter events related to this subscription
        return self._paginate_stripe(f"{self._base_url}/v1/events", params)

    def _paginate_stripe(self, url: str, params: dict) -> list[dict]:
        all_results: list[dict] = []
        current_params = dict(params)

        for page in range(MAX_PAGES):
            data = self._cached_get(url, self._headers, current_params)
            items = data.get("data", [])
            all_results.extend(items)

            if not data.get("has_more", False):
                break

            if items:
                current_params["starting_after"] = items[-1]["id"]
            else:
                break

            logger.debug(
                "Stripe pagination: page %d, total results so far: %d",
                page + 1,
                len(all_results),
            )

        return all_results
