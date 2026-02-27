"""Unified data schema — dataclasses used by all layers above connectors."""

from dataclasses import dataclass, field


@dataclass
class UnifiedUser:
    internal_id: str
    email: str
    posthog_distinct_id: str | None = None
    stripe_customer_id: str | None = None
    first_seen: str = ""  # ISO 8601
    last_seen: str = ""  # ISO 8601
    is_matched: bool = False
    properties: dict = field(default_factory=dict)


@dataclass
class UnifiedEvent:
    user_id: str  # internal_id reference
    event_name: str  # normalized
    original_name: str  # raw from source
    timestamp: str  # ISO 8601
    source: str  # "posthog" or "stripe"
    properties: dict = field(default_factory=dict)


@dataclass
class SubscriptionInfo:
    user_id: str  # internal_id reference
    stripe_subscription_id: str
    status: str  # "active", "canceled", "past_due", "trialing"
    plan_name: str
    mrr_cents: int  # Monthly recurring revenue in cents
    started_at: str  # ISO 8601
    canceled_at: str | None = None  # ISO 8601 or None
    cancel_reason: str | None = None
