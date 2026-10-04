# Claude Model Pricing Sheet (Official Anthropic API Rates)

> Source: https://platform.claude.com/docs/en/about-claude/pricing — verified Oct 4, 2026.
> All prices are **USD per million tokens (MTok)**. "Sonnet 5.5 at multiple capacities (max/medium/high)" doesn't exist as a separate pricing tier — token price is the same regardless of extended-thinking effort level; thinking/reasoning tokens are simply billed as **output tokens** at the model's standard output rate. Effort level changes how many tokens get used, not the per-token rate.

## 1. Standard API Pricing (Messages API)

| Model | Input | Output | Cache Write (5 min) | Cache Write (1 hr) | Cache Read (hit) |
|---|---|---|---|---|---|
| **Claude Haiku 4.5** | $1 / MTok | $5 / MTok | $1.25 / MTok | $2 / MTok | $0.10 / MTok |
| **Claude Sonnet 5** | $2 / MTok | $10 / MTok | $2.50 / MTok | $4 / MTok | $0.20 / MTok |
| **Claude Sonnet 5.5** | $2 / MTok | $10 / MTok | $2.50 / MTok | $4 / MTok | $0.20 / MTok |
| **Claude Opus 5** | $5 / MTok | $25 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok |
| **Claude Opus 5.5** | $4 / MTok | $20 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok |
| **Claude Fable 5.1** | $10 / MTok | $50 / MTok | $12.50 / MTok | $20 / MTok | $0.25 / MTok |

### Legacy / deprecated models (for reference)

| Model | Input | Output | Cache Write (5 min) | Cache Write (1 hr) | Cache Read (hit) |
|---|---|---|---|---|---|
| Claude Mythos 5.1 | $10 / MTok | $50 / MTok | $12.50 / MTok | $20 / MTok | $0.25 / MTok |
| Claude Fable 5 | $10 / MTok | $50 / MTok | $12.50 / MTok | $20 / MTok | $1.00 / MTok |
| Claude Mythos 5 | $10 / MTok | $50 / MTok | $12.50 / MTok | $20 / MTok | $1.00 / MTok |
| Claude Opus 4.8 | $5 / MTok | $25 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok |
| Claude Opus 4.7 | $5 / MTok | $25 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok |
| Claude Opus 4.6 | $5 / MTok | $25 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok |
| Claude Opus 4.5 | $5 / MTok | $25 / MTok | $6.25 / MTok | $10 / MTok | $0.50 / MTok |
| Claude Opus 4.1 | $15 / MTok | $75 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok |
| Claude Opus 4 | $15 / MTok | $75 / MTok | $18.75 / MTok | $30 / MTok | $1.50 / MTok |
| Claude Sonnet 4.6 | $3 / MTok | $15 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok |
| Claude Sonnet 4.5 | $3 / MTok | $15 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok |
| Claude Sonnet 4 | $3 / MTok | $15 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok |
| Claude Haiku 3.5 | $0.80 / MTok | $4 / MTok | $1.00 / MTok | $1.60 / MTok | $0.08 / MTok |

**Note on cache-write multipliers:** 5-min write = 1.25x input price; 1-hr write = 2x input price. Cache read = 0.1x input price (0.05x on Opus 5.5; 0.025x on Fable 5.1 / Mythos 5.1).

## 2. Batch API Pricing (50% off standard — async only)

| Model | Batch Input | Batch Output |
|---|---|---|
| Claude Haiku 4.5 | $0.50 / MTok | $2.50 / MTok |
| Claude Sonnet 5 | $1.00 / MTok | $5.00 / MTok |
| Claude Sonnet 5.5 | $1.00 / MTok | $5.00 / MTok |
| Claude Opus 5 | $2.50 / MTok | $12.50 / MTok |
| Claude Opus 5.5 | $2.00 / MTok | $10.00 / MTok |
| Claude Fable 5.1 | $5.00 / MTok | $25.00 / MTok |
| Claude Sonnet 4.6 / 4.5 / 4 | $1.50 / MTok | $7.50 / MTok |
| Claude Opus 4.8 / 4.7 / 4.6 / 4.5 | $2.50 / MTok | $12.50 / MTok |
| Claude Opus 4.1 / 4 | $7.50 / MTok | $37.50 / MTok |
| Claude Haiku 3.5 | $0.40 / MTok | $2.00 / MTok |

## 3. Fast Mode Pricing (research preview — Opus only, premium rate)

| Model | Fast Input | Fast Output |
|---|---|---|
| Claude Opus 5.5 | $8 / MTok | $40 / MTok |
| Claude Opus 5 / Opus 4.8 | $10 / MTok | $50 / MTok |

Not available on Opus 4.7 (errors) or Opus 4.6 (runs standard, billed standard). Not available with Batch API.

## 4. Other surcharges & modifiers that affect effective cost

| Item | Rate / Multiplier |
|---|---|
| Data residency (`inference_geo: "us"`, Claude 4.6+ models) | 1.1x on all token categories |
| Bedrock / Vertex regional or multi-region endpoints (Sonnet 4.5, Haiku 4.5, Opus 4.5+) | +10% over global endpoint |
| Web search tool | $10 per 1,000 searches, plus standard token cost of returned content |
| Web fetch tool | No extra charge — standard token cost only |
| Code execution (without web search/fetch) | Free up to 1,550 hrs/org/month, then $0.05/hr per container |
| Claude Managed Agents session runtime | $0.08 per session-hour, in addition to token costs |
| 1M-token context window (Sonnet/Opus/Fable 4.6+ and later) | Same per-token rate even past 200K input — no long-context surcharge |

### Tool-use system-prompt token overhead (added to input tokens whenever tools are present)

| Model | `auto`/`none` | `any`/`tool` |
|---|---|---|
| Claude Opus 5.5 | 286 | — |
| Claude Sonnet 5.5 | 286 | — |
| Claude Sonnet 5 | 354 | 474 |
| Claude Haiku 4.5 | 496 | 588 |
| Claude Opus 5 | 286 | 406 |

## 5. Quick blended-cost reference (per 1M total tokens, 80% input / 20% output mix)

| Model | Blended $ / MTok (no cache) |
|---|---|
| Claude Haiku 4.5 | $1.80 |
| Claude Sonnet 5 / 5.5 | $3.60 |
| Claude Opus 5.5 | $7.20 |
| Claude Opus 5 | $9.00 |
| Claude Fable 5.1 | $18.00 |

*(Formula: 0.8 × input rate + 0.2 × output rate. Recalculate with your own input/output split for an accurate estimate.)*

## 6. Worked example (from Anthropic docs)

1-hour session on Claude Opus 5: 50,000 input tokens + 15,000 output tokens, no caching:
- Input: 50,000 × $5/1M = $0.25
- Output: 15,000 × $25/1M = $0.375
- **Total (tokens only): $0.625**

Same session with 40,000 of the 50,000 input tokens served from cache reads:
- Uncached input: 10,000 × $5/1M = $0.05
- Cache reads: 40,000 × ($5 × 0.1)/1M = $0.02
- Output: 15,000 × $25/1M = $0.375
- **Total: $0.445** (≈29% savings from caching alone)

---

*For current rates, always check https://claude.com/pricing or https://platform.claude.com/docs/en/about-claude/pricing — these change over time and this sheet is a snapshot.*
