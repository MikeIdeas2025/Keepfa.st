"""Dirty data handling — normalize event names, clean events, detect onboarding."""

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone

from keepfast.normalizer.schema import UnifiedEvent

logger = logging.getLogger(__name__)


class DataCleaner:
    """Normalizes messy vibecoder data into clean, consistent formats."""

    def normalize_event_name(self, name: str) -> str:
        if not name:
            return ""

        # Preserve PostHog auto-capture events with $ prefix
        if name.startswith("$"):
            return name

        # Replace hyphens and spaces with underscores
        result = name.replace("-", "_").replace(" ", "_")

        # Insert underscore before uppercase letters (camelCase/PascalCase → snake_case)
        result = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", result)
        result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)

        # Lowercase everything
        result = result.lower()

        # Collapse multiple underscores
        result = re.sub(r"_+", "_", result)

        # Strip leading/trailing underscores
        result = result.strip("_")

        return result

    def clean_events(self, events: list[dict], user_id: str = "") -> list[UnifiedEvent]:
        cleaned: list[UnifiedEvent] = []
        for raw in events:
            try:
                event_name = raw.get("event", "")
                if not event_name:
                    logger.warning("Skipping event with no name: %s", raw)
                    continue

                timestamp = raw.get("timestamp", "")
                if not timestamp:
                    logger.warning("Skipping event with no timestamp: %s", raw)
                    continue

                cleaned.append(
                    UnifiedEvent(
                        user_id=user_id or raw.get("distinct_id", ""),
                        event_name=self.normalize_event_name(event_name),
                        original_name=event_name,
                        timestamp=timestamp,
                        source="posthog",
                        properties=raw.get("properties", {}),
                    )
                )
            except (KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping malformed event: %s — %s", raw, e)
                continue

        return cleaned

    def detect_likely_onboarding_events(self, events: list[UnifiedEvent]) -> list[str]:
        if not events:
            return []

        # Group events by user
        user_events: dict[str, list[UnifiedEvent]] = defaultdict(list)
        for event in events:
            user_events[event.user_id].append(event)

        total_users = len(user_events)
        if total_users == 0:
            return []

        # Find each user's first event timestamp
        user_first_seen: dict[str, datetime] = {}
        for uid, evts in user_events.items():
            timestamps = []
            for e in evts:
                try:
                    timestamps.append(datetime.fromisoformat(e.timestamp.replace("Z", "+00:00")))
                except ValueError:
                    continue
            if timestamps:
                user_first_seen[uid] = min(timestamps)

        # Count how many users fired each event within 24h of their first event
        event_early_users: dict[str, int] = defaultdict(int)
        for uid, evts in user_events.items():
            first = user_first_seen.get(uid)
            if not first:
                continue
            cutoff = first.replace(tzinfo=timezone.utc) if first.tzinfo is None else first
            seen_events: set[str] = set()
            for e in evts:
                try:
                    ts = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
                except ValueError:
                    continue
                ts_aware = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
                hours_diff = (ts_aware - cutoff).total_seconds() / 3600
                if hours_diff <= 24 and e.event_name not in seen_events:
                    event_early_users[e.event_name] += 1
                    seen_events.add(e.event_name)

        # Events fired by >60% of users in first 24h
        threshold = total_users * 0.6
        onboarding = [name for name, count in event_early_users.items() if count >= threshold]

        return sorted(onboarding)
