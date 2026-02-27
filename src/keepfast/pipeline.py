"""Central data pipeline — connector -> normalizer -> NormalizedData."""

from dataclasses import dataclass

from keepfast.normalizer.cleaner import DataCleaner
from keepfast.normalizer.mapper import UserMapper
from keepfast.normalizer.schema import SubscriptionInfo, UnifiedEvent, UnifiedUser


@dataclass
class NormalizedData:
    users: list[UnifiedUser]
    events: list[UnifiedEvent]
    subscriptions: list[SubscriptionInfo]


class DataPipeline:
    """Orchestrates connector -> normalizer flow. Shared by all 3 MCP skills."""

    def __init__(self, posthog_connector, stripe_connector):
        self.posthog = posthog_connector
        self.stripe = stripe_connector
        self._cleaner = DataCleaner()
        self._mapper = UserMapper()

    def fetch_and_normalize(self) -> NormalizedData:
        # 1. Fetch raw data from both connectors
        raw_persons = self.posthog.get_persons()
        raw_events = self.posthog.get_events()
        raw_customers = self.stripe.get_customers()
        raw_subscriptions = self.stripe.get_subscriptions()

        # 2. Map users (PostHog <-> Stripe via email)
        users = self._mapper.map_users(raw_persons, raw_customers)

        # 3. Map subscriptions
        subscriptions = self._mapper.map_subscriptions(users, raw_subscriptions)

        # 4. Build PostHog distinct_id -> internal_id lookup
        ph_to_internal: dict[str, str] = {}
        for user in users:
            if user.posthog_distinct_id:
                ph_to_internal[user.posthog_distinct_id] = user.internal_id

        # 5. Clean events and remap user_ids to internal_ids
        all_events: list[UnifiedEvent] = []
        for raw in raw_events:
            distinct_id = raw.get("distinct_id", "")
            internal_id = ph_to_internal.get(distinct_id, distinct_id)
            cleaned = self._cleaner.clean_events([raw], user_id=internal_id)
            all_events.extend(cleaned)

        return NormalizedData(users=users, events=all_events, subscriptions=subscriptions)
