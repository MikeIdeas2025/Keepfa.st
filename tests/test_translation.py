"""Tests for translation layer — TC-009, TC-010."""

import pytest

from keepfast.translation.plain_language import TranslationLayer


@pytest.fixture()
def translator():
    return TranslationLayer()


class TestLanguageDetection:
    def test_detect_italian(self, translator):
        assert translator.detect_language("come sono i dati del mese scorso?") == "it"

    def test_detect_english(self, translator):
        assert translator.detect_language("how are my users doing?") == "en"

    def test_default_to_english(self, translator):
        assert translator.detect_language("xyz abc 123") == "en"


class TestCohortTranslation:
    """TC-009: Cohort output in EN and IT."""

    def test_cohort_english(self, translator):
        data = {
            "cohorts": [
                {"name": "Jan 2026", "size": 45, "retention": [100, 67, 45]},
                {"name": "Feb 2026", "size": 30, "retention": [100, 50]},
            ],
            "average_retention": [100, 58, 45],
            "trend": "declining",
            "confidence": "medium",
            "total_users": 75,
        }
        result = translator.translate("cohort", data, language="en")
        assert "Jan 2026" in result
        assert "came back" in result
        assert "declining" in result.lower() or "coming back less" in result.lower()

    def test_cohort_italian(self, translator):
        data = {
            "cohorts": [
                {"name": "Gen 2026", "size": 45, "retention": [100, 67, 45]},
            ],
            "average_retention": [100, 67, 45],
            "trend": "stable",
            "confidence": "medium",
            "total_users": 45,
        }
        result = translator.translate("cohort", data, language="it")
        assert "è tornato" in result
        assert "utenti" in result


class TestFunnelTranslation:
    def test_funnel_english(self, translator):
        data = {
            "steps": [
                {"name": "signup", "count": 100, "rate": 100},
                {"name": "onboarding", "count": 60, "rate": 60},
                {"name": "first_action", "count": 35, "rate": 35},
            ],
            "biggest_drop": {
                "from": "onboarding",
                "to": "first_action",
                "drop_rate": 42,
                "users_lost": 25,
            },
            "overall_conversion": 35,
            "confidence": "medium",
        }
        result = translator.translate("funnel", data, language="en")
        assert "critical point" in result.lower() or "stop here" in result.lower()
        assert "25" in result
        assert "35%" in result

    def test_funnel_italian(self, translator):
        data = {
            "steps": [
                {"name": "signup", "count": 50, "rate": 100},
                {"name": "onboarding", "count": 20, "rate": 40},
            ],
            "biggest_drop": {
                "from": "signup",
                "to": "onboarding",
                "drop_rate": 60,
                "users_lost": 30,
            },
            "overall_conversion": 40,
            "confidence": "low",
        }
        result = translator.translate("funnel", data, language="it")
        assert "punto critico" in result.lower() or "si fermano" in result.lower()


class TestTrendTranslation:
    def test_trend_growing(self, translator):
        data = {
            "metric": "active_users",
            "data_points": [
                {"period": "2026-W01", "value": 100},
                {"period": "2026-W02", "value": 110},
                {"period": "2026-W03", "value": 120},
            ],
            "direction": "growing",
            "change_rate": 9.1,
            "anomalies": [],
            "confidence": "medium",
            "total_users": 50,
        }
        result = translator.translate("trend", data, language="en")
        assert "growing" in result.lower()
        assert "9.1%" in result

    def test_trend_with_anomaly(self, translator):
        data = {
            "metric": "events_count",
            "data_points": [{"period": f"W{i}", "value": 10} for i in range(5)],
            "direction": "stable",
            "change_rate": 0,
            "anomalies": [{"period": "W4", "expected": 10, "actual": 30, "severity": "severe"}],
            "confidence": "low",
            "total_users": 10,
        }
        result = translator.translate("trend", data, language="en")
        assert "unusual" in result.lower()
        assert "30" in result


