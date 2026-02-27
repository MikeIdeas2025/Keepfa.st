# Keepfa.st — Implementation Specification (Implementation Document)

> **Document Type:** Implementation
> **Version:** 1.0
> **Last Updated:** 2026-02-27
> **Parent:** [CLAUDE.md (Strategic)](../CLAUDE.md)

---

## 1. PROJECT STRUCTURE

```
keepfast/
├── pyproject.toml                # Project config, dependencies, entry point
├── README.md                     # Setup guide for vibecoder (< 5 min)
├── CLAUDE.md                     # Strategic document (unchanged)
├── docs/
│   └── IMPLEMENTATION_SPEC.md    # This document
├── src/
│   └── keepfast/
│       ├── __init__.py           # Package init, version
│       ├── server.py             # FastMCP server entry point
│       ├── auth/
│       │   ├── __init__.py
│       │   └── manager.py        # API key management from MCP params
│       ├── connectors/
│       │   ├── __init__.py
│       │   ├── base.py           # Base connector with shared cache logic
│       │   ├── posthog.py        # PostHog API connector
│       │   └── stripe.py         # Stripe API connector
│       ├── normalizer/
│       │   ├── __init__.py
│       │   ├── schema.py         # Unified data schema (dataclasses)
│       │   ├── mapper.py         # Cross-platform user_id mapping
│       │   └── cleaner.py        # Dirty data handling
│       ├── intelligence/
│       │   ├── __init__.py
│       │   ├── cohort.py         # Cohort retention calculation
│       │   ├── funnel.py         # Funnel analysis + drop-off detection
│       │   ├── trends.py         # Metric trends + anomaly detection
│       │   ├── segments.py       # Segment comparison
│       │   └── omtm.py           # OMTM selection by stage
│       ├── translation/
│       │   ├── __init__.py
│       │   └── plain_language.py # Analytics → builder language
│       └── tools/
│           ├── __init__.py       # Tool registration
│           ├── get_cohort_retention.py
│           ├── get_funnel_analysis.py
│           ├── get_metric_trend.py
│           ├── compare_segments.py
│           └── get_anomalies.py
└── tests/
    ├── __init__.py
    ├── conftest.py               # Shared fixtures
    ├── test_auth.py
    ├── test_connectors.py
    ├── test_normalizer.py
    ├── test_intelligence.py
    ├── test_translation.py
    └── fixtures/
        ├── posthog_events.json
        └── stripe_subscriptions.json
```

**Implementation Implication:** All source code lives under `src/keepfast/` to follow Python `src` layout. The package is importable as `keepfast`. Entry point for MCP is `keepfast.server:main`.

---

## 2. DEPENDENCY SPECIFICATION

### pyproject.toml

| Dependency | Version | Purpose |
|------------|---------|---------|
| `python` | >=3.11 | f-strings, dataclasses, tomllib |
| `mcp[cli]` | >=1.0.0 | FastMCP framework for MCP server |
| `httpx` | >=0.27.0 | Sync HTTP client for PostHog + Stripe APIs |
| `cachetools` | >=5.3.0 | In-memory TTL cache |

### Dev Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `pytest` | >=8.0 | Test runner |
| `pytest-cov` | >=5.0 | Coverage reporting |
| `ruff` | >=0.5.0 | Linting + formatting |

**Implementation Implication:** Use `uv` as package manager. Install with `uv sync`. No other tools required.

---

## 3. SERVER ENTRY POINT (`server.py`)

### FastMCP Server Configuration

```python
# server.py creates a FastMCP instance and registers all 5 tools.
# API keys are received as MCP server initialization parameters.

Server name: "keepfast"
Server version: from __init__.py __version__

# MCP server parameters (passed by client in MCP config):
# - posthog_api_key: str (required)
# - posthog_project_id: str (required)
# - posthog_host: str (default: "https://app.posthog.com")
# - stripe_api_key: str (required)
```

### Initialization Flow

```
1. FastMCP server starts
2. Read API keys from MCP server params (context.params)
3. Create AuthManager with keys
4. Create PostHogConnector + StripeConnector (inject AuthManager)
5. Create Normalizer (inject both connectors)
6. Create Intelligence modules (inject Normalizer)
7. Create TranslationLayer
8. Register 5 tools — each tool calls Intelligence → Translation → return string
```

