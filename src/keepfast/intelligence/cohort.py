"""Cohort retention calculation."""

from collections import defaultdict
from datetime import datetime


class CohortAnalyzer:
    """Calculates retention by cohort — how many users come back after signing up."""

    def calculate_retention(
        self,
        users: list,
        events: list,
        cohort_period: str = "monthly",
        periods: int = 6,
    ) -> dict:
        """
        Args:
            users: list[UnifiedUser]
            events: list[UnifiedEvent]
            cohort_period: "monthly" or "weekly"
            periods: number of periods to analyze

        Returns dict with cohorts, average_retention, trend, confidence.
        """
        if not users or not events:
            return {
                "cohorts": [],
                "average_retention": [],
                "trend": "insufficient_data",
                "confidence": "low",
                "total_users": 0,
            }

        # Build user lookup and event index
        user_first_seen = {}
        for user in users:
            if user.first_seen:
                try:
                    dt = datetime.fromisoformat(user.first_seen.replace("Z", "+00:00"))
                    user_first_seen[user.internal_id] = dt
                except ValueError:
                    continue

        # Group events by user_id and period
        user_event_periods: dict[str, set[str]] = defaultdict(set)
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                period_key = self._period_key(dt, cohort_period)
                user_event_periods[event.user_id].add(period_key)
            except ValueError:
                continue

        # Assign users to cohorts based on first_seen
        cohort_users: dict[str, list[str]] = defaultdict(list)
        for uid, first_dt in user_first_seen.items():
            cohort_key = self._period_key(first_dt, cohort_period)
            cohort_users[cohort_key].append(uid)

        # Sort cohort keys chronologically
        sorted_cohorts = sorted(cohort_users.keys())

        # Generate all period keys from earliest to latest
        all_period_keys = self._generate_period_keys(sorted_cohorts, periods, cohort_period)

        # Calculate retention for each cohort
        cohort_results = []
        for cohort_key in sorted_cohorts:
            uids = cohort_users[cohort_key]
            size = len(uids)
            if size == 0:
                continue

            # Find the index of this cohort in all_period_keys
            if cohort_key not in all_period_keys:
                continue
            start_idx = all_period_keys.index(cohort_key)

            retention_pcts = []
            retention_abs = []
            for p in range(periods):
                period_idx = start_idx + p
                if period_idx >= len(all_period_keys):
                    break
                target_period = all_period_keys[period_idx]
                retained = sum(
                    1 for uid in uids if target_period in user_event_periods.get(uid, set())
                )
                retention_abs.append(retained)
                retention_pcts.append(round(retained / size * 100))

            if retention_pcts:
                cohort_results.append(
                    {
                        "name": self._format_period_name(cohort_key, cohort_period),
                        "size": size,
                        "retention": retention_pcts,
                        "absolute": retention_abs,
                    }
                )

        # Calculate average retention across cohorts
        avg_retention = self._calculate_average_retention(cohort_results, periods)

        # Determine trend
        trend = self._determine_trend(cohort_results)

        # Determine confidence
        total_users = sum(c["size"] for c in cohort_results)
        confidence = self._confidence_level(total_users)

        return {
            "cohorts": cohort_results,
            "average_retention": avg_retention,
            "trend": trend,
            "confidence": confidence,
            "total_users": total_users,
        }

    def _period_key(self, dt: datetime, period_type: str) -> str:
        if period_type == "weekly":
            iso = dt.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        return f"{dt.year}-{dt.month:02d}"

    def _format_period_name(self, key: str, period_type: str) -> str:
        if period_type == "weekly":
            return key  # "2026-W05"
        year, month = key.split("-")
        months = [
            "",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        return f"{months[int(month)]} {year}"

    def _generate_period_keys(
        self, cohort_keys: list[str], periods: int, period_type: str
    ) -> list[str]:
        if not cohort_keys:
            return []

        if period_type == "weekly":
            return self._generate_weekly_keys(cohort_keys, periods)
        return self._generate_monthly_keys(cohort_keys, periods)

    def _generate_monthly_keys(self, cohort_keys: list[str], periods: int) -> list[str]:
        if not cohort_keys:
            return []
        first = cohort_keys[0]
        last = cohort_keys[-1]
        year, month = map(int, first.split("-"))
        last_year, last_month = map(int, last.split("-"))

        # Generate enough keys to cover last cohort + periods
        total_months = (last_year - year) * 12 + (last_month - month) + periods
        keys = []
        for i in range(total_months):
            m = month + i
            y = year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            keys.append(f"{y}-{m:02d}")
        return keys

    def _generate_weekly_keys(self, cohort_keys: list[str], periods: int) -> list[str]:
        if not cohort_keys:
            return []

        # Parse first and last week
        first_year, first_week = self._parse_week_key(cohort_keys[0])
        last_year, last_week = self._parse_week_key(cohort_keys[-1])

        # Use datetime to generate weeks
        from datetime import timedelta

        start_dt = datetime.strptime(f"{first_year}-W{first_week:02d}-1", "%Y-W%W-%w")
        last_dt = datetime.strptime(f"{last_year}-W{last_week:02d}-1", "%Y-W%W-%w")
        total_weeks = int((last_dt - start_dt).days / 7) + periods

        keys = []
        for i in range(total_weeks):
            dt = start_dt + timedelta(weeks=i)
            iso = dt.isocalendar()
            keys.append(f"{iso[0]}-W{iso[1]:02d}")
        return keys

    def _parse_week_key(self, key: str) -> tuple[int, int]:
        parts = key.split("-W")
        return int(parts[0]), int(parts[1])

    def _calculate_average_retention(self, cohorts: list[dict], periods: int) -> list[int]:
        if not cohorts:
            return []

        avg = []
        for p in range(periods):
            values = [c["retention"][p] for c in cohorts if p < len(c["retention"])]
            if values:
                avg.append(round(sum(values) / len(values)))
            else:
                break
        return avg

    def _determine_trend(self, cohorts: list[dict]) -> str:
        if len(cohorts) < 2:
            return "insufficient_data"

        # Compare M1 retention (index 1) of recent vs early cohorts
        m1_values = [c["retention"][1] for c in cohorts if len(c["retention"]) > 1]
        if len(m1_values) < 2:
            return "insufficient_data"

        midpoint = len(m1_values) // 2
        early_avg = sum(m1_values[:midpoint]) / midpoint
        recent_avg = sum(m1_values[midpoint:]) / (len(m1_values) - midpoint)

        diff = recent_avg - early_avg
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        return "stable"

    def _confidence_level(self, total_users: int) -> str:
        if total_users < 30:
            return "low"
        if total_users <= 100:
            return "medium"
        return "high"
