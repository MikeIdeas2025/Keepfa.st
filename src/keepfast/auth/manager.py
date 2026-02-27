"""API key management for PostHog and Stripe."""


class AuthManager:
    """Holds and validates API keys. No persistence — keys come from MCP params every session."""

    def __init__(
        self,
        posthog_api_key: str,
        posthog_project_id: str,
        stripe_api_key: str,
        posthog_host: str = "https://app.posthog.com",
    ):
        if not posthog_api_key or not posthog_api_key.strip():
            raise ValueError("PostHog API key is required and cannot be empty")
        if not posthog_project_id or not posthog_project_id.strip():
            raise ValueError("PostHog project ID is required and cannot be empty")
        if not stripe_api_key or not stripe_api_key.strip():
            raise ValueError("Stripe API key is required and cannot be empty")

        self._posthog_api_key = posthog_api_key.strip()
        self._posthog_project_id = posthog_project_id.strip()
        self._stripe_api_key = stripe_api_key.strip()
        self._posthog_host = posthog_host.rstrip("/")

    @property
    def posthog_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._posthog_api_key}"}

    @property
    def stripe_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._stripe_api_key}"}

    @property
    def posthog_base_url(self) -> str:
        return f"{self._posthog_host}/api/projects/{self._posthog_project_id}"

    @property
    def stripe_base_url(self) -> str:
        return "https://api.stripe.com"
