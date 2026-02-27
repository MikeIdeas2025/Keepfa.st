"""Tests for FastMCP server — tool registration and error handling."""

from unittest.mock import MagicMock, patch

from keepfast.server import (
    AppContext,
    compare_segments,
    customer_health_diagnostician,
    get_anomalies,
    get_cohort_retention,
    get_funnel_analysis,
    get_metric_trend,
    lucrative_loyal_strategist,
    mcp,
    retention_journey_orchestrator,
)


class TestToolRegistration:
    def test_server_has_eight_tools(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        assert "customer_health_diagnostician" in tool_names
        assert "retention_journey_orchestrator" in tool_names
        assert "lucrative_loyal_strategist" in tool_names
        assert "get_cohort_retention" in tool_names
        assert "get_funnel_analysis" in tool_names
        assert "get_metric_trend" in tool_names
        assert "compare_segments" in tool_names
        assert "get_anomalies" in tool_names
        assert len(tool_names) == 8

    def test_server_name(self):
        assert mcp.name == "keepfast"


class TestToolErrorHandling:
    def test_health_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = customer_health_diagnostician(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_journey_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = retention_journey_orchestrator(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_clv_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = lucrative_loyal_strategist(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_cohort_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = get_cohort_retention(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_funnel_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = get_funnel_analysis(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
                steps="signup,onboarding",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_trend_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = get_metric_trend(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
                metric="active_users",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_segments_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = compare_segments(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
                segment_a="paying",
                segment_b="free",
                metric="retention",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result

    def test_anomalies_tool_returns_string_on_error(self):
        with patch.object(AppContext, "get", side_effect=Exception("connection failed")):
            result = get_anomalies(
                posthog_api_key="bad",
                posthog_project_id="bad",
                stripe_api_key="bad",
                metric="active_users",
            )
        assert isinstance(result, str)
        assert "Something went wrong" in result


def _mock_ctx(translate_return="test output"):
    """Create a mock AppContext with pipeline and translator."""
    mock = MagicMock()
    mock_data = MagicMock()
    mock_data.users = []
    mock_data.events = []
    mock_data.subscriptions = []
    mock.pipeline.fetch_and_normalize.return_value = mock_data
    mock.translator.translate.return_value = translate_return
    return mock


class TestToolsReturnStrings:
    def test_health_returns_string(self):
        mock_ctx = _mock_ctx("test output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = customer_health_diagnostician(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "test output"

    def test_journey_returns_string(self):
        mock_ctx = _mock_ctx("journey output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = retention_journey_orchestrator(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "journey output"

    def test_clv_returns_string(self):
        mock_ctx = _mock_ctx("clv output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = lucrative_loyal_strategist(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "clv output"

    def test_cohort_returns_string(self):
        mock_ctx = _mock_ctx("cohort output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = get_cohort_retention(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "cohort output"

    def test_funnel_returns_string(self):
        mock_ctx = _mock_ctx("funnel output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = get_funnel_analysis(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
                steps="signup,onboarding",
            )
        assert isinstance(result, str)
        assert result == "funnel output"

    def test_trend_returns_string(self):
        mock_ctx = _mock_ctx("trend output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = get_metric_trend(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
                metric="active_users",
            )
        assert isinstance(result, str)
        assert result == "trend output"

    def test_segments_returns_string(self):
        mock_ctx = _mock_ctx("segment output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = compare_segments(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
                segment_a="paying",
                segment_b="free",
                metric="retention",
            )
        assert isinstance(result, str)
        assert result == "segment output"

    def test_anomalies_returns_string(self):
        mock_ctx = _mock_ctx("anomaly output")
        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = get_anomalies(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
                metric="active_users",
            )
        assert isinstance(result, str)
        assert result == "anomaly output"


class TestGetFunnelAnalysis:
    def test_steps_parsing(self):
        """Verify comma-separated steps string is parsed into a list."""
        mock_ctx = _mock_ctx("funnel parsed")

        with patch.object(AppContext, "get", return_value=mock_ctx):
            with patch("keepfast.server.FunnelAnalyzer") as MockAnalyzer:
                instance = MockAnalyzer.return_value
                instance.analyze_funnel.return_value = {"steps": [], "biggest_drop": None}
                get_funnel_analysis(
                    posthog_api_key="phx_test",
                    posthog_project_id="123",
                    stripe_api_key="sk_test",
                    steps="signup, onboarding_complete , feature_used",
                )
                # Verify the steps were parsed and stripped
                call_args = instance.analyze_funnel.call_args
                steps_arg = call_args[0][1]  # second positional arg
                assert steps_arg == ["signup", "onboarding_complete", "feature_used"]

    def test_empty_steps_ignored(self):
        """Verify empty segments from trailing commas are filtered out."""
        mock_ctx = _mock_ctx("funnel parsed")

        with patch.object(AppContext, "get", return_value=mock_ctx):
            with patch("keepfast.server.FunnelAnalyzer") as MockAnalyzer:
                instance = MockAnalyzer.return_value
                instance.analyze_funnel.return_value = {"steps": [], "biggest_drop": None}
                get_funnel_analysis(
                    posthog_api_key="phx_test",
                    posthog_project_id="123",
                    stripe_api_key="sk_test",
                    steps="signup,,onboarding,",
                )
                call_args = instance.analyze_funnel.call_args
                steps_arg = call_args[0][1]
                assert steps_arg == ["signup", "onboarding"]


class TestGetAnomalies:
    def test_threshold_filtering(self):
        """Verify that threshold filters anomalies by relative deviation."""
        mock_ctx = _mock_ctx("anomaly output")
        # Mock TrendAnalyzer to return known anomalies
        trend_result = {
            "anomalies": [
                {"period": "2026-01", "expected": 100, "actual": 250, "severity": "severe"},
                {"period": "2026-02", "expected": 100, "actual": 120, "severity": "mild"},
            ],
            "confidence": "medium",
        }

        with patch.object(AppContext, "get", return_value=mock_ctx):
            with patch("keepfast.server.TrendAnalyzer") as MockAnalyzer:
                instance = MockAnalyzer.return_value
                instance.get_trend.return_value = trend_result
                get_anomalies(
                    posthog_api_key="phx_test",
                    posthog_project_id="123",
                    stripe_api_key="sk_test",
                    metric="active_users",
                    threshold=1.0,
                )
                # Check that translator received only anomalies passing threshold
                translate_call = mock_ctx.translator.translate.call_args
                anomaly_data = translate_call[0][1]
                # 2026-01: |250-100|/100 = 1.5 >= 1.0 → included
                # 2026-02: |120-100|/100 = 0.2 < 1.0 → excluded
                assert len(anomaly_data["anomalies"]) == 1
                assert anomaly_data["anomalies"][0]["period"] == "2026-01"

    def test_high_threshold_filters_all(self):
        """With a very high threshold, no anomalies pass."""
        mock_ctx = _mock_ctx("no anomalies")
        trend_result = {
            "anomalies": [
                {"period": "2026-01", "expected": 100, "actual": 120, "severity": "mild"},
            ],
            "confidence": "low",
        }

        with patch.object(AppContext, "get", return_value=mock_ctx):
            with patch("keepfast.server.TrendAnalyzer") as MockAnalyzer:
                instance = MockAnalyzer.return_value
                instance.get_trend.return_value = trend_result
                get_anomalies(
                    posthog_api_key="phx_test",
                    posthog_project_id="123",
                    stripe_api_key="sk_test",
                    metric="active_users",
                    threshold=5.0,
                )
                translate_call = mock_ctx.translator.translate.call_args
                anomaly_data = translate_call[0][1]
                assert len(anomaly_data["anomalies"]) == 0
