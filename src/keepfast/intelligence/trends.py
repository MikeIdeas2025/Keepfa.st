"""Metric trends and anomaly detection."""

import statistics
from collections import defaultdict
from datetime import datetime


class TrendAnalyzer:
    """Shows metric trends and flags anomalies."""

    SUPPORTED_METRICS = {
        "active_users",
        "new_users",
        "churned_users",
        "mrr",
        "subscriptions",
        "events_count",
    }

    def get_trend(
        self,
        users: list,
        events: list,
        subscriptions: list,
        metric: str,
        granularity: str = "weekly",
    ) -> dict:
        if metric not in self.SUPPORTED_METRICS:
            return {
                "metric": metric,
                "error": (
                    f"Unknown metric '{metric}'. "
                    f"Available: {', '.join(sorted(self.SUPPORTED_METRICS))}"
                ),
            }

        if not users and not events:
            return {
                "metric": metric,
                "granularity": granularity,
                "data_points": [],
                "direction": "insufficient_data",
                "change_rate": 0,
                "anomalies": [],
                "confidence": "low",
                "total_users": 0,
            }

        data_points = self._calculate_metric(users, events, subscriptions, metric, granularity)

        if len(data_points) < 2:
            return {
                "metric": metric,
                "granularity": granularity,
                "data_points": data_points,
                "direction": "insufficient_data",
                "change_rate": 0,
                "anomalies": [],
                "confidence": "low",
                "total_users": len(users),
            }

        # Direction
        last = data_points[-1]["value"]
        prev = data_points[-2]["value"]
        if prev > 0:
            change_rate = round((last - prev) / prev * 100, 1)
        else:
            change_rate = 0.0

        if change_rate > 5:
            direction = "growing"
        elif change_rate < -5:
            direction = "declining"
        else:
            direction = "stable"

        # Anomalies
        anomalies = self._detect_anomalies(data_points)

        confidence = self._confidence_level(len(users))

        return {
            "metric": metric,
            "granularity": granularity,
            "data_points": data_points,
            "direction": direction,
            "change_rate": change_rate,
            "anomalies": anomalies,
            "confidence": confidence,
            "total_users": len(users),
        }

    def _calculate_metric(
        self, users: list, events: list, subscriptions: list, metric: str, granularity: str
    ) -> list[dict]:
        if metric == "active_users":
            return self._active_users_by_period(events, granularity)
        elif metric == "new_users":
            return self._new_users_by_period(users, granularity)
        elif metric == "events_count":
            return self._events_count_by_period(events, granularity)
        elif metric == "mrr":
            return self._mrr_by_period(subscriptions, granularity)
        elif metric == "subscriptions":
            return self._subscriptions_by_period(subscriptions, granularity)
        elif metric == "churned_users":
            return self._churned_users_by_period(users, events, granularity)
        return []

    def _period_key(self, dt: datetime, granularity: str) -> str:
        if granularity == "daily":
            return dt.strftime("%Y-%m-%d")
        elif granularity == "weekly":
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        return f"{dt.year}-{dt.month:02d}"

    def _active_users_by_period(self, events: list, granularity: str) -> list[dict]:
        period_users: dict[str, set[str]] = defaultdict(set)
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                key = self._period_key(dt, granularity)
                period_users[key].add(event.user_id)
            except (ValueError, AttributeError):
                continue

        return [{"period": k, "value": len(v)} for k, v in sorted(period_users.items())]

    def _new_users_by_period(self, users: list, granularity: str) -> list[dict]:
        period_count: dict[str, int] = defaultdict(int)
        for user in users:
            if user.first_seen:
                try:
                    dt = datetime.fromisoformat(user.first_seen.replace("Z", "+00:00"))
                    key = self._period_key(dt, granularity)
                    period_count[key] += 1
                except ValueError:
                    continue

        return [{"period": k, "value": v} for k, v in sorted(period_count.items())]

    def _events_count_by_period(self, events: list, granularity: str) -> list[dict]:
        period_count: dict[str, int] = defaultdict(int)
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                key = self._period_key(dt, granularity)
                period_count[key] += 1
            except (ValueError, AttributeError):
                continue

        return [{"period": k, "value": v} for k, v in sorted(period_count.items())]

    def _mrr_by_period(self, subscriptions: list, granularity: str) -> list[dict]:
        # Simplified: sum of active subscription MRR at creation time
        period_mrr: dict[str, int] = defaultdict(int)
        for sub in subscriptions:
            if sub.status in ("active", "trialing"):
                try:
                    dt = datetime.fromisoformat(sub.started_at.replace("Z", "+00:00"))
                    key = self._period_key(dt, granularity)
                    period_mrr[key] += sub.mrr_cents
                except (ValueError, AttributeError):
                    continue

        return [{"period": k, "value": v} for k, v in sorted(period_mrr.items())]

    def _subscriptions_by_period(self, subscriptions: list, granularity: str) -> list[dict]:
        period_count: dict[str, int] = defaultdict(int)
        for sub in subscriptions:
            try:
                dt = datetime.fromisoformat(sub.started_at.replace("Z", "+00:00"))
                key = self._period_key(dt, granularity)
                period_count[key] += 1
            except (ValueError, AttributeError):
                continue

        return [{"period": k, "value": v} for k, v in sorted(period_count.items())]

    def _churned_users_by_period(self, users: list, events: list, granularity: str) -> list[dict]:
        # Simplified: users who had events in period N but not in period N+1
        period_users: dict[str, set[str]] = defaultdict(set)
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                key = self._period_key(dt, granularity)
                period_users[key].add(event.user_id)
            except (ValueError, AttributeError):
                continue

        sorted_periods = sorted(period_users.keys())
        results = []
        for i in range(1, len(sorted_periods)):
            prev_period = sorted_periods[i - 1]
            curr_period = sorted_periods[i]
            churned = period_users[prev_period] - period_users[curr_period]
            results.append({"period": curr_period, "value": len(churned)})

        return results

    def _detect_anomalies(self, data_points: list[dict]) -> list[dict]:
        if len(data_points) < 5:
            return []

        anomalies = []
        values = [dp["value"] for dp in data_points]

        for i in range(4, len(values)):
            window = values[i - 4 : i]
            avg = statistics.mean(window)
            if avg == 0:
                continue
            stdev = statistics.stdev(window) if len(set(window)) > 1 else 0
            if stdev == 0:
                continue

            deviation = abs(values[i] - avg)
            ratio = deviation / stdev

            if ratio >= 1.5:
                if ratio >= 3:
                    severity = "severe"
                elif ratio >= 2:
                    severity = "notable"
                else:
                    severity = "mild"

                anomalies.append(
                    {
                        "period": data_points[i]["period"],
                        "expected": round(avg),
                        "actual": values[i],
                        "severity": severity,
                    }
                )

        return anomalies

    def _confidence_level(self, total_users: int) -> str:
        if total_users < 30:
            return "low"
        if total_users <= 100:
            return "medium"
        return "high"
