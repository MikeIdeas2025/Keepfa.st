"""Base connector with shared cache, retry, and error handling."""

import logging
import time

import httpx
from cachetools import TTLCache

from keepfast.auth import AuthManager

logger = logging.getLogger(__name__)

MAX_PAGES = 10


class ConnectorError(Exception):
    """Raised for non-retryable connector errors (401, 404, etc.)."""


class BaseConnector:
    """Base class for API connectors with TTL cache and retry logic."""

    def __init__(self, auth: AuthManager, cache_ttl: int = 300):
        self._auth = auth
        self._cache: TTLCache = TTLCache(maxsize=100, ttl=cache_ttl)
        self._client = httpx.Client(timeout=30.0)

    def _cache_key(self, url: str, params: dict | None = None) -> str:
        sorted_params = tuple(sorted((params or {}).items()))
        return f"{url}|{sorted_params}"

    def _cached_get(self, url: str, headers: dict[str, str], params: dict | None = None) -> dict:
        key = self._cache_key(url, params)
        if key in self._cache:
            logger.debug("Cache hit: %s", url)
            return self._cache[key]

        data = self._request_with_retry(url, headers, params)
        self._cache[key] = data
        return data

    def _request_with_retry(
        self, url: str, headers: dict[str, str], params: dict | None = None
    ) -> dict:
        backoff_times = [2, 4]
        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = self._client.get(url, headers=headers, params=params)

                if response.status_code == 401:
                    raise ConnectorError(
                        f"Authentication failed (401). Check your API key. URL: {url}"
                    )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    retry_after = min(retry_after, 60)
                    logger.warning("Rate limited (429). Waiting %ds.", retry_after)
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < 2:
                    wait = backoff_times[attempt]
                    logger.warning("Timeout on attempt %d. Retrying in %ds.", attempt + 1, wait)
                    time.sleep(wait)
                    continue
                raise ConnectorError(
                    f"Request timed out after 3 attempts. URL: {url}"
                ) from last_error

            except httpx.ConnectError as e:
                last_error = e
                if attempt < 1:
                    logger.warning("Connection error. Retrying in 2s.")
                    time.sleep(2)
                    continue
                raise ConnectorError(
                    f"Cannot reach the service. Check your internet connection. URL: {url}"
                ) from last_error

            except httpx.HTTPStatusError as e:
                raise ConnectorError(f"HTTP {e.response.status_code} error. URL: {url}") from e

        raise ConnectorError(f"Request failed after retries. URL: {url}")