**Implementation Implication:** Use FastMCP's `@mcp.tool()` decorator. Each tool function receives parameters from the LLM and returns a plain string. Use lifespan or lazy init to create connectors on first call. Server params accessed via `ctx.params` in tool functions.

---

## 4. AUTH MANAGER (`auth/manager.py`)

### Responsibility

Hold and validate API keys. No persistence — keys come from MCP params every session.

### Interface

```python
class AuthManager:
    def __init__(self, posthog_api_key: str, posthog_project_id: str,
                 stripe_api_key: str, posthog_host: str = "https://app.posthog.com"):
        # Validate non-empty strings
        # Store as instance attributes

    @property
    def posthog_headers(self) -> dict[str, str]:
        # Returns {"Authorization": "Bearer <key>"}

    @property
    def stripe_headers(self) -> dict[str, str]:
        # Returns {"Authorization": "Bearer <key>"}

    @property
    def posthog_base_url(self) -> str:
        # Returns f"{host}/api/projects/{project_id}"
```

**Implementation Implication:** Raises `ValueError` with a clear message if any required key is empty or missing. No encryption — keys are ephemeral, passed per-session.

---

## 5. CONNECTORS (`connectors/`)

### Base Connector

```python
class BaseConnector:
    def __init__(self, auth: AuthManager, cache_ttl: int = 300):
        # cache_ttl in seconds, default 5 minutes
        # self._cache = TTLCache(maxsize=100, ttl=cache_ttl)
        # self._client = httpx.Client(timeout=30.0)

    def _cached_get(self, url: str, params: dict | None = None) -> dict:
        # Cache key = url + sorted(params)
        # If in cache → return cached
        # Else → self._client.get(url, headers=..., params=...)
        # Raise ConnectorError on non-2xx response
```

### PostHog Connector

| Method | Endpoint | Returns |
|--------|----------|---------|
| `get_events(event_name: str, date_from: str, date_to: str)` | `GET /api/projects/{id}/events` | `list[dict]` — raw events |
| `get_persons(search: str \| None = None)` | `GET /api/projects/{id}/persons` | `list[dict]` — person profiles |
| `get_insights(insight_type: str, params: dict)` | `GET /api/projects/{id}/insights/trend` | `dict` — insight result |
| `get_cohorts()` | `GET /api/projects/{id}/cohorts` | `list[dict]` — defined cohorts |

**PostHog API pagination:** All list endpoints return `{"results": [...], "next": "url_or_null"}`. The connector must follow `next` until null, aggregating results. Max 10 pages to prevent runaway.

### Stripe Connector

| Method | Endpoint | Returns |
|--------|----------|---------|
| `get_customers(limit: int = 100)` | `GET /v1/customers` | `list[dict]` — customer objects |
| `get_subscriptions(status: str = "all")` | `GET /v1/subscriptions` | `list[dict]` — subscription objects |
| `get_invoices(customer_id: str \| None = None)` | `GET /v1/invoices` | `list[dict]` — invoice objects |
| `get_subscription_events(sub_id: str)` | `GET /v1/events` (filtered) | `list[dict]` — lifecycle events |

**Stripe API base URL:** `https://api.stripe.com`
**Stripe pagination:** Uses `has_more: bool` and `starting_after: str`. Follow until `has_more=false`. Max 10 pages.

**Implementation Implication:** Both connectors use `httpx.Client` (sync). All API responses are returned as raw dicts — the Normalizer handles transformation. Connectors do NOT interpret data.

---

## 6. NORMALIZER (`normalizer/`)

### Unified Schema (`schema.py`)

