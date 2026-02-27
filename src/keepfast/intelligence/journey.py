"""Joey Coleman's 8 emotional phases — customer journey mapping."""

from collections import defaultdict
from datetime import datetime, timezone

PHASES = ["Assess", "Admit", "Affirm", "Activate", "Acclimate", "Accomplish", "Adopt", "Advocate"]
PHASE_INDEX = {name: i for i, name in enumerate(PHASES)}


class JourneyOrchestrator:
    """Maps each customer to one of Joey Coleman's 8 journey phases."""

    def map_journey(self, users: list, events: list, subscriptions: list) -> dict:
        """
        Args:
            users: list[UnifiedUser]
            events: list[UnifiedEvent]
            subscriptions: list[SubscriptionInfo]

        Returns dict with phase_distribution, bottleneck, first_100_days,
        customers_by_phase, confidence.
        """
        if not users:
            return {
                "phase_distribution": [{"phase": p, "count": 0, "pct": 0} for p in PHASES],
                "bottleneck": None,
                "first_100_days": {
                    "users_in_window": 0,
                    "avg_phase": "Assess",
                    "completion_rate": 0,
                },
                "customers_by_phase": {p: [] for p in PHASES},
                "confidence": "low",
            }

        now = datetime.now(timezone.utc)

        # Index events by user_id
        events_by_user: dict[str, list] = defaultdict(list)
        for event in events:
            events_by_user[event.user_id].append(event)

        # Index subscriptions by user_id
        subs_by_user: dict[str, list] = defaultdict(list)
        for sub in subscriptions:
            subs_by_user[sub.user_id].append(sub)

        # Assign each user to their highest phase
        customers_by_phase: dict[str, list[str]] = {p: [] for p in PHASES}

        for user in users:
            user_events = events_by_user.get(user.internal_id, [])
            user_subs = subs_by_user.get(user.internal_id, [])
            first_seen = self._parse_ts(user.first_seen)

            phase = self._assign_phase(user_events, user_subs, first_seen, now)
            customers_by_phase[phase].append(user.email or user.internal_id)

        total = len(users)
        phase_distribution = [
            {
                "phase": p,
                "count": len(customers_by_phase[p]),
                "pct": round(len(customers_by_phase[p]) / total * 100) if total else 0,
            }
            for p in PHASES
        ]

        # Bottleneck: biggest drop-off between consecutive phases
        bottleneck = self._find_bottleneck(phase_distribution)

        # First 100 Days analysis
        first_100 = self._first_100_days(users, events_by_user, subs_by_user, now)

        return {
            "phase_distribution": phase_distribution,
            "bottleneck": bottleneck,
            "first_100_days": first_100,
            "customers_by_phase": customers_by_phase,
            "confidence": self._confidence_level(total),
        }

    def _assign_phase(
        self,
        user_events: list,
        user_subs: list,
        first_seen: datetime | None,
        now: datetime,
    ) -> str:
        if not user_events:
            return "Assess"

        event_names = {e.event_name for e in user_events}
        total_events = len(user_events)
        distinct_event_types = len(event_names)

        # Parse timestamps for time-based heuristics
        timestamps = [self._parse_ts(e.timestamp) for e in user_events]
        timestamps = [t for t in timestamps if t is not None]
        if not timestamps:
            return "Assess"

        earliest = min(timestamps)
        latest = max(timestamps)
        days_active = (latest - earliest).days
        # Has paying subscription?
        is_paying = any(s.status in ("active", "trialing") for s in user_subs)

        # Check each phase from highest to lowest (assign highest achieved)

        # Advocate: Active >60 days, high engagement + paying
        if days_active > 60 and total_events > 20 and is_paying:
            return "Advocate"

        # Adopt: Active >30 days, multi-month retention
        if days_active > 30 and self._has_multimonth_activity(timestamps):
            return "Adopt"

        # Accomplish: Active >14 days, has feature_used events
        if days_active > 14 and self._has_feature_usage(event_names):
            return "Accomplish"

        # Acclimate: Active in first 7 days, >5 distinct event types
        if days_active >= 7 and distinct_event_types > 5:
            return "Acclimate"

        # Activate: Has onboarding_complete event
        if self._has_onboarding_complete(event_names):
            return "Activate"

        # Affirm: Has >3 events in first 48h
        if self._events_in_first_48h(user_events, earliest) > 3:
            return "Affirm"

        # Admit: Has sign_up or onboarding event, <3 total events
        signup_events = {"sign_up", "signup", "onboarding_started", "register", "registered"}
        if event_names & signup_events:
            return "Admit"

        # Default: has events but doesn't match higher phases
        return "Admit" if total_events > 0 else "Assess"

    def _has_onboarding_complete(self, event_names: set[str]) -> bool:
        onboarding_names = {
            "onboarding_complete",
            "onboarding_completed",
            "onboarding_done",
            "onboarding_finished",
            "setup_complete",
            "setup_completed",
        }
        return bool(event_names & onboarding_names)

    def _has_feature_usage(self, event_names: set[str]) -> bool:
        feature_names = {"feature_used", "feature_activated", "action_performed"}
        return bool(event_names & feature_names)

    def _events_in_first_48h(self, user_events: list, earliest: datetime) -> int:
        count = 0
        for event in user_events:
            ts = self._parse_ts(event.timestamp)
            if ts and (ts - earliest).total_seconds() <= 48 * 3600:
                count += 1
        return count

    def _has_multimonth_activity(self, timestamps: list[datetime]) -> bool:
        months = set()
        for ts in timestamps:
            months.add((ts.year, ts.month))
        return len(months) >= 2

    def _find_bottleneck(self, phase_distribution: list[dict]) -> dict | None:
        max_drop = 0
        bottleneck = None
        for i in range(len(phase_distribution) - 1):
            current = phase_distribution[i]["count"]
            next_count = phase_distribution[i + 1]["count"]
            if current > 0:
                drop = current - next_count
                drop_pct = round(drop / current * 100) if current else 0
                if drop > max_drop:
                    max_drop = drop
                    bottleneck = {
                        "from": phase_distribution[i]["phase"],
                        "to": phase_distribution[i + 1]["phase"],
                        "drop_pct": drop_pct,
                    }
        return bottleneck

    def _first_100_days(
        self,
        users: list,
        events_by_user: dict[str, list],
        subs_by_user: dict[str, list],
        now: datetime,
    ) -> dict:
        users_in_window = []
        phase_indices = []

        for user in users:
            first_seen = self._parse_ts(user.first_seen)
            if first_seen and (now - first_seen).days <= 100:
                user_events = events_by_user.get(user.internal_id, [])
                user_subs = subs_by_user.get(user.internal_id, [])
                phase = self._assign_phase(user_events, user_subs, first_seen, now)
                users_in_window.append(user.email or user.internal_id)
                phase_indices.append(PHASE_INDEX[phase])

        total_in_window = len(users_in_window)
        if total_in_window == 0:
            return {
                "users_in_window": 0,
                "avg_phase": "Assess",
                "completion_rate": 0,
            }

        avg_idx = round(sum(phase_indices) / total_in_window)
        avg_idx = min(avg_idx, len(PHASES) - 1)
        adopt_idx = PHASE_INDEX["Adopt"]
        completed = sum(1 for idx in phase_indices if idx >= adopt_idx)

        return {
            "users_in_window": total_in_window,
            "avg_phase": PHASES[avg_idx],
            "completion_rate": round(completed / total_in_window * 100),
        }

    def _parse_ts(self, ts: str) -> datetime | None:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _confidence_level(self, total_users: int) -> str:
        if total_users < 30:
            return "low"
        if total_users <= 100:
            return "medium"
        return "high"
