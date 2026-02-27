"""PostHog API connector."""

import logging

from keepfast.auth import AuthManager
from keepfast.connectors.base import MAX_PAGES, BaseConnector

logger = logging.getLogger(__name__)


class PostHogConnector(BaseConnector):
    """Fetches events, persons, insights, and cohorts from PostHog API."""

    def __init__(self, auth: AuthManager, cache_ttl: int = 300):
        super().__init__(auth, cache_ttl)
        self._base_url = auth.posthog_base_url
        self._headers = auth.posthog_headers

    def get_events(
        self, event_name: str | None = None, date_from: str = "", date_to: str = ""
    ) -> list[dict]:
        params: dict = {}
        if event_name:
            params["event"] = event_name
        if date_from:
            params["after"] = date_from
        if date_to:
            params["before"] = date_to
        return self._paginate_posthog(f"{self._base_url}/events", params)

    def get_persons(self, search: str | None = None) -> list[dict]:
        params: dict = {}
        if search:
            params["search"] = search
        return self._paginate_posthog(f"{self._base_url}/persons", params)

    def get_insights(self, insight_type: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}/insights/trend"
        request_params = dict(params or {})
        request_params["insight"] = insight_type
        return self._cached_get(url, self._headers, request_params)

    def get_cohorts(self) -> list[dict]:
        return self._paginate_posthog(f"{self._base_url}/cohorts", {})

    def _paginate_posthog(self, url: str, params: dict) -> list[dict]:
        all_results: list[dict] = []
        current_url = url
        current_params: dict | None = params

        for page in range(MAX_PAGES):
            data = self._cached_get(current_url, self._headers, current_params)
            results = data.get("results", [])
            all_results.extend(results)

            next_url = data.get("next")
            if not next_url:
                break

            current_url = next_url
            current_params = None  # next URL includes params
            logger.debug(
                "PostHog pagination: page %d, total results so far: %d", page + 1, len(all_results)
            )

        return all_results
