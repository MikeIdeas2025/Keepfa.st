"""Keepfa.st MCP server — 9 retention analysis tools."""

import logging

from mcp.server.fastmcp import FastMCP

from keepfast.auth import AuthManager
from keepfast.connectors.posthog import PostHogConnector
from keepfast.connectors.stripe import StripeConnector
from keepfast.intelligence.clv import CLVAnalyzer
from keepfast.intelligence.cohort import CohortAnalyzer
from keepfast.intelligence.funnel import FunnelAnalyzer
from keepfast.intelligence.health import CustomerHealthAnalyzer
from keepfast.intelligence.journey import JourneyOrchestrator
from keepfast.intelligence.omtm import OMTMSelector
from keepfast.intelligence.segments import SegmentAnalyzer
from keepfast.intelligence.trends import TrendAnalyzer
from keepfast.pipeline import DataPipeline
from keepfast.translation.plain_language import TranslationLayer

logger = logging.getLogger(__name__)

mcp = FastMCP("keepfast")

SANDBOX_KEY = "sandbox"


def _is_sandbox(posthog_api_key: str) -> bool:
    return posthog_api_key.strip().lower() == SANDBOX_KEY


def _sandbox_context() -> "AppContext":
    """Build an AppContext with fake connectors and fixture data."""
    from keepfast.sandbox import FakePostHogConnector, FakeStripeConnector

    pipeline = DataPipeline(FakePostHogConnector(), FakeStripeConnector())
    return AppContext(pipeline, TranslationLayer())


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
        if _is_sandbox(posthog_api_key):
            return _sandbox_context()

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
    user_query: str = "",
) -> str:
    """Analyze the health of your customers. Shows who's thriving,
    who's at risk, and what's causing problems."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = CustomerHealthAnalyzer().diagnose(data.users, data.events, data.subscriptions)
        return ctx.translator.translate("health", result, language, user_query=user_query)
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
    user_query: str = "",
) -> str:
    """Map where your customers are in their journey — from first
    contact to loyal advocate. Identifies where people get stuck."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = JourneyOrchestrator().map_journey(data.users, data.events, data.subscriptions)
        return ctx.translator.translate("journey", result, language, user_query=user_query)
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
    user_query: str = "",
) -> str:
    """Calculate how much each customer is worth over their lifetime
    and get a plan to increase loyalty."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = CLVAnalyzer().analyze(
            data.users, data.events, data.subscriptions, discount_rate=discount_rate
        )
        return ctx.translator.translate("clv", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("lucrative_loyal_strategist failed")
        return f"Something went wrong while calculating customer value: {e}"


@mcp.tool()
def get_cohort_retention(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    posthog_host: str = "https://app.posthog.com",
    cohort_period: str = "monthly",
    periods: int = 6,
    language: str = "auto",
    user_query: str = "",
) -> str:
    """See how many of your users come back over time, grouped by when they signed up."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = CohortAnalyzer().calculate_retention(
            data.users, data.events, cohort_period, periods
        )
        return ctx.translator.translate("cohort", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("get_cohort_retention failed")
        return f"Something went wrong while analyzing cohort retention: {e}"


@mcp.tool()
def get_funnel_analysis(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    steps: str,
    posthog_host: str = "https://app.posthog.com",
    language: str = "auto",
    user_query: str = "",
) -> str:
    """Find where people drop off in a specific flow. Pass event names separated by commas."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        steps_list = [s.strip() for s in steps.split(",") if s.strip()]
        result = FunnelAnalyzer().analyze_funnel(data.events, steps_list)
        return ctx.translator.translate("funnel", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("get_funnel_analysis failed")
        return f"Something went wrong while analyzing the funnel: {e}"


@mcp.tool()
def get_metric_trend(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    metric: str,
    posthog_host: str = "https://app.posthog.com",
    granularity: str = "weekly",
    language: str = "auto",
    user_query: str = "",
) -> str:
    """Show how any metric is changing over time — growing, declining, or stable."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = TrendAnalyzer().get_trend(
            data.users, data.events, data.subscriptions, metric, granularity
        )
        return ctx.translator.translate("trend", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("get_metric_trend failed")
        return f"Something went wrong while analyzing the metric trend: {e}"


@mcp.tool()
def compare_segments(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    segment_a: str,
    segment_b: str,
    metric: str,
    posthog_host: str = "https://app.posthog.com",
    language: str = "auto",
    user_query: str = "",
) -> str:
    """Compare two groups of users on any metric. Segments: paying, free, new, returning, active, inactive."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = SegmentAnalyzer().compare(
            data.users, data.events, data.subscriptions, segment_a, segment_b, metric
        )
        return ctx.translator.translate("segment", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("compare_segments failed")
        return f"Something went wrong while comparing segments: {e}"


@mcp.tool()
def get_anomalies(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    metric: str,
    posthog_host: str = "https://app.posthog.com",
    threshold: float = 1.5,
    language: str = "auto",
    user_query: str = "",
) -> str:
    """Detect unusual patterns in any metric. Flags spikes, drops, and unexpected changes."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        trend_result = TrendAnalyzer().get_trend(
            data.users, data.events, data.subscriptions, metric
        )
        # Filter anomalies by threshold sensitivity
        all_anomalies = trend_result.get("anomalies", [])
        filtered = [
            a
            for a in all_anomalies
            if abs(a["actual"] - a["expected"]) / max(a["expected"], 1) >= threshold
        ]
        anomaly_result = {
            "metric": metric,
            "anomalies": filtered,
            "confidence": trend_result.get("confidence", "low"),
        }
        return ctx.translator.translate("anomaly", anomaly_result, language, user_query=user_query)
    except Exception as e:
        logger.exception("get_anomalies failed")
        return f"Something went wrong while detecting anomalies: {e}"


@mcp.tool()
def get_omtm(
    posthog_api_key: str,
    posthog_project_id: str,
    stripe_api_key: str,
    posthog_host: str = "https://app.posthog.com",
    language: str = "auto",
    user_query: str = "",
) -> str:
    """Find the one number you should focus on right now, based on your product's current stage."""
    try:
        ctx = AppContext.get(posthog_api_key, posthog_project_id, stripe_api_key, posthog_host)
        data = ctx.pipeline.fetch_and_normalize()
        result = OMTMSelector().suggest_omtm(data.users, data.events, data.subscriptions)
        return ctx.translator.translate("omtm", result, language, user_query=user_query)
    except Exception as e:
        logger.exception("get_omtm failed")
        return f"Something went wrong while finding your key metric: {e}"


def main():
    mcp.run()