```python
@dataclass
class UnifiedUser:
    internal_id: str          # UUID generated by Keepfast
    email: str                # Primary key for cross-platform matching
    posthog_distinct_id: str | None
    stripe_customer_id: str | None
    first_seen: str           # ISO 8601
    last_seen: str            # ISO 8601
    properties: dict          # Merged properties from both sources

@dataclass
class UnifiedEvent:
    user_id: str              # internal_id reference
    event_name: str           # Normalized event name
    original_name: str        # Original name from source
    timestamp: str            # ISO 8601
    source: str               # "posthog" or "stripe"
    properties: dict          # Event properties

@dataclass
class SubscriptionInfo:
    user_id: str              # internal_id reference
    stripe_subscription_id: str
    status: str               # "active", "canceled", "past_due", "trialing"
    plan_name: str
    mrr_cents: int            # Monthly recurring revenue in cents
    started_at: str           # ISO 8601
    canceled_at: str | None   # ISO 8601 or None
    cancel_reason: str | None
```

### User Mapper (`mapper.py`)

**Mapping strategy (ordered by priority):**

1. Match by `email` (PostHog person property `email` == Stripe customer `email`)
2. Match by `stripe_customer_id` in PostHog person properties (if the builder set it)
3. If no match → create separate UnifiedUser entries, flag as `unmatched`

```python
class UserMapper:
    def map_users(self, posthog_persons: list[dict],
                  stripe_customers: list[dict]) -> list[UnifiedUser]:
        # Returns list of UnifiedUser with cross-platform IDs populated
        # Logs warning for unmatched users
```

### Data Cleaner (`cleaner.py`)

**Event name normalization rules:**

| Input Pattern | Normalized To | Example |
|---------------|---------------|---------|
| camelCase | snake_case | `pageView` → `page_view` |
| PascalCase | snake_case | `PageView` → `page_view` |
| spaces | snake_case | `page view` → `page_view` |
| kebab-case | snake_case | `page-view` → `page_view` |
| $ prefix (PostHog auto) | keep as-is | `$pageview` → `$pageview` |
| Multiple underscores | single underscore | `page__view` → `page_view` |

```python
class DataCleaner:
    def normalize_event_name(self, name: str) -> str:
        # Apply rules above in order

    def clean_events(self, events: list[dict]) -> list[UnifiedEvent]:
        # Normalize names, parse timestamps to ISO 8601, extract properties

    def detect_likely_onboarding_events(self, events: list[UnifiedEvent]) -> list[str]:
        # Heuristic: events that occur in first 24h for >60% of users
        # Returns list of event names
```

**Implementation Implication:** The Normalizer is the critical bridge. Connectors return raw dicts, Intelligence modules consume dataclasses. The Normalizer transforms between them. All timestamps are ISO 8601 strings (no datetime objects — simpler serialization).

---

## 7. INTELLIGENCE MODULES (`intelligence/`)

### Cohort Retention (`cohort.py`)

```python
class CohortAnalyzer:
    def __init__(self, normalizer: Normalizer):
        pass

    def calculate_retention(self, cohort_period: str,
                            periods: int = 6) -> dict:
        """
        Args:
            cohort_period: "monthly" or "weekly"
            periods: number of periods to analyze (default 6)

        Returns:
            {
                "cohorts": [
                    {
                        "name": "Jan 2026",
                        "size": 45,
                        "retention": [100, 67, 45, 38, 34, 31],  # percentages
                        "absolute": [45, 30, 20, 17, 15, 14]     # raw numbers
                    },
                    ...
                ],
                "average_retention": [100, 62, 41, 35, 30, 28],
                "trend": "declining",  # "improving", "stable", "declining"
                "confidence": "low"    # "low" (<30 users), "medium" (30-100), "high" (>100)
            }
        """
```

**Retention definition:** A user is "retained" in period N if they triggered ANY event in that period (not just a specific event). This is the simplest definition for vibecoder context.

### Funnel Analysis (`funnel.py`)

```python
class FunnelAnalyzer:
    def analyze_funnel(self, steps: list[str],
                       date_from: str, date_to: str) -> dict:
        """
        Args:
            steps: ordered list of event names defining the funnel
            date_from, date_to: ISO 8601 date strings

        Returns:
            {
                "steps": [
                    {"name": "signup", "count": 100, "rate": 100},
                    {"name": "onboarding_complete", "count": 60, "rate": 60},
                    {"name": "first_action", "count": 35, "rate": 35},
                ],
                "biggest_drop": {
                    "from": "onboarding_complete",
                    "to": "first_action",
                    "drop_rate": 42,  # percentage lost
                    "users_lost": 25
                },
                "overall_conversion": 35,
                "confidence": "medium"
            }
        """
```