class TestZeroDataTemplates:
    """TC-010: Zero data scenarios produce helpful messages."""

    def test_zero_cohort_en(self, translator):
        result = translator.translate("cohort", {"cohorts": []}, language="en")
        assert "don't have any event data" in result.lower() or "start tracking" in result.lower()

    def test_zero_cohort_it(self, translator):
        result = translator.translate("cohort", {"cohorts": []}, language="it")
        assert "non ho ancora dati" in result.lower() or "tracciare" in result.lower()

    def test_zero_funnel_en(self, translator):
        data = {"steps": [{"name": "signup", "count": 0, "rate": 0}], "confidence": "low"}
        result = translator.translate("funnel", data, language="en")
        assert "don't have" in result.lower() or "no" in result.lower()

    def test_zero_segment_en(self, translator):
        data = {
            "segment_a": {"name": "paying", "size": 0, "metric_value": 0},
            "segment_b": {"name": "free", "size": 0, "metric_value": 0},
            "confidence": "low",
        }
        result = translator.translate("segment", data, language="en")
        assert "don't have" in result.lower()


class TestSegmentTranslation:
    def test_segment_english(self, translator):
        data = {
            "segment_a": {"name": "paying", "size": 50, "metric_value": 72},
            "segment_b": {"name": "free", "size": 200, "metric_value": 31},
            "difference": 41,
            "winner": "paying",
            "statistically_significant": False,
            "confidence": "low",
        }
        result = translator.translate("segment", data, language="en")
        assert "paying" in result
        assert "ahead" in result
        assert (
            "too small" in result.lower()
            or "not confident" in result.lower()
            or "numbers are too small" in result.lower()
        )


class TestOMTMTranslation:
    def test_omtm_english(self, translator):
        data = {
            "suggested_metric": "week_1_retention",
            "current_value": 34,
            "target_value": 50,
            "reasoning": "People try your product but don't come back.",
            "stage": "retention",
        }
        result = translator.translate("omtm", data, language="en")
        assert "focus on" in result.lower()
        assert "34" in result

    def test_omtm_italian(self, translator):
        data = {
            "suggested_metric": "new_users_per_week",
            "current_value": 5,
            "target_value": 10,
            "reasoning": "Hai pochi utenti.",
            "stage": "acquisition",
        }
        result = translator.translate("omtm", data, language="it")
        assert "concentrarti" in result.lower()


class TestNoJargon:
    """Scan output for banned jargon words."""

    BANNED_WORDS = ["cohort", "OMTM", "retention curve", "churn rate"]

    def _assert_no_jargon(self, text: str):
        for word in self.BANNED_WORDS:
            assert word.lower() not in text.lower(), (
                f"Found jargon word '{word}' in output: {text[:100]}..."
            )

    def test_cohort_output_no_jargon(self, translator):
        data = {
            "cohorts": [{"name": "Jan 2026", "size": 40, "retention": [100, 60]}],
            "trend": "stable",
            "confidence": "medium",
            "total_users": 40,
        }
        result = translator.translate("cohort", data, language="en")
        self._assert_no_jargon(result)

    def test_funnel_output_no_jargon(self, translator):
        data = {
            "steps": [
                {"name": "signup", "count": 50, "rate": 100},
                {"name": "purchase", "count": 10, "rate": 20},
            ],
            "biggest_drop": {"from": "signup", "to": "purchase", "drop_rate": 80, "users_lost": 40},
            "overall_conversion": 20,
            "confidence": "medium",
        }
        result = translator.translate("funnel", data, language="en")
        self._assert_no_jargon(result)

    def test_omtm_output_no_jargon(self, translator):
        data = {
            "suggested_metric": "week_1_retention",
            "current_value": 34,
            "target_value": 50,
            "reasoning": "People try your product but don't come back.",
            "stage": "retention",
        }
        result = translator.translate("omtm", data, language="en")
        self._assert_no_jargon(result)

    def test_trend_output_no_jargon(self, translator):
        data = {
            "metric": "active_users",
            "data_points": [{"period": "W1", "value": 10}],
            "direction": "stable",
            "change_rate": 0,
            "anomalies": [],
            "confidence": "low",
            "total_users": 10,
        }
        result = translator.translate("trend", data, language="en")
        self._assert_no_jargon(result)
