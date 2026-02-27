"""Customer health scoring — activity, recency, monetary signals."""

from collections import defaultdict
from datetime import datetime, timezone


class CustomerHealthAnalyzer:
    """Diagnoses per-customer health and aggregate risk summary."""

    def diagnose(self, users: list, events: list, subscriptions: list) -> dict:
        """
        Args:
            users: list[UnifiedUser]
            events: list[UnifiedEvent]
            subscriptions: list[SubscriptionInfo]

        Returns dict with customers, summary, top_risk_factors, confidence.
        """
        if not users:
            return {
                "customers": [],
                "summary": {
                    "total": 0,
                    "healthy": 0,
                    "at_risk": 0,
                    "critical": 0,
                    "total_mrr_at_risk": 0,
                },
                "top_risk_factors": [],
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

        # Calculate average events per user (for activity scoring)
        event_counts = [len(events_by_user.get(u.internal_id, [])) for u in users]
        avg_events = sum(event_counts) / len(users) if users else 0

        # Calculate MRR values for percentile ranking
        mrr_values = []
        for user in users:
            user_subs = subs_by_user.get(user.internal_id, [])
            mrr = sum(s.mrr_cents for s in user_subs if s.status in ("active", "trialing"))
            mrr_values.append(mrr)
        sorted_mrr = sorted(mrr_values)

        customers = []
        all_risk_factors: dict[str, int] = defaultdict(int)

        for i, user in enumerate(users):
            user_events = events_by_user.get(user.internal_id, [])
            user_subs = subs_by_user.get(user.internal_id, [])
            mrr_cents = sum(s.mrr_cents for s in user_subs if s.status in ("active", "trialing"))

            activity_score = self._activity_score(user_events, avg_events)
            recency_score = self._recency_score(user_events, now)
            monetary_score = self._monetary_score(mrr_cents, sorted_mrr)

            health_score = round(activity_score * 0.4 + recency_score * 0.3 + monetary_score * 0.3)

            risk_level = self._risk_level(health_score)
            risk_factors = self._risk_factors(
                user_events, user_subs, activity_score, recency_score, monetary_score, now
            )

            for factor in risk_factors:
                all_risk_factors[factor] += 1

            customers.append(
                {
                    "email": user.email,
                    "health_score": health_score,
                    "risk_level": risk_level,
                    "activity_score": activity_score,
                    "recency_score": recency_score,
                    "monetary_score": monetary_score,
                    "risk_factors": risk_factors,
                    "mrr_cents": mrr_cents,
                }
            )

        # Summary
        healthy = sum(1 for c in customers if c["risk_level"] == "healthy")
        at_risk = sum(1 for c in customers if c["risk_level"] == "at_risk")
        critical = sum(1 for c in customers if c["risk_level"] == "critical")
        mrr_at_risk = sum(
            c["mrr_cents"] for c in customers if c["risk_level"] in ("at_risk", "critical")
        )

        # Top risk factors sorted by frequency
        top_factors = sorted(
            all_risk_factors.keys(), key=lambda k: all_risk_factors[k], reverse=True
        )

        return {
            "customers": customers,
            "summary": {
                "total": len(customers),
                "healthy": healthy,
                "at_risk": at_risk,
                "critical": critical,
                "total_mrr_at_risk": mrr_at_risk,
            },
            "top_risk_factors": top_factors[:5],
            "confidence": self._confidence_level(len(users)),
        }

    def _activity_score(self, user_events: list, avg_events: float) -> int:
        count = len(user_events)
        if avg_events <= 0:
            return 0 if count == 0 else 50
        ratio = count / avg_events
        return min(100, round(ratio * 50))

    def _recency_score(self, user_events: list, now: datetime) -> int:
        if not user_events:
            return 0
        latest = max(
            self._parse_ts(e.timestamp) for e in user_events if self._parse_ts(e.timestamp)
        )
        if latest is None:
            return 0
        days_ago = (now - latest).days
        if days_ago <= 1:
            return 100
        if days_ago <= 3:
            return 85
        if days_ago <= 7:
            return 70
        if days_ago <= 14:
            return 50
        if days_ago <= 30:
            return 30
        return 10

    def _monetary_score(self, mrr_cents: int, sorted_mrr: list[int]) -> int:
        if not sorted_mrr or max(sorted_mrr) == 0:
            return 0
        if mrr_cents == 0:
            return 0
        # Percentile rank
        rank = sum(1 for v in sorted_mrr if v <= mrr_cents)
        return round(rank / len(sorted_mrr) * 100)

    def _risk_level(self, health_score: int) -> str:
        if health_score > 70:
            return "healthy"
        if health_score >= 40:
            return "at_risk"
        return "critical"

    def _risk_factors(
        self,
        user_events: list,
        user_subs: list,
        activity_score: int,
        recency_score: int,
        monetary_score: int,
        now: datetime,
    ) -> list[str]:
        factors = []
        if not user_events:
            factors.append("No events recorded")
            return factors

        latest = max(
            self._parse_ts(e.timestamp) for e in user_events if self._parse_ts(e.timestamp)
        )
        if latest:
            days_ago = (now - latest).days
            if days_ago >= 14:
                factors.append("No events in 14+ days")
            elif days_ago >= 7:
                factors.append("No events in 7+ days")

        if activity_score < 30:
            factors.append("Below-average feature usage")

        if monetary_score == 0 and user_subs:
            canceled = [s for s in user_subs if s.status == "canceled"]
            if canceled:
                factors.append("Subscription canceled")

        if not user_subs:
            factors.append("No active subscription")

        return factors

    def _parse_ts(self, ts: str) -> datetime | None:
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