**Step matching:** A user completes step N if they have an event matching `steps[N]` AFTER their event for `steps[N-1]`. Matching is case-insensitive and uses normalized event names.

### Metric Trends (`trends.py`)

```python
class TrendAnalyzer:
    def get_trend(self, metric: str,
                  granularity: str = "weekly") -> dict:
        """
        Supported metrics: "active_users", "new_users", "churned_users",
                          "mrr", "subscriptions", "events_count"
        Granularity: "daily", "weekly", "monthly"

        Returns:
            {
                "metric": "active_users",
                "granularity": "weekly",
                "data_points": [
                    {"period": "2026-W05", "value": 120},
                    {"period": "2026-W06", "value": 115},
                    ...
                ],
                "direction": "declining",  # "growing", "stable", "declining"
                "change_rate": -4.2,       # percentage change last period vs previous
                "anomalies": [
                    {"period": "2026-W06", "expected": 125, "actual": 115,
                     "severity": "mild"}  # "mild", "notable", "severe"
                ],
                "confidence": "medium"
            }
        """
```

**Anomaly detection (heuristic):** An anomaly is flagged when a data point deviates > 1.5x standard deviation from the rolling average of the last 4 periods. Severity: mild (1.5-2x), notable (2-3x), severe (>3x).

### Segment Comparison (`segments.py`)

```python
class SegmentAnalyzer:
    def compare(self, segment_a: str, segment_b: str,
                metric: str) -> dict:
        """
        Segments defined by: "paying" vs "free", "new" vs "returning",
                            "mobile" vs "desktop", or custom property values

        Returns:
            {
                "segment_a": {"name": "paying", "size": 50, "metric_value": 72},
                "segment_b": {"name": "free", "size": 200, "metric_value": 31},
                "difference": 41,           # absolute difference
                "winner": "paying",
                "statistically_significant": False,  # always False if <30 in either
                "confidence": "low"
            }
        """
```

**Predefined segments:**

| Segment Key | Definition |
|-------------|------------|
| `paying` | Has active Stripe subscription |
| `free` | No active Stripe subscription |
| `new` | First seen < 30 days ago |
| `returning` | First seen >= 30 days ago |
| `active` | Had any event in last 7 days |
| `inactive` | No events in last 7 days |

### OMTM Selection (`omtm.py`)

```python
class OMTMSelector:
    def suggest_omtm(self, context: dict) -> dict:
        """
        Analyzes current data and suggests the One Metric That Matters.

        Returns:
            {
                "suggested_metric": "week_1_retention",
                "current_value": 34,
                "target_value": 50,
                "reasoning": "...",  # plain language explanation
                "stage": "activation"  # "acquisition", "activation", "retention", "revenue", "referral"
            }
        """
```

**OMTM heuristic rules:**

| Condition | Stage | Suggested OMTM |
|-----------|-------|-----------------|
| < 50 total users | acquisition | new_users_per_week |
| < 30% complete onboarding | activation | onboarding_completion_rate |
| Month-1 retention < 40% | retention | week_1_retention |
| < 10 paying users | revenue | trial_to_paid_conversion |
| > 100 paying users, retention > 60% | referral | referral_rate |

**Implementation Implication:** All Intelligence modules return plain dicts with string keys. No custom objects — keeps serialization simple and Translation layer input predictable.

---

## 8. TRANSLATION LAYER (`translation/plain_language.py`)

### Responsibility

Convert Intelligence output dicts → builder-friendly strings. Auto-detect input language (Italian or English).

### Interface

```python
class TranslationLayer:
    def translate(self, analysis_type: str, data: dict,
                  language: str = "auto") -> str:
        """
        Args:
            analysis_type: "cohort", "funnel", "trend", "segment", "anomaly", "omtm"
            data: output dict from Intelligence module
            language: "en", "it", or "auto" (detect from MCP context)

        Returns:
            Plain language string. No jargon. Builder-friendly.
        """

    def _detect_language(self, context: str) -> str:
        # Simple heuristic: check if input contains Italian stop words
        # ("del", "dei", "come", "perché", "cosa", "quali")
        # Default to English if unsure
```

### Translation Rules

