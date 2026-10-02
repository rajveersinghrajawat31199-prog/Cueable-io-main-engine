---
name: performance-core
description: "Shared core for performance-marketing agents (LinkedIn now, Meta later). Owns the contract between strategy and production: the ad-brief JSON (personas, offer, sourced proof, 3-6 radically different concepts, test plan), a validator that blocks invented proof and untestable test sets, a variant generator with traceable names + a results sheet + UTM scheme, and the AIDA method for reading results into creative changes. Platform-neutral. Use when planning ads for any platform or reading ad results; platform agents build on it."
---

# Performance core (shared by every platform agent)

**What it is:** the strategy layer that sits before and after the studio. It never makes video. It produces an **ad brief** the studio can build from, and it turns real results into the next creative change.

**What it is not:** a promise of ROI. Return depends on offer, landing page, targeting, budget and price; creative is one input. What we control: assets that follow known mechanics (hook, proof, one ask, silent-first), checked by `/quality-gate`, delivered as a TEST PACK of radically different variants that can be traced back when results arrive.

## Pieces
| File | Job |
|---|---|
| `templates/ad-brief.template.json` | the contract: brand, platform, objective, offer, sourced proof, personas, concepts, test plan, risks, unverified |
| `scripts/validate_brief.py` | FAIL on placeholders, unsourced proof, fabricated testimonials, fewer than 3 concepts / 3 hook types, duplicate angles |
| `scripts/make_variants.py` | persona x concept x length -> named variants, `variants.csv`, `results.csv`, `utm.txt` |
| `templates/results-template.csv` | what a user fills in (spend, impressions, first-view plays, watch time, clicks, leads) |
| `references/aida-diagnosis.md` | results -> which creative lever to change |
| `references/evidence-grades.md` | V / S / O / U / X: how sure we are of any rule |
| `references/demand-curve-extract.md` | what the two Demand Curve files say, line-referenced and graded |

## Process (every platform agent follows it)
1. **Intake** only what is missing: offer, who buys (function + seniority), the one goal metric, real proof they can share, brand assets ready?, existing best ad.
2. **Offer decision** with a stated hypothesis (e.g. gated guide vs demo) and how it will be tested.
3. **Personas**: one pain each, in their words. One persona per ad.
4. **3-6 concepts** that differ in ANGLE and HOOK TYPE (pain-callout, number, contrarian, demo-first, question, before/after, customer story only with real proof).
5. **Write the brief**, run `validate_brief.py` until 0 FAIL, `make_variants.py`, then hand to the studio (`/studio-intake` -> `format: ad-creative`).
6. **After launch (later, when the user brings numbers):** fill `results.csv`, diagnose with `aida-diagnosis.md`, write ONE change per weak stage as the next variant (`-v2`).

## Hard rules
- Never invent proof, customers, quotes or numbers. Unsourced items must be labelled illustrative, and illustrative numbers never go to a paid campaign unreplaced.
- Never promise results. Say what was tested and what it can teach.
- Tag every recommendation with an evidence grade when it is not V. Do not present O/U as fact.
- Media-buying advice (targeting, budgets, bids) is a short checklist marked verify-current, never the core deliverable.
