"""Keepfa.st MCP server — 3 high-level retention analysis skills."""

import logging

from mcp.server.fastmcp import FastMCP

from keepfast.auth import AuthManager
from keepfast.connectors.posthog import PostHogConnector
from keepfast.connectors.stripe import StripeConnector
from keepfast.intelligence.clv import CLVAnalyzer
from keepfast.intelligence.health import CustomerHealthAnalyzer
from keepfast.intelligence.journey import JourneyOrchestrator
from keepfast.pipeline import DataPipeline
from keepfast.translation.plain_language import TranslationLayer

logger = logging.getLogger(__name__)

mcp = FastMCP("keepfast")


class AppContext:
    """Lazy-initialized shared state — cached per credential set."""

    _instance: "AppContext | None" = None
    _cache_key: str = ""

    def __init__(self, pipeline: DataPipeline, translator: TranslationLayer):
        self.pipeline = pipeline
        self.translator = translator

    @classmethod
    def get(
        cls,
        posthog_api_key: str,
        posthog_project_id: str,
        stripe_api_key: str,
        posthog_host: str,
    ) -> "AppContext":
        key = f"{posthog_api_key}:{posthog_project_id}:{stripe_api_key}:{posthog_host}"
        if cls._instance is None or cls._cache_key != key:
            auth = AuthManager(
                posthog_api_key=posthog_api_key,
                posthog_project_id=posthog_project_id,
                stripe_api_key=stripe_api_key,
                posthog_host=posthog_host,
            )
            posthog = PostHogConnector(auth)
            stripe = StripeConnector(auth)
            pipeline = DataPipeline(posthog, stripe)
            translator = TranslationLayer()
            cls._instance = cls(pipeline, translator)
            cls._cache_key = key
        return cls._instance


@mcp.tool()
def customer_health_diagnostician(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    posthog_host: str = "https://app.posthog.com",
    language: str = "auto",
) -> str:
    """Analyze the health of your customers. Shows who's thriving,
    who's at risk, and what's causing problems."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = CustomerHealthAnalyzer().diagnose(data.users, data.events, data.subscriptions)
        return ctx.translator.translate("health", result, language)
    except Exception as e:
        logger.exception("customer_health_diagnostician failed")
        return f"Something went wrong while analyzing customer health: {e}"


@mcp.tool()
def retention_journey_orchestrator(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    posthog_host: str = "https://app.posthog.com",
    language: str = "auto",
) -> str:
    """Map where your customers are in their journey — from first
    contact to loyal advocate. Identifies where people get stuck."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = JourneyOrchestrator().map_journey(data.users, data.events, data.subscriptions)
        return ctx.translator.translate("journey", result, language)
    except Exception as e:
        logger.exception("retention_journey_orchestrator failed")
        return f"Something went wrong while mapping customer journeys: {e}"


@mcp.tool()
def lucrative_loyal_strategist(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    posthog_host: str = "https://app.posthog.com",
    discount_rate: float = 0.1,
    language: str = "auto",
) -> str:
    """Calculate how much each customer is worth over their lifetime
    and get a plan to increase loyalty."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = CLVAnalyzer().analyze(
            data.users, data.events, data.subscriptions, discount_rate=discount_rate
        )
        return ctx.translator.translate("clv", result, language)
    except Exception as e:
        logger.exception("lucrative_loyal_strategist failed")
        return f"Something went wrong while calculating customer value: {e}"


def main():
    mcp.run()