| Jargon | Plain Language (EN) | Plain Language (IT) |
|--------|---------------------|---------------------|
| Cohort retention M1: 34% | "Of last month's users, only 1 in 3 came back" | "Degli utenti del mese scorso, solo 1 su 3 è tornato" |
| Churn rate: 15% | "You're losing about 1 in 7 users every month" | "Stai perdendo circa 1 utente su 7 ogni mese" |
| Day 7 retention | "Do people come back after the first week?" | "Le persone tornano dopo la prima settimana?" |
| MRR | "Monthly recurring revenue — what you earn every month from subscriptions" | "Quanto guadagni ogni mese dagli abbonamenti" |
| Funnel drop-off | "This is where people give up" | "Qui è dove le persone si arrendono" |
| OMTM | "The one number you should focus on right now" | "Il numero su cui dovresti concentrarti adesso" |

### Confidence disclaimer templates

| Confidence | Template (EN) | Template (IT) |
|------------|---------------|---------------|
| low (<30 users) | "Heads up: I'm working with very little data ({n} users). Take this as a rough signal, not a firm answer." | "Attenzione: sto lavorando con pochissimi dati ({n} utenti). Prendilo come un segnale indicativo, non una risposta definitiva." |
| medium (30-100) | "I have enough data to spot patterns, but not enough for full statistical confidence." | "Ho abbastanza dati per individuare dei pattern, ma non abbastanza per una certezza statistica." |
| high (>100) | (no disclaimer) | (nessun disclaimer) |

### Zero data templates

| Scenario | Template (EN) | Template (IT) |
|----------|---------------|---------------|
| Zero events in PostHog | "I don't have any event data yet. Here's what to start tracking: [list based on tool type]" | "Non ho ancora dati sugli eventi. Ecco cosa iniziare a tracciare: [lista basata sul tipo di tool]" |
| Zero subscriptions in Stripe | "No subscriptions found yet. When your first users subscribe, I'll be able to tell you about [metric]." | "Nessun abbonamento trovato. Quando i primi utenti si abboneranno, potrò dirti [metrica]." |
| No matching users | "I couldn't match any PostHog users to Stripe customers. Check that users have the same email in both systems." | "Non sono riuscito ad abbinare utenti PostHog con clienti Stripe. Verifica che gli utenti abbiano la stessa email in entrambi i sistemi." |

**Implementation Implication:** The translation layer uses string templates with f-string formatting. No LLM calls — deterministic output. Each analysis_type has its own template function.

---

## 9. MCP TOOLS (`tools/`)

### Tool Registration Pattern

Each tool file exports a single function decorated with `@mcp.tool()`. The `tools/__init__.py` imports and registers all tools with the server.

### Tool Signatures (Final)

```python
# tools/get_cohort_retention.py
@mcp.tool()
def get_cohort_retention(
    period: str = "monthly",     # "monthly" or "weekly"
    num_periods: int = 6         # how many periods to show
) -> str:
    """Analyze user retention: how many people come back after signing up.
    Shows you which months/weeks keep users and which lose them."""

# tools/get_funnel_analysis.py
@mcp.tool()
def get_funnel_analysis(
    steps: list[str],            # ordered event names, e.g. ["signup", "onboarding", "purchase"]
    date_from: str = "",         # ISO date, default last 30 days
    date_to: str = ""            # ISO date, default today
) -> str:
    """Find where users drop off in a specific flow.
    Tell me the steps (events) and I'll show you where people give up."""

# tools/get_metric_trend.py
@mcp.tool()
def get_metric_trend(
    metric: str,                 # "active_users", "new_users", "mrr", etc.
    granularity: str = "weekly"  # "daily", "weekly", "monthly"
) -> str:
    """Show the trend for any metric — is it going up, down, or flat?
    I'll also flag anything unusual."""

# tools/compare_segments.py
@mcp.tool()
def compare_segments(
    segment_a: str,              # e.g. "paying", "new", "active"
    segment_b: str,              # e.g. "free", "returning", "inactive"
    metric: str                  # metric to compare on
) -> str:
    """Compare two groups of users on any metric.
    For example: are paying users more active than free users?"""

# tools/get_anomalies.py
@mcp.tool()
def get_anomalies(
    metric: str = "all",         # specific metric or "all"
    lookback_days: int = 30      # how far back to look
) -> str:
    """Detect unusual patterns in your data — spikes, drops, or weird changes.
    I'll tell you what changed, when, and suggest why."""
```

