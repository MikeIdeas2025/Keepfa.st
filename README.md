# Keepfa.st

You build products. Keepfa.st tells you why people leave.

Connect your PostHog + Stripe, ask questions in plain language, get answers you can act on — right inside Cursor or Claude.

No dashboards. No analytics jargon. Just answers.

---

## What it does

Keepfa.st is an MCP server that reads your PostHog events and Stripe subscriptions and answers your questions about retention, growth, and customer health.

It gives you 9 tools:

1. **Health Check** — Which customers are doing well, which ones are about to leave, and why
2. **Journey Map** — Where people get stuck between signing up and becoming loyal users
3. **Customer Value** — How much each customer is worth and a plan to keep them longer
4. **Cohort Retention** — How many users come back over time, grouped by when they signed up
5. **Funnel Analysis** — Where people drop off in any flow you define
6. **Metric Trends** — Whether any metric is growing, declining, or stable
7. **Segment Comparison** — Compare two groups of users (paying vs free, new vs returning, etc.)
8. **Anomaly Detection** — Spot unusual spikes or drops in any metric
9. **Key Metric (OMTM)** — The one number you should focus on right now, based on your stage

Everything comes back in plain language. Instead of "your M1 cohort retention is 34%", you get "only 1 in 3 people came back last month — here's why."

---

## Before you start

You need:
- [PostHog](https://posthog.com) account with some events tracked (free tier works)
- [Stripe](https://stripe.com) account (even with 0 subscriptions — Keepfa.st handles that)
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An MCP client: [Cursor](https://cursor.sh), [Claude Desktop](https://claude.ai/download), or [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Setup (3 minutes)

### 1. Clone and install

```bash
git clone https://github.com/MikeIdeas2025/Keepfa.st.git
cd Keepfa.st
uv sync
```

### 2. Find your API keys

**PostHog:**
- Go to Settings > Project > Project API Key
- Note your Project ID from the URL: `https://app.posthog.com/project/XXXXX` (the number)

**Stripe:**
- Go to Developers > API Keys > Secret key (starts with `sk_`)

### 3. Connect to your MCP client

Add this to your MCP config:

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "keepfast": {
      "command": "uv",
      "args": ["--directory", "/path/to/Keepfa.st", "run", "keepfast"]
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):
```json
{
  "mcpServers": {
    "keepfast": {
      "command": "uv",
      "args": ["--directory", "/path/to/Keepfa.st", "run", "keepfast"]
    }
  }
}
```

Replace `/path/to/Keepfa.st` with the actual path where you cloned it.

### 4. Try it without API keys (sandbox mode)

Don't have PostHog or Stripe set up yet? No problem. Use `sandbox` as your PostHog API key and Keepfa.st will use built-in sample data so you can see what it does before connecting your real accounts.

> "Check the health of my customers" — use `sandbox` as the PostHog API key, any value for project ID and Stripe key.

### 5. Ask your first question

Open Cursor or Claude and ask:

> "Check the health of my customers" and pass your PostHog API key, project ID, and Stripe key.

That's it.

---

## What you can ask

### Health Check
> "Are any of my customers about to leave?"

> "Which customers need attention right now?"

> "How much revenue am I at risk of losing?"

Shows each customer's health score (0-100), flags who's at risk and why — like "no activity in 14+ days" or "canceled subscription."

### Journey Map
> "Where do people get stuck after signing up?"

> "How many users actually make it through onboarding?"

> "Show me the customer journey"

Maps every user to a phase — from first contact to loyal advocate. Tells you where the biggest drop-off is so you know what to fix first.

### Customer Value
> "How much is each customer worth?"

> "Who are my most valuable customers?"

> "Give me a plan to increase customer loyalty"

Calculates lifetime value per customer, groups them into segments (Champions, Advocates, Affluents, Misers), and gives you a 5-step action plan.

### Cohort Retention
> "Do my users come back after the first month?"

> "Show me retention for weekly cohorts"

### Funnel Analysis
> "Where do people drop off between signup, onboarding, and first purchase?"

### Metric Trends
> "Is my MRR growing or shrinking?"

> "How are active users trending week over week?"

### Segment Comparison
> "Are paying users more active than free users?"

> "Compare new users vs returning users on retention"

### Anomaly Detection
> "Has anything unusual happened with my active users?"

### Key Metric
> "What's the one number I should focus on right now?"

---

## How it works

```
PostHog (events, users) ──→ ┐
                             ├──→ Normalize ──→ Analyze ──→ Plain language answer
Stripe (subscriptions)   ──→ ┘
```

Keepfa.st pulls your data, matches users across both platforms (via email), cleans up messy event names, runs the analysis, and translates everything into language a builder can act on.

It handles the mess:
- **No naming convention?** Your events can be called `signUp`, `sign-up`, `Sign Up`, or `sign_up` — Keepfa.st normalizes them all
- **Mismatched user IDs?** It matches PostHog and Stripe users by email
- **Not enough data?** Instead of crashing, it tells you what to start tracking
- **Too few users?** It's transparent about confidence levels — no fake precision

---

## Works in Italian too

Ask in Italian, get answers in Italian:

> "Come stanno i miei clienti?"

> "Dove si bloccano le persone dopo la registrazione?"

> "Quanto vale ogni cliente?"

---

## For contributors

```bash
# Run tests
uv run pytest --cov=keepfast -v

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/
```

205 tests, 84% coverage. Python 3.11+.

---

## Who this is for

You know how to build a product but not how to read analytics. You've got PostHog installed but you don't know what to look at. You check your Stripe dashboard and hope the number goes up.

Keepfa.st is the PM you never hired — it reads your data and tells you what to fix.

---

Built by [Michele Laurelli](https://x.com/MicLau93)
