"""OMTM (One Metric That Matters) selection by stage."""

from datetime import datetime


class OMTMSelector:
    """Suggests the one metric that matters most for the current stage."""

    def suggest_omtm(
        self,
        users: list,
        events: list,
        subscriptions: list,
    ) -> dict:
        total_users = len(users)

        # Calculate key indicators
        paying_users = sum(1 for s in subscriptions if s.status in ("active", "trialing"))

        # Onboarding completion rate (heuristic: users who have >3 distinct events)
        user_event_counts: dict[str, int] = {}
        for event in events:
            user_event_counts[event.user_id] = user_event_counts.get(event.user_id, 0) + 1

        users_with_events = sum(1 for uid in user_event_counts if user_event_counts[uid] > 3)
        onboarding_rate = (users_with_events / total_users * 100) if total_users > 0 else 0

        # Month-1 retention (users who had events in 2 different months)
        user_months: dict[str, set[str]] = {}
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                month_key = f"{dt.year}-{dt.month:02d}"
                if event.user_id not in user_months:
                    user_months[event.user_id] = set()
                user_months[event.user_id].add(month_key)
            except ValueError:
                continue

        multi_month_users = sum(1 for months in user_months.values() if len(months) > 1)
        m1_retention = (multi_month_users / total_users * 100) if total_users > 0 else 0

        # Apply heuristic rules (ordered by priority)
        if total_users < 50:
            return {
                "suggested_metric": "new_users_per_week",
                "current_value": round(total_users / max(1, self._weeks_of_data(users))),
                "target_value": 10,
                "reasoning": self._reasoning("acquisition", total_users),
                "stage": "acquisition",
            }

        if onboarding_rate < 30:
            return {
                "suggested_metric": "onboarding_completion_rate",
                "current_value": round(onboarding_rate),
                "target_value": 50,
                "reasoning": self._reasoning("activation", onboarding_rate),
                "stage": "activation",
            }

        if m1_retention < 40:
            return {
                "suggested_metric": "week_1_retention",
                "current_value": round(m1_retention),
                "target_value": 50,
                "reasoning": self._reasoning("retention", m1_retention),
                "stage": "retention",
            }

        if paying_users < 10:
            return {
                "suggested_metric": "trial_to_paid_conversion",
                "current_value": round(paying_users / max(1, total_users) * 100),
                "target_value": 20,
                "reasoning": self._reasoning("revenue", paying_users),
                "stage": "revenue",
            }

        if paying_users >= 100 and m1_retention > 60:
            return {
                "suggested_metric": "referral_rate",
                "current_value": 0,  # Would need referral tracking
                "target_value": 10,
                "reasoning": self._reasoning("referral", paying_users),
                "stage": "referral",
            }

        # Default: focus on retention
        return {
            "suggested_metric": "week_1_retention",
            "current_value": round(m1_retention),
            "target_value": 60,
            "reasoning": self._reasoning("retention_default", m1_retention),
            "stage": "retention",
        }

    def _weeks_of_data(self, users: list) -> int:
        if not users:
            return 1
        dates = []
        for user in users:
            if user.first_seen:
                try:
                    dt = datetime.fromisoformat(user.first_seen.replace("Z", "+00:00"))
                    dates.append(dt)
                except ValueError:
                    continue
        if not dates:
            return 1
        span = max(dates) - min(dates)
        return max(1, span.days // 7)

    def _reasoning(self, stage: str, value: float) -> str:
        # Placeholder — will be overridden by TranslationLayer
        v = int(value)
        reasons = {
            "acquisition": (
                f"You have fewer than 50 users ({v} total). "
                "Focus on getting more people in the door."
            ),
            "activation": (
                f"Only {v}% of users complete onboarding. "
                "Fix the first experience before worrying about retention."
            ),
            "retention": (
                f"Month-1 retention is {v}%. People try your product but don't come back."
            ),
            "revenue": (f"Only {v} paying users. Focus on converting free users to paid."),
            "referral": (
                f"With {v} paying users and solid retention, it's time to grow through referrals."
            ),
            "retention_default": (f"Retention is at {v}%. Keep improving the core experience."),
        }
        return reasons.get(stage, "")