**Implementation Implication:** Tool docstrings are visible to the LLM that calls them — write them as instructions for Claude/Cursor, not for end users. Return type is always `str` (translated plain language).

---

## 10. ANTI-PATTERNS (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Return raw dicts from tools | Always return translated strings | The builder reads tool output directly — it must be plain language |
| Use `datetime` objects in schemas | Use ISO 8601 strings everywhere | Serialization issues with JSON, simpler debugging |
| Catch generic `Exception` | Catch `httpx.HTTPError`, `KeyError`, `ValueError` specifically | Generic catches hide bugs |
| Store API keys in files or env vars | Read from MCP server params only | Keys are ephemeral, per-session, zero persistence |
| Use `requests` library | Use `httpx` | Modern, sync+async support, better timeout handling |
| Import all connectors at module level | Lazy-init on first tool call | Faster server startup, fails gracefully if one API is misconfigured |
| Return analytics jargon in any output | Pass through TranslationLayer | Core differentiator — every output must be builder-friendly |
| Use `print()` for debugging | Use `logging` module with levels | Print pollutes MCP stdout communication |
| Paginate without limit | Max 10 pages per API call | Prevents runaway API consumption on large datasets |
| Calculate statistics with < 30 users | Use heuristics and flag low confidence | Statistics on tiny datasets are misleading |

---

## 11. TEST CASE SPECIFICATIONS

### Unit Tests

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| TC-001 | AuthManager.__init__ | Valid keys | AuthManager instance | Empty key → ValueError |
| TC-002 | AuthManager.posthog_headers | Valid key | `{"Authorization": "Bearer <key>"}` | — |
| TC-003 | DataCleaner.normalize_event_name | "pageView" | "page_view" | "$pageview" unchanged, "" → "", spaces |
| TC-004 | DataCleaner.normalize_event_name | "My Custom Event" | "my_custom_event" | Unicode chars, very long names |
| TC-005 | UserMapper.map_users | Matching emails | UnifiedUser with both IDs | No match → separate entries |
| TC-006 | CohortAnalyzer.calculate_retention | 3 cohorts, 3 periods | Correct retention percentages | Empty cohort, 1 user cohort |
| TC-007 | FunnelAnalyzer.analyze_funnel | 3-step funnel | Correct drop-off detection | 1-step funnel, no events matching |
| TC-008 | TrendAnalyzer anomaly detection | Data with 3x spike | Anomaly flagged as "severe" | All values identical (no anomaly) |
| TC-009 | TranslationLayer.translate | cohort data, lang=en | Plain language string, no jargon | lang=it, lang=auto |
| TC-010 | TranslationLayer zero data | Empty events list | "I don't have any event data yet..." | Zero subscriptions, no matching users |
| TC-011 | SegmentAnalyzer.compare | paying vs free | Correct comparison with winner | One segment empty, both empty |
| TC-012 | OMTMSelector.suggest_omtm | < 50 users | acquisition stage, new_users_per_week | Edge between stages |

### Integration Tests

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| IT-001 | Full tool flow: get_cohort_retention | Load fixture data, init all components | Returns translated string with retention data | — |
| IT-002 | Full tool flow: get_funnel_analysis | Load fixture data with 3-step funnel | Returns translated string with drop-off info | — |
| IT-003 | Full tool flow: zero data scenario | Empty fixture data | Returns helpful "no data yet" message, no crash | — |
| IT-004 | User mapping across PostHog + Stripe | Fixture with matching emails | UnifiedUser has both posthog_distinct_id and stripe_customer_id | — |
| IT-005 | Cache behavior | Call connector twice with same params | Second call uses cache (no HTTP request) | Clear cache |

---

## 12. ERROR HANDLING MATRIX

### External Service Errors

