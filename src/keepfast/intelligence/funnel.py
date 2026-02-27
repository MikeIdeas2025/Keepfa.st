"""Funnel analysis and drop-off detection."""

from collections import defaultdict
from datetime import datetime, timezone


class FunnelAnalyzer:
    """Identifies where users drop off in a flow."""

    def analyze_funnel(
        self,
        events: list,
        steps: list[str],
        date_from: str = "",
        date_to: str = "",
    ) -> dict:
        """
        Args:
            events: list[UnifiedEvent]
            steps: ordered list of event names (normalized)
            date_from, date_to: ISO 8601 date strings for filtering

        Returns dict with steps, biggest_drop, overall_conversion, confidence.
        """
        if not steps:
            return {
                "steps": [],
                "biggest_drop": None,
                "overall_conversion": 0,
                "confidence": "low",
            }

        if not events:
            return {
                "steps": [{"name": s, "count": 0, "rate": 0} for s in steps],
                "biggest_drop": None,
                "overall_conversion": 0,
                "confidence": "low",
            }

        # Normalize step names to lowercase for case-insensitive matching
        normalized_steps = [s.lower() for s in steps]

        # Filter events by date range
        filtered = self._filter_by_date(events, date_from, date_to)

        # Group events by user, sorted by timestamp
        user_events: dict[str, list] = defaultdict(list)
        for event in filtered:
            user_events[event.user_id].append(event)

        for uid in user_events:
            user_events[uid].sort(key=lambda e: e.timestamp)

        # For each user, check which funnel steps they completed (in order)
        step_counts = [0] * len(normalized_steps)

        for uid, evts in user_events.items():
            current_step = 0
            last_step_time = None

            for event in evts:
                if current_step >= len(normalized_steps):
                    break

                if event.event_name.lower() == normalized_steps[current_step]:
                    try:
                        event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    except ValueError:
                        continue

                    # Step N+1 must have timestamp > step N
                    if last_step_time is None or event_time > last_step_time:
                        step_counts[current_step] += 1
                        last_step_time = event_time
                        current_step += 1

        # Build step results
        total_entering = step_counts[0] if step_counts else 0
        step_results = []
        for i, step_name in enumerate(steps):
            count = step_counts[i]
            rate = round(count / total_entering * 100) if total_entering > 0 else 0
            step_results.append({"name": step_name, "count": count, "rate": rate})

        # Find biggest drop
        biggest_drop = None
        max_drop = 0
        for i in range(len(step_results) - 1):
            users_lost = step_results[i]["count"] - step_results[i + 1]["count"]
            if users_lost > max_drop:
                max_drop = users_lost
                drop_rate = (
                    round(users_lost / step_results[i]["count"] * 100)
                    if step_results[i]["count"] > 0
                    else 0
                )
                biggest_drop = {
                    "from": step_results[i]["name"],
                    "to": step_results[i + 1]["name"],
                    "drop_rate": drop_rate,
                    "users_lost": users_lost,
                }

        overall_conversion = step_results[-1]["rate"] if step_results else 0

        confidence = self._confidence_level(total_entering)

        return {
            "steps": step_results,
            "biggest_drop": biggest_drop,
            "overall_conversion": overall_conversion,
            "confidence": confidence,
        }

    def _filter_by_date(self, events: list, date_from: str, date_to: str) -> list:
        if not date_from and not date_to:
            return events

        from_dt = self._parse_date(date_from) if date_from else None
        to_dt = self._parse_date(date_to) if date_to else None

        filtered = []
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            if from_dt and dt < from_dt:
                continue
            if to_dt and dt > to_dt:
                continue
            filtered.append(event)

        return filtered

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _confidence_level(self, total_entering: int) -> str:
        if total_entering < 30:
            return "low"
        if total_entering <= 100:
            return "medium"
        return "high"
