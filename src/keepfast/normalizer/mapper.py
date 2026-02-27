"""Cross-platform user_id mapping — PostHog ↔ Stripe."""

import logging
import uuid
from datetime import datetime, timezone

from keepfast.normalizer.schema import SubscriptionInfo, UnifiedUser

logger = logging.getLogger(__name__)


class UserMapper:
    """Maps users across PostHog and Stripe using email as primary key."""

    def map_users(
        self, posthog_persons: list[dict], stripe_customers: list[dict]
    ) -> list[UnifiedUser]:
        # Index Stripe customers by email (lowercased)
        stripe_by_email: dict[str, dict] = {}
        for cust in stripe_customers:
            email = (cust.get("email") or "").strip().lower()
            if email:
                stripe_by_email[email] = cust

        users: list[UnifiedUser] = []
        seen_stripe_ids: set[str] = set()

        for person in posthog_persons:
            props = person.get("properties", {})
            email = (props.get("email") or "").strip().lower()
            distinct_ids = person.get("distinct_ids", [])
            distinct_id = distinct_ids[0] if distinct_ids else None
            created_at = person.get("created_at", "")

            internal_id = str(uuid.uuid4())

            # Try to match with Stripe by email
            stripe_match = stripe_by_email.get(email) if email else None

            # Fallback: match by stripe_customer_id in PostHog properties
            if not stripe_match:
                stripe_cust_id = props.get("stripe_customer_id", "")
                if stripe_cust_id:
                    for cust in stripe_customers:
                        if cust.get("id") == stripe_cust_id:
                            stripe_match = cust
                            break

            stripe_customer_id = stripe_match["id"] if stripe_match else None
            if stripe_customer_id:
                seen_stripe_ids.add(stripe_customer_id)

            user = UnifiedUser(
                internal_id=internal_id,
                email=email,
                posthog_distinct_id=distinct_id,
                stripe_customer_id=stripe_customer_id,
                first_seen=created_at,
                last_seen=created_at,
                is_matched=stripe_match is not None,
                properties={**props, **(stripe_match or {})},
            )
            users.append(user)

        # Add Stripe-only customers (not matched to any PostHog person)
        for cust in stripe_customers:
            if cust["id"] not in seen_stripe_ids:
                email = (cust.get("email") or "").strip().lower()
                created_ts = cust.get("created", 0)
                created_iso = (
                    datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()
                    if created_ts
                    else ""
                )

                user = UnifiedUser(
                    internal_id=str(uuid.uuid4()),
                    email=email,
                    posthog_distinct_id=None,
                    stripe_customer_id=cust["id"],
                    first_seen=created_iso,
                    last_seen=created_iso,
                    is_matched=False,
                    properties=cust,
                )
                users.append(user)
                logger.warning("Stripe customer %s has no PostHog match", cust["id"])

        matched = sum(1 for u in users if u.is_matched)
        logger.info("Mapped %d users total, %d matched cross-platform", len(users), matched)

        return users

    def map_subscriptions(
        self, users: list[UnifiedUser], stripe_subscriptions: list[dict]
    ) -> list[SubscriptionInfo]:
        # Index users by stripe_customer_id
        user_by_stripe_id: dict[str, UnifiedUser] = {}
        for user in users:
            if user.stripe_customer_id:
                user_by_stripe_id[user.stripe_customer_id] = user

        subscriptions: list[SubscriptionInfo] = []
        for sub in stripe_subscriptions:
            customer_id = sub.get("customer", "")
            user = user_by_stripe_id.get(customer_id)
            if not user:
                logger.warning(
                    "Subscription %s has no mapped user (customer: %s)", sub.get("id"), customer_id
                )
                continue

            # Extract plan info from items
            items = sub.get("items", {}).get("data", [])
            price_info = items[0].get("price", {}) if items else {}
            plan_name = price_info.get("nickname") or price_info.get("id", "unknown")
            mrr_cents = price_info.get("unit_amount", 0)

            # Convert Unix timestamps to ISO 8601
            started_at = self._unix_to_iso(sub.get("created", 0))
            canceled_at_raw = sub.get("canceled_at")
            canceled_at = self._unix_to_iso(canceled_at_raw) if canceled_at_raw else None

            cancel_details = sub.get("cancellation_details", {}) or {}
            cancel_reason = cancel_details.get("reason")

            subscriptions.append(
                SubscriptionInfo(
                    user_id=user.internal_id,
                    stripe_subscription_id=sub.get("id", ""),
                    status=sub.get("status", "unknown"),
                    plan_name=plan_name,
                    mrr_cents=mrr_cents,
                    started_at=started_at,
                    canceled_at=canceled_at,
                    cancel_reason=cancel_reason,
                )
            )

        return subscriptions

    @staticmethod
    def _unix_to_iso(ts: int) -> str:
        if not ts:
            return ""
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