| Error Type | Detection | Response | Fallback | Logging |
|------------|-----------|----------|----------|---------|
| PostHog API timeout | `httpx.TimeoutException` after 30s | Retry 2x with exponential backoff (2s, 4s) | Return "PostHog is taking too long to respond. Try again in a minute." | ERROR |
| PostHog 401 Unauthorized | HTTP 401 response | No retry | Return "Your PostHog API key seems invalid. Check it in your MCP config." | ERROR |
| PostHog 429 Rate Limited | HTTP 429 response | Wait `Retry-After` header seconds, max 60s | Return "PostHog rate limit hit. Waiting..." | WARN |
| Stripe API timeout | `httpx.TimeoutException` after 30s | Retry 2x with exponential backoff | Return "Stripe is taking too long to respond. Try again in a minute." | ERROR |
| Stripe 401 Unauthorized | HTTP 401 response | No retry | Return "Your Stripe API key seems invalid. Check it in your MCP config." | ERROR |
| Stripe 429 Rate Limited | HTTP 429 response | Wait `Retry-After` header seconds, max 60s | Return "Stripe rate limit hit. Waiting..." | WARN |
| Network error (any) | `httpx.ConnectError` | Retry 1x after 2s | Return "Can't reach [service]. Check your internet connection." | ERROR |

### Data Errors

| Error Type | Detection | Response | Logging |
|------------|-----------|----------|---------|
| Zero events in PostHog | Empty results list | Return zero-data template from TranslationLayer | INFO |
| Zero customers in Stripe | Empty results list | Return zero-data template from TranslationLayer | INFO |
| No user matches | UserMapper returns all unmatched | Return no-match template + suggestion to check emails | WARN |
| Malformed event data | KeyError or TypeError during normalization | Skip event, log warning, continue with rest | WARN |
| Invalid date format in tool input | ValueError on date parse | Return "I couldn't understand that date. Use YYYY-MM-DD format." | WARN |
| Unknown metric name | Metric not in supported list | Return "I don't know the metric '[name]'. Available metrics: [list]" | INFO |

### System Errors

| Error Type | Detection | Response | Logging |
|------------|-----------|----------|---------|
| Missing API keys on init | Empty/None params | Return "Missing API key for [service]. Add it to your MCP server config." | ERROR |
| Out of memory (large dataset) | MemoryError | Return "Too much data to process at once. Try a shorter date range." | CRITICAL |

**Implementation Implication:** All errors caught in tool functions. Tools NEVER raise exceptions to the MCP client. Every error path returns a helpful translated string.

---

## 13. REFERENCES

### Strategic Document
| Topic | Location | Section |
|-------|----------|---------|
| Product vision & ICP | [CLAUDE.md](../CLAUDE.md) | "Cos'è questo progetto", "Per chi è" |
| ODA Loop & HITL principles | [CLAUDE.md](../CLAUDE.md) | "Principi di prodotto" |
| Translation philosophy | [CLAUDE.md](../CLAUDE.md) | "Translation Layer (differenziatore CRITICO)" |
| MVP scope exclusions | [CLAUDE.md](../CLAUDE.md) | "Cosa NON buildare" |
| Success metrics | [CLAUDE.md](../CLAUDE.md) | "Metriche di successo" |
| Roadmap | [CLAUDE.md](../CLAUDE.md) | "Roadmap builder" |

### External API Documentation
| API | Documentation URL | Key Endpoints |
|-----|-------------------|---------------|
| PostHog API | https://posthog.com/docs/api | /api/projects/{id}/events, /api/projects/{id}/persons, /api/projects/{id}/insights |
| Stripe API | https://docs.stripe.com/api | /v1/customers, /v1/subscriptions, /v1/invoices, /v1/events |
| FastMCP | https://github.com/modelcontextprotocol/python-sdk | Server setup, tool decorator, context params |

### Test Fixtures
| Fixture | Location | Content |
|---------|----------|---------|
| PostHog events sample | [tests/fixtures/posthog_events.json](../tests/fixtures/posthog_events.json) | 50 sample events across 10 users, 3 months |
| Stripe subscriptions sample | [tests/fixtures/stripe_subscriptions.json](../tests/fixtures/stripe_subscriptions.json) | 10 customers, mixed subscription states |

---

*This is an Implementation document. Strategic context lives in [CLAUDE.md](../CLAUDE.md).*
