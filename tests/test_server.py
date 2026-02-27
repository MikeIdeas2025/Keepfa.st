"""Tests for FastMCP server — tool registration and error handling."""

from unittest.mock import MagicMock, patch

from keepfast.server import (
    AppContext,
    customer_health_diagnostician,
    lucrative_loyal_strategist,
    mcp,
    retention_journey_orchestrator,
)


class TestToolRegistration:
    def test_server_has_three_tools(self):
        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())
        assert "customer_health_diagnostician" in tool_names
        assert "retention_journey_orchestrator" in tool_names
        assert "lucrative_loyal_strategist" in tool_names

    def test_server_name(self):
        assert mcp.name == "keepfast"


class TestToolErrorHandling:
    def test_health_tool_returns_string_on_error(self):
        # Force an error by using invalid credentials that will fail at connector level
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


class TestToolsReturnStrings:
    def test_health_returns_string(self):
        mock_ctx = MagicMock()
        mock_data = MagicMock()
        mock_data.users = []
        mock_data.events = []
        mock_data.subscriptions = []
        mock_ctx.pipeline.fetch_and_normalize.return_value = mock_data
        mock_ctx.translator.translate.return_value = "test output"

        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = customer_health_diagnostician(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "test output"

    def test_journey_returns_string(self):
        mock_ctx = MagicMock()
        mock_data = MagicMock()
        mock_data.users = []
        mock_data.events = []
        mock_data.subscriptions = []
        mock_ctx.pipeline.fetch_and_normalize.return_value = mock_data
        mock_ctx.translator.translate.return_value = "journey output"

        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = retention_journey_orchestrator(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "journey output"

    def test_clv_returns_string(self):
        mock_ctx = MagicMock()
        mock_data = MagicMock()
        mock_data.users = []
        mock_data.events = []
        mock_data.subscriptions = []
        mock_ctx.pipeline.fetch_and_normalize.return_value = mock_data
        mock_ctx.translator.translate.return_value = "clv output"

        with patch.object(AppContext, "get", return_value=mock_ctx):
            result = lucrative_loyal_strategist(
                posthog_api_key="phx_test",
                posthog_project_id="123",
                stripe_api_key="sk_test",
            )
        assert isinstance(result, str)
        assert result == "clv output"
