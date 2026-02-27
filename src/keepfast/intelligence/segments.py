"""Segment comparison."""

from datetime import datetime, timedelta, timezone


class SegmentAnalyzer:
    """Compares two segments of users on a metric."""

    def compare(
        self,
        users: list,
        events: list,
        subscriptions: list,
        segment_a: str,
        segment_b: str,
        metric: str,
    ) -> dict:
        now = datetime.now(tz=timezone.utc)

        users_a = self._get_segment_users(users, events, subscriptions, segment_a, now)
        users_b = self._get_segment_users(users, events, subscriptions, segment_b, now)

        metric_a = self._calculate_segment_metric(users_a, events, subscriptions, metric, now)
        metric_b = self._calculate_segment_metric(users_b, events, subscriptions, metric, now)

        size_a = len(users_a)
        size_b = len(users_b)

        diff = round(metric_a - metric_b, 1)
        winner = segment_a if metric_a >= metric_b else segment_b

        # Always False if <30 in either segment
        statistically_significant = size_a >= 30 and size_b >= 30

        min_size = min(size_a, size_b)
        if min_size < 30:
            confidence = "low"
        elif min_size <= 100:
            confidence = "medium"
        else:
            confidence = "high"

        return {
            "segment_a": {"name": segment_a, "size": size_a, "metric_value": round(metric_a, 1)},
            "segment_b": {"name": segment_b, "size": size_b, "metric_value": round(metric_b, 1)},
            "difference": abs(diff),
            "winner": winner,
            "statistically_significant": statistically_significant,
            "confidence": confidence,
        }

    def _get_segment_users(
        self, users: list, events: list, subscriptions: list, segment: str, now: datetime
    ) -> list:
        sub_user_ids = {s.user_id for s in subscriptions if s.status in ("active", "trialing")}

        # Build last event time per user
        last_event: dict[str, datetime] = {}
        for event in events:
            try:
                dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                if event.user_id not in last_event or dt > last_event[event.user_id]:
                    last_event[event.user_id] = dt
            except ValueError:
                continue

        result = []
        for user in users:
            match segment:
                case "paying":
                    if user.internal_id in sub_user_ids:
                        result.append(user)
                case "free":
                    if user.internal_id not in sub_user_ids:
                        result.append(user)
                case "new":
                    if user.first_seen:
                        try:
                            dt = datetime.fromisoformat(user.first_seen.replace("Z", "+00:00"))
                            if (now - dt) < timedelta(days=30):
                                result.append(user)
                        except ValueError:
                            continue
                case "returning":
                    if user.first_seen:
                        try:
                            dt = datetime.fromisoformat(user.first_seen.replace("Z", "+00:00"))
                            if (now - dt) >= timedelta(days=30):
                                result.append(user)
                        except ValueError:
                            continue
                case "active":
                    uid = user.internal_id
                    if uid in last_event and (now - last_event[uid]) < timedelta(days=7):
                        result.append(user)
                case "inactive":
                    uid = user.internal_id
                    if uid not in last_event or (now - last_event[uid]) >= timedelta(days=7):
                        result.append(user)
                case _:
                    # Unknown segment — return empty
                    pass

        return result

    def _calculate_segment_metric(
        self, segment_users: list, events: list, subscriptions: list, metric: str, now: datetime
    ) -> float:
        if not segment_users:
            return 0.0

        user_ids = {u.internal_id for u in segment_users}

        if metric == "retention":
            # Percentage who had events in the last 30 days
            recent_active = set()
            cutoff = now - timedelta(days=30)
            for event in events:
                try:
                    dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    if dt >= cutoff and event.user_id in user_ids:
                        recent_active.add(event.user_id)
                except ValueError:
                    continue
            return round(len(recent_active) / len(segment_users) * 100, 1)

        elif metric == "active_users":
            return float(len(segment_users))

        elif metric == "mrr":
            total = sum(
                s.mrr_cents
                for s in subscriptions
                if s.user_id in user_ids and s.status in ("active", "trialing")
            )
            return total / 100  # Convert cents to dollars

        elif metric == "events_per_user":
            user_event_count = sum(1 for e in events if e.user_id in user_ids)
            return round(user_event_count / len(segment_users), 1)

        return 0.0
