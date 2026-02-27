"""Additional tests to boost coverage on trends, segments, funnel, and translation."""

from datetime import datetime, timedelta, timezone

from keepfast.intelligence.funnel import FunnelAnalyzer
from keepfast.intelligence.segments import SegmentAnalyzer
from keepfast.intelligence.trends import TrendAnalyzer
from keepfast.normalizer.schema import SubscriptionInfo, UnifiedEvent, UnifiedUser
from keepfast.translation.plain_language import TranslationLayer


def _user(uid, first_seen, email="", stripe_id=None):
    return UnifiedUser(
        internal_id=uid,
        email=email,
        posthog_distinct_id=uid,
        stripe_customer_id=stripe_id,
        first_seen=first_seen,
        last_seen=first_seen,
        is_matched=stripe_id is not None,
    )


def _event(uid, name, timestamp):
    return UnifiedEvent(
        user_id=uid,
        event_name=name,
        original_name=name,
        timestamp=timestamp,
        source="posthog",
    )


def _sub(uid, sub_id, status, mrr, started, canceled=None):
    return SubscriptionInfo(
        user_id=uid,
        stripe_subscription_id=sub_id,
        status=status,
        plan_name="Pro",
        mrr_cents=mrr,
        started_at=started,
        canceled_at=canceled,
    )


# --- Trends coverage ---


class TestTrendMetrics:
    """Cover all metric types in TrendAnalyzer."""

    def _make_users_and_events(self):
        users = [_user(f"u{i}", f"2025-12-{(i % 28) + 1:02d}T10:00:00Z") for i in range(10)]
        events = []
        for i in range(10):
            for week in range(6):
                day = 1 + week * 7 + (i % 5)
                if day <= 28:
                    events.append(_event(f"u{i}", "click", f"2025-12-{day:02d}T10:00:00Z"))
        return users, events

    def test_new_users_metric(self):
        users, events = self._make_users_and_events()
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "new_users", "weekly")
        assert result["metric"] == "new_users"
        assert len(result["data_points"]) > 0

    def test_events_count_metric(self):
        users, events = self._make_users_and_events()
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "events_count", "weekly")
        assert result["metric"] == "events_count"

    def test_active_users_metric(self):
        users, events = self._make_users_and_events()
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "active_users", "monthly")
        assert result["metric"] == "active_users"

    def test_mrr_metric(self):
        users = [_user("u1", "2025-12-01T10:00:00Z", stripe_id="cus_1")]
        subs = [
            _sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z"),
            _sub("u1", "sub_2", "active", 900, "2026-01-01T10:00:00Z"),
        ]
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, [], subs, "mrr", "monthly")
        assert result["metric"] == "mrr"
        assert len(result["data_points"]) >= 1

    def test_subscriptions_metric(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        subs = [_sub("u1", "sub_1", "active", 2900, "2025-12-01T10:00:00Z")]
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, [], subs, "subscriptions", "monthly")
        assert result["metric"] == "subscriptions"

    def test_churned_users_metric(self):
        users = [_user(f"u{i}", "2025-12-01T10:00:00Z") for i in range(5)]
        events = []
        # u0,u1,u2 active in Dec; only u0 active in Jan
        for i in range(3):
            events.append(_event(f"u{i}", "click", "2025-12-15T10:00:00Z"))
        events.append(_event("u0", "click", "2026-01-15T10:00:00Z"))
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "churned_users", "monthly")
        assert result["metric"] == "churned_users"
        # Should show churned users in Jan
        if result["data_points"]:
            jan = [dp for dp in result["data_points"] if "01" in dp["period"]]
            if jan:
                assert jan[0]["value"] >= 1

    def test_daily_granularity(self):
        users = [_user("u1", "2025-12-01T10:00:00Z")]
        events = [
            _event("u1", "click", "2025-12-01T10:00:00Z"),
            _event("u1", "click", "2025-12-02T10:00:00Z"),
            _event("u1", "click", "2025-12-03T10:00:00Z"),
        ]
        analyzer = TrendAnalyzer()
        result = analyzer.get_trend(users, events, [], "active_users", "daily")
        assert result["granularity"] == "daily"
        assert len(result["data_points"]) == 3


# --- Segments coverage ---


class TestSegmentMetrics:
    """Cover segment types and metric calculations."""

    def _make_data(self):
        now = datetime.now(tz=timezone.utc)
        recent = (now - timedelta(days=5)).isoformat()
        old = (now - timedelta(days=60)).isoformat()
        very_recent = (now - timedelta(days=2)).isoformat()

        users = [
            _user("u1", old, stripe_id="cus_1"),
            _user("u2", old),
            _user("u3", recent),
            _user("u4", recent),
        ]
        events = [
            _event("u1", "click", very_recent),
            _event("u1", "click", very_recent),
            _event("u3", "click", very_recent),
        ]
        subs = [_sub("u1", "sub_1", "active", 2900, old)]
        return users, events, subs

    def test_new_vs_returning(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "new", "returning", "active_users")
        assert result["segment_a"]["name"] == "new"
        assert result["segment_b"]["name"] == "returning"

    def test_active_vs_inactive(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "active", "inactive", "active_users")
        assert result["segment_a"]["size"] + result["segment_b"]["size"] <= len(users)

    def test_retention_metric(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "paying", "free", "retention")
        assert isinstance(result["segment_a"]["metric_value"], float)

    def test_mrr_metric(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "paying", "free", "mrr")
        assert result["segment_a"]["metric_value"] >= 0

    def test_events_per_user_metric(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "paying", "free", "events_per_user")
        assert isinstance(result["segment_a"]["metric_value"], float)

    def test_unknown_segment(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "unknown_seg", "free", "active_users")
        assert result["segment_a"]["size"] == 0

    def test_unknown_metric(self):
        users, events, subs = self._make_data()
        analyzer = SegmentAnalyzer()
        result = analyzer.compare(users, events, subs, "paying", "free", "unknown_metric")
        assert result["segment_a"]["metric_value"] == 0.0


