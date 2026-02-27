"""Customer Lifetime Value calculation + Kumar segmentation."""

from collections import defaultdict
from datetime import datetime, timezone


class CLVAnalyzer:
    """Calculates CLV per customer and applies Kumar segmentation."""

    def analyze(
        self,
        users: list,
        events: list,
        subscriptions: list,
        discount_rate: float = 0.1,
    ) -> dict:
        """
        Args:
            users: list[UnifiedUser]
            events: list[UnifiedEvent]
            subscriptions: list[SubscriptionInfo]
            discount_rate: annual discount rate for CLV formula

        Returns dict with customers, segments, loyalty_plan, total_portfolio_clv, confidence.
        """
        if not users:
            return {
                "customers": [],
                "segments": {s: {"count": 0, "total_clv": 0, "avg_clv": 0} for s in self.SEGMENTS},
                "loyalty_plan": [],
                "total_portfolio_clv": 0,
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

        customers = []
        for user in users:
            user_events = events_by_user.get(user.internal_id, [])
            user_subs = subs_by_user.get(user.internal_id, [])

            mrr_cents = sum(s.mrr_cents for s in user_subs if s.status in ("active", "trialing"))
            mrr = mrr_cents / 100.0

            retention_prob = self._estimate_retention(user_events, user_subs, now)
            lifetime_months = self._estimate_lifetime(user_subs, now)
            margin = mrr * 0.8  # assume 80% gross margin
            clv = self._calculate_clv(margin, retention_prob, discount_rate)

            customers.append(
                {
                    "email": user.email,
                    "clv": round(clv, 2),
                    "mrr": round(mrr, 2),
                    "retention_probability": round(retention_prob, 2),
                    "lifetime_months": lifetime_months,
                    "internal_id": user.internal_id,
                }
            )

        # Assign Kumar segments
        clv_values = [c["clv"] for c in customers]
        clv_values_sorted = sorted(clv_values)
        q75_idx = max(0, int(len(clv_values_sorted) * 0.75) - 1)
        clv_q75 = clv_values_sorted[q75_idx] if clv_values_sorted else 0

        for customer in customers:
            user_events = events_by_user.get(customer["internal_id"], [])
            engagement = self._engagement_level(user_events, now)
            customer["segment"] = self._assign_segment(customer["clv"], clv_q75, engagement)
            del customer["internal_id"]  # remove internal field from output

        # Aggregate segments
        segments: dict[str, dict] = {s: {"count": 0, "total_clv": 0.0} for s in self.SEGMENTS}
        for c in customers:
            seg = c["segment"]
            if seg in segments:
                segments[seg]["count"] += 1
                segments[seg]["total_clv"] += c["clv"]

        for seg_data in segments.values():
            seg_data["total_clv"] = round(seg_data["total_clv"], 2)
            seg_data["avg_clv"] = (
                round(seg_data["total_clv"] / seg_data["count"], 2) if seg_data["count"] else 0
            )

        total_clv = round(sum(c["clv"] for c in customers), 2)
        loyalty_plan = self._generate_loyalty_plan(segments)

        return {
            "customers": customers,
            "segments": segments,
            "loyalty_plan": loyalty_plan,
            "total_portfolio_clv": total_clv,
            "confidence": self._confidence_level(len(users)),
        }

    SEGMENTS = ["Champions", "Advocates", "Affluents", "Misers"]

    def _calculate_clv(self, margin: float, retention: float, discount: float) -> float:
        denominator = 1 + discount - retention
        if denominator <= 0:
            # Avoid division by zero / negative — cap at high value
            return margin * 120 if margin > 0 else 0
        return (margin * retention) / denominator

    def _estimate_retention(self, user_events: list, user_subs: list, now: datetime) -> float:
        if not user_events and not user_subs:
            return 0.0

        score = 0.5  # base

        # Event recency boost
        if user_events:
            timestamps = [self._parse_ts(e.timestamp) for e in user_events]
            timestamps = [t for t in timestamps if t is not None]
            if timestamps:
                latest = max(timestamps)
                days_ago = (now - latest).days
                if days_ago <= 3:
                    score += 0.3
                elif days_ago <= 7:
                    score += 0.2
                elif days_ago <= 14:
                    score += 0.1
                elif days_ago > 30:
                    score -= 0.2

        # Event frequency boost
        if len(user_events) > 20:
            score += 0.1
        elif len(user_events) > 10:
            score += 0.05

        # Active subscription boost
        active_subs = [s for s in user_subs if s.status in ("active", "trialing")]
        if active_subs:
            score += 0.1
        canceled = [s for s in user_subs if s.status == "canceled"]
        if canceled:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def _estimate_lifetime(self, user_subs: list, now: datetime) -> int:
        if not user_subs:
            return 0
        earliest_start = None
        for sub in user_subs:
            ts = self._parse_ts(sub.started_at)
            if ts and (earliest_start is None or ts < earliest_start):
                earliest_start = ts
        if earliest_start is None:
            return 0
        months = max(1, (now - earliest_start).days // 30)
        return months

    def _engagement_level(self, user_events: list, now: datetime) -> str:
        if not user_events:
            return "low"
        timestamps = [self._parse_ts(e.timestamp) for e in user_events]
        timestamps = [t for t in timestamps if t is not None]
        if not timestamps:
            return "low"
        latest = max(timestamps)
        earliest = min(timestamps)
        days_active = (latest - earliest).days
        if days_active > 60 and len(user_events) > 15:
            return "high"
        if days_active > 14 and len(user_events) > 5:
            return "medium"
        return "low"

    def _assign_segment(self, clv: float, clv_q75: float, engagement: str) -> str:
        high_clv = clv >= clv_q75 and clv > 0

        if high_clv and engagement == "high":
            return "Champions"
        if high_clv and engagement == "medium":
            return "Advocates"
        if high_clv and engagement == "low":
            return "Affluents"
        # Low CLV
        return "Misers"

    def _generate_loyalty_plan(self, segments: dict[str, dict]) -> list[str]:
        plan = []

        champions = segments.get("Champions", {})
        advocates = segments.get("Advocates", {})
        affluents = segments.get("Affluents", {})
        misers = segments.get("Misers", {})

        if champions.get("count", 0) > 0:
            plan.append(
                f"Step 1: Nurture your {champions['count']} Champions — "
                "they're your most valuable customers. Ask for referrals and testimonials."
            )
        else:
            plan.append(
                "Step 1: You don't have Champions yet — focus on converting "
                "your best customers into long-term advocates."
            )

        if advocates.get("count", 0) > 0:
            plan.append(
                f"Step 2: Engage your {advocates['count']} Advocates more deeply — "
                "increase their feature usage to move them toward Champion status."
            )
        else:
            plan.append(
                "Step 2: Build advocacy by encouraging high-value customers "
                "to use more features and stay longer."
            )

        if affluents.get("count", 0) > 0:
            plan.append(
                f"Step 3: Re-engage your {affluents['count']} Affluents — "
                "they pay well but aren't using the product much. "
                "Show them value before they churn."
            )
        else:
            plan.append("Step 3: Watch for high-paying customers who stop engaging — act fast.")

        if misers.get("count", 0) > 0:
            plan.append(
                f"Step 4: Evaluate your {misers['count']} Misers — "
                "consider whether upselling or improving onboarding could increase their value."
            )
        else:
            plan.append("Step 4: Ensure new customers see value quickly to avoid low-CLV patterns.")

        plan.append(
            "Step 5: Review this analysis monthly — track how customers move between segments."
        )

        return plan

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
