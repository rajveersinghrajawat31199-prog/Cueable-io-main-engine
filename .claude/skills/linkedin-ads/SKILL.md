---
name: linkedin-ads
description: "LinkedIn-specific knowledge for B2B/SaaS ad creative and testing: what LinkedIn's own docs verify (video specs, copy limits, guidance: platforms/linkedin.json), what Demand Curve advises (graded O/U), the persona structure (function x seniority), offer trade-offs (gated content vs demo, lead forms), the challenger-vs-incumbent test, refresh cycle, and a dated launch/read-results checklist. Loaded by the linkedin-performance-marketer agent; use directly when a request names LinkedIn ads. Video CRAFT lives in /ad-creative; shared method in /performance-core."
---

# LinkedIn ads (knowledge module)

Read with `performance-core` (method) and `ad-creative` (craft). The adapter `ad-creative/platforms/linkedin.json` holds the verified limits.

## What is verified (V, LinkedIn's own pages, 2026-09-29)
Video ads (PAID): mp4, H.264, 75 KB-500 MB, **frame rate below 30** (so paid exports are blended from the 60 fps master to 29.97), 3 s-30 min, **15-30 s recommended**, aspects 16:9 / 1:1 / 4:5 / 9:16 with sizes in the adapter, thumbnail JPG/PNG <= 2 MB, captions as SRT. Copy: intro text 150 recommended (3,000 max), headline 70 (200 max). LinkedIn's own guidance: point within the first 5 s, show what you want in the first 10 s, think like a silent film director (burn in subtitles), clear CTA; short 7-15 s videos reported up to a 300% completion lift (LinkedIn data 2025), while for demand generation longer content performed equivalently.
**Organic Page video (separate page, V):** 10-60 fps, 3 s-10 min, up to 5 GB, resolution 256x144-4096x2304, aspect 1:2.4-2.4:1, no MOV/AVI: the 60 fps master is fine for organic.
**Not stated by LinkedIn:** 9:16 behaviour on desktop, caption safe zones, Thought Leader video specs, metric names in Campaign Manager. Never assume them.

## What Demand Curve advises (O/U: hypotheses to test, see performance-core/references/demand-curve-extract.md)
| Advice | Grade | What it changes in our output |
|---|---|---|
| Segment by job function x seniority; one campaign per seniority (manager / director / VP / C-level) | O | one persona per ad; variants per seniority |
| Advertise gated content (guide, whitepaper, ebook, webinar), not "sign up" | O | the CTA/offer is a hypothesis to test against a demo request |
| Lead forms: cheaper per lead, worse down-funnel | O | choose per goal; state the trade-off |
| Challenger vs incumbent, duplicated in one campaign | O | `test_plan.structure` |
| Ads saturate slowly; CTR falls after 28-33 days | U/O | `refresh_after_days: 30`, tested not assumed |
| "75% of LinkedIn visits are on phones" | U | verify before deciding aspect mix; until then deliver 1:1 (works both) plus 9:16 |
| No text-share rule like Facebook's | X for us | do not rely on it |

## B2B creative hypotheses (ours, O: label as such)
- The buyer is scanning a professional feed, not killing time: the hook should call out a ROLE or a costly PROBLEM, not a lifestyle image.
- Proof beats claims: a real product moment, a sourced number, a real customer.
- The ask must match the buyer's stage: gated asset for cold, demo for warm/retargeting.
- Sound is often off at work: silent-first, captions burned in.

## Checklist and results
`references/launch-checklist.md` (O, dated, verify-current). Results diagnosis: `performance-core/references/aida-diagnosis.md`.