# --- Funnel coverage ---


class TestFunnelDateFiltering:
    """Cover funnel date range filtering."""

    def test_filter_by_date_range(self):
        events = [
            _event("u1", "sign_up", "2025-11-01T10:00:00Z"),
            _event("u1", "purchase", "2025-11-02T10:00:00Z"),
            _event("u2", "sign_up", "2025-12-15T10:00:00Z"),
            _event("u2", "purchase", "2025-12-16T10:00:00Z"),
        ]
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(
            events,
            steps=["sign_up", "purchase"],
            date_from="2025-12-01",
            date_to="2025-12-31",
        )
        # Only u2 should be in range
        assert result["steps"][0]["count"] == 1

    def test_single_step_funnel(self):
        events = [_event("u1", "click", "2025-12-01T10:00:00Z")]
        analyzer = FunnelAnalyzer()
        result = analyzer.analyze_funnel(events, steps=["click"])
        assert result["steps"][0]["count"] == 1
        assert result["biggest_drop"] is None


# --- Translation coverage ---


class TestTranslationEdgeCases:
    """Cover translation paths not yet tested."""

    def test_unknown_analysis_type_en(self):
        t = TranslationLayer()
        result = t.translate("unknown_type", {}, language="en")
        assert "Unknown" in result

    def test_unknown_analysis_type_it(self):
        t = TranslationLayer()
        result = t.translate("unknown_type", {}, language="it")
        assert "non riconosciuto" in result

    def test_cohort_no_m1_data(self):
        t = TranslationLayer()
        data = {
            "cohorts": [{"name": "Jan 2026", "size": 10, "retention": [100]}],
            "trend": "insufficient_data",
            "confidence": "low",
            "total_users": 10,
        }
        result = t.translate("cohort", data, language="en")
        assert "not enough data" in result.lower()

    def test_cohort_improving_trend(self):
        t = TranslationLayer()
        data = {
            "cohorts": [{"name": "Jan", "size": 20, "retention": [100, 60]}],
            "trend": "improving",
            "confidence": "medium",
            "total_users": 20,
        }
        result = t.translate("cohort", data, language="en")
        assert "improving" in result.lower()

    def test_trend_declining(self):
        t = TranslationLayer()
        data = {
            "metric": "active_users",
            "data_points": [{"period": "W1", "value": 100}, {"period": "W2", "value": 80}],
            "direction": "declining",
            "change_rate": -20.0,
            "anomalies": [],
            "confidence": "medium",
            "total_users": 50,
        }
        result = t.translate("trend", data, language="en")
        assert "declining" in result.lower()

    def test_trend_italian(self):
        t = TranslationLayer()
        data = {
            "metric": "active_users",
            "data_points": [{"period": "W1", "value": 100}],
            "direction": "stable",
            "change_rate": 0,
            "anomalies": [],
            "confidence": "low",
            "total_users": 5,
        }
        result = t.translate("trend", data, language="it")
        assert "stabile" in result

    def test_trend_with_anomaly_italian(self):
        t = TranslationLayer()
        data = {
            "metric": "events",
            "data_points": [{"period": "W1", "value": 10}],
            "direction": "stable",
            "change_rate": 0,
            "anomalies": [{"period": "W1", "expected": 5, "actual": 10, "severity": "notable"}],
            "confidence": "low",
            "total_users": 5,
        }
        result = t.translate("trend", data, language="it")
        assert "insolito" in result

    def test_segment_italian(self):
        t = TranslationLayer()
        data = {
            "segment_a": {"name": "paying", "size": 5, "metric_value": 80},
            "segment_b": {"name": "free", "size": 20, "metric_value": 30},
            "difference": 50,
            "winner": "paying",
            "statistically_significant": False,
            "confidence": "low",
        }
        result = t.translate("segment", data, language="it")
        assert "vantaggio" in result

    def test_anomaly_standalone_en(self):
        t = TranslationLayer()
        data = {"anomalies": [{"period": "W5", "expected": 10, "actual": 30, "severity": "severe"}]}
        result = t.translate("anomaly", data, language="en")
        assert "unusual" in result.lower()

    def test_anomaly_standalone_it(self):
        t = TranslationLayer()
        data = {"anomalies": [{"period": "W5", "expected": 10, "actual": 30, "severity": "mild"}]}
        result = t.translate("anomaly", data, language="it")
        assert "insoliti" in result

    def test_anomaly_no_anomalies_en(self):
        t = TranslationLayer()
        result = t.translate("anomaly", {"anomalies": []}, language="en")
        assert "normal" in result.lower()

    def test_anomaly_no_anomalies_it(self):
        t = TranslationLayer()
        result = t.translate("anomaly", {"anomalies": []}, language="it")
        assert "norma" in result.lower()

    def test_zero_data_subscription(self):
        t = TranslationLayer()
        result = t._zero_data("subscription", "en")
        assert "subscriptions" in result.lower()

    def test_zero_data_matching(self):
        t = TranslationLayer()
        result = t._zero_data("matching", "en")
        assert "match" in result.lower()

    def test_confidence_high_no_disclaimer(self):
        t = TranslationLayer()
        result = t._confidence_disclaimer("high", 200, "en")
        assert result == ""

    def test_pct_to_ratio_extremes(self):
        t = TranslationLayer()
        assert t._pct_to_ratio(0) == "nobody"
        assert t._pct_to_ratio(100) == "everyone"
        assert t._pct_to_ratio(50) == "about 1 in 2"
        assert t._pct_to_ratio(10) == "about 1 in 10"
        assert t._pct_to_ratio(15) == "about 1 in 7"
        assert t._pct_to_ratio(20) == "about 1 in 5"
        assert t._pct_to_ratio(25) == "about 1 in 4"
        assert t._pct_to_ratio(40) == "about 2 in 5"
        assert t._pct_to_ratio(60) == "about 3 in 5"
        assert t._pct_to_ratio(75) == "about 3 in 4"
        assert t._pct_to_ratio(85) == "most"

    def test_funnel_english_with_steps(self):
        t = TranslationLayer()
        data = {
            "steps": [
                {"name": "signup", "count": 100, "rate": 100},
                {"name": "purchase", "count": 0, "rate": 0},
            ],
            "biggest_drop": {
                "from": "signup",
                "to": "purchase",
                "drop_rate": 100,
                "users_lost": 100,
            },
            "overall_conversion": 0,
            "confidence": "high",
        }
        result = t.translate("funnel", data, language="en")
        assert "100" in result

    def test_funnel_italian_output(self):
        t = TranslationLayer()
        data = {
            "steps": [
                {"name": "signup", "count": 10, "rate": 100},
                {"name": "buy", "count": 5, "rate": 50},
            ],
            "biggest_drop": {
                "from": "signup",
                "to": "buy",
                "drop_rate": 50,
                "users_lost": 5,
            },
            "overall_conversion": 50,
            "confidence": "low",
        }
        result = t.translate("funnel", data, language="it")
        assert "flusso" in result or "punto critico" in result.lower()

    def test_trend_growing_italian(self):
        t = TranslationLayer()
        data = {
            "metric": "active_users",
            "data_points": [{"period": "W1", "value": 100}, {"period": "W2", "value": 120}],
            "direction": "growing",
            "change_rate": 20.0,
            "anomalies": [],
            "confidence": "low",
            "total_users": 10,
        }
        result = t.translate("trend", data, language="it")
        assert "crescendo" in result

    def test_omtm_italian(self):
        t = TranslationLayer()
        data = {
            "suggested_metric": "trial_to_paid_conversion",
            "current_value": 5,
            "target_value": 20,
            "reasoning": "Pochi utenti paganti.",
            "stage": "revenue",
        }
        result = t.translate("omtm", data, language="it")
        assert "concentrarti" in result

    def test_cohort_italian_no_m1(self):
        t = TranslationLayer()
        data = {
            "cohorts": [{"name": "Gen 2026", "size": 5, "retention": [100]}],
            "trend": "insufficient_data",
            "confidence": "low",
            "total_users": 5,
        }
        result = t.translate("cohort", data, language="it")
        assert "mese successivo" in result

    def test_cohort_declining_italian(self):
        t = TranslationLayer()
        data = {
            "cohorts": [{"name": "Gen", "size": 10, "retention": [100, 30]}],
            "trend": "declining",
            "confidence": "low",
            "total_users": 10,
        }
        result = t.translate("cohort", data, language="it")
        assert "calo" in result

    def test_cohort_stable_italian(self):
        t = TranslationLayer()
        data = {
            "cohorts": [{"name": "Gen", "size": 10, "retention": [100, 50]}],
            "trend": "stable",
            "confidence": "low",
            "total_users": 10,
        }
        result = t.translate("cohort", data, language="it")
        assert "stabile" in result

    def test_segment_statistically_significant(self):
        t = TranslationLayer()
        data = {
            "segment_a": {"name": "paying", "size": 50, "metric_value": 80},
            "segment_b": {"name": "free", "size": 200, "metric_value": 30},
            "difference": 50,
            "winner": "paying",
            "statistically_significant": True,
            "confidence": "high",
        }
        result = t.translate("segment", data, language="en")
        assert "ahead" in result
        # Should NOT have "too small" disclaimer
        assert "too small" not in result.lower()
