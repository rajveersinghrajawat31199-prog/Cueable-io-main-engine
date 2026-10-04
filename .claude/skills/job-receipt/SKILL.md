---
name: job-receipt
description: Use at the START and END of every video job (any format) to record and report what it really cost: wall and active time, model calls, exact tokens (input, cache write, cache read, output), dollars (API list-price equivalent, from the pricing sheet), tool calls, images viewed, machine seconds, and external credits (Pollo, ElevenLabs, Higgsfield). Also lists every Claude Code session with its cost. Reads the Claude Code session transcript or backend usage events. Answers "how long did it take, how many tokens/credits/dollars did it use".
---

# Job receipt

`python3 .claude/skills/job-receipt/scripts/job_receipt.py <cmd>` (full usage: `--help`).

```bash
J=.claude/skills/job-receipt/scripts/job_receipt.py
python3 $J start  --project videos/<p> --name "<what>"      # first action of a job (also records which session runs it)
python3 $J mark   --project videos/<p> "analysis"           # when a new stage begins (optional, gives a per-stage table)
python3 $J credit --project videos/<p> pollo 6 --note "3 images"      # after ANY paid external call (Pollo, ElevenLabs, Higgsfield)
python3 $J report --project videos/<p> [--what-if]           # put this block in the hand-off
python3 $J report --project videos/<p> --since "2026-10-03 01:45" --until "2026-10-03 03:05"   # retrospective window
python3 $J report --project videos/<p> --session             # the whole current session
python3 $J sessions [--since 2026-10-01]                     # every session of this project: title, time, tokens, dollars, totals by token type and model
python3 $J verify                                            # re-price Claude Code's own recorded totals with pricing.json and compare dollars
```

## What it reads (nothing is guessed, no message text is read)
- Tokens, model calls, tool calls, images viewed: the Claude Code session transcript (`~/.claude/projects/<slug>/<session>.jsonl`) plus the transcripts of the
  subagents that session spawned (`<session>/subagents/*.jsonl`): only timestamps, `usage` numbers and tool names. Per call it reads the 5-minute / 1-hour
  cache-write split, `speed` (fast mode), `inference_geo` (US residency) and web-search counts, and sums `usage.iterations` if a call has several.
  A SaaS backend with no transcript logs the API usage fields instead: `job_receipt.py usage --model M --in N --out N --cache-read N --cache-write N`.
- **Which session:** the Claude Code process running the shell carries `--resume=<session id>`; the tool follows the parent processes to find it. Never "newest file":
  two sessions can be live in one project at once (on 2026-10-04 "Agentic video editor test" ran beside this one). When another session was also active in the
  window, the receipt says so and counts only its own.
- Machine seconds: `quality/timing.jsonl` (`stage_timer.py run ...` around renders/gates).
- External credits: only what was logged with `credit`. "none logged" is printed when nothing was.

## Dollars: pricing sheet in the engine
- `pricing/claude-model-pricing-sheet.md` is the founder's sheet (Anthropic API rates, verified against the live pricing page on 2026-10-04). It is the source of truth.
- `scripts/pricing_from_sheet.py [sheet] --live-checked "<what you compared>"` turns it into `pricing/pricing.json` (19 models: input, output, 5-min and 1-hour cache write, cache read,
  batch and fast-mode rates, plus modifiers: US residency x1.1, web search $10 per 1000) and regenerates `quality-gate/scripts/prices.json` (do not edit either by hand). It prints
  consistency warnings if a row breaks the sheet's own multipliers.
- **Refresh when prices change** (the receipt warns after 45 days): paste the new sheet over `pricing/claude-model-pricing-sheet.md`, run the generator with `--live-checked`, then `verify`.
- Cost = (new input x in + cache write x write rate + cache read x read rate + output x out) / 1e6, per call, summed. Thinking tokens are already inside `output`; do not add them again.
- **It is an API list-price equivalent.** A Claude Code subscription is not billed per token. The figure is what the same work costs through the API: what the SaaS
  backend would pay, and the way to compare jobs. It is a slight under-count: Claude Code also makes background calls (titles, suggestions) that are in no transcript.
- `verify` re-prices the totals Claude Code recorded itself (`cost-state` records in each transcript) with `pricing.json`. 2026-10-04: **26 of 26 model entries within 1% or $0.10, 23 exact to the cent**,
  largest gap $0.06 (Opus 4.6 sessions that mixed 5-minute cache writes; the entry has no tier split). Models covered: Sonnet 5, Sonnet 5.5, Opus 4.6, 4.8, 5.5, Haiku 4.5.
  Run it after any pricing change; the result is stored in `pricing/last-verify.json` and quoted in every receipt.
- `--what-if` prices the same tokens on Haiku 4.5 / Sonnet 5.5 / Opus 5.5 / Fable 5.1. A guide only: Claude 4.7+ tokenizers produce about 30% more tokens than 4.6 and earlier for the same text,
  and a stronger model may need fewer steps.

## Reading it
- **Active time** excludes idle gaps over 5 min (the customer being away). Wall time is the window.
- **Cache reads dominate** (every model call re-reads the whole conversation) and so does the money: across all 24 sessions to 2026-10-04 ($535 API-equivalent, 4,042 calls)
  cache read was 60%, cache write 25%, output 15%, new input 0%. Thinking and writing is the small part; re-reading a 490k-token conversation 175 times is the big part.
  Levers: fewer model calls (work in scripts), smaller context (fewer images and file dumps, short sessions per job).
- First retrospective receipt (Inktober -> "Three takes", 01:45-03:05): 62 min active, 175 model calls, 203 tool calls, 46 images viewed, 389k output tokens (278k thinking),
  719k cache write, 85.2M cache read, **$23.81** (cache read $17.04, output $3.89, cache write $2.88), machine time under 2 min, no external credits.
- Engine build that followed (receipt + analyzer, 04:11-04:29): 22 calls, $4.91.
