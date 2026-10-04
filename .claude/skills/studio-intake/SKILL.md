---
name: studio-intake
description: "FIRST STOP for any new video request in this studio ('make a video', 'launch video for X', 'demo', 'ad', 'promo', a URL, a script, a reference video). Classifies the OUTCOME the user wants (launch video, product demo, performance ad, brand film, explainer, recut/captions, motion graphic, deck), asks only what is missing, writes BRIEF.md with `format:` locked, then hands off to the playbook for that format. Routes by intent, not by input type (a URL alone does not decide anything). Skip for edits to an existing project."
---

# Studio intake (router)

Old behaviour: the stock `/hyperframes` router chose a workflow from the **input type** (URL -> product-launch-video,
text -> explainer). That is why a demo, an ad and a launch video for the same URL all got the same slideshow-ish treatment.
This router chooses from the **outcome**, then delegates. It replaces nothing upstream: it runs first, writes `BRIEF.md`,
and the chosen playbook (or the stock skill) carries on.

## 0. Skip when
An existing project is being edited/rendered/diagnosed (`BRIEF.md`, `hyperframes.json`, `STORYBOARD.md` exists): do the
edit; do not re-interview.

## 1. Classify (one glance, then confirm in one line)
| The user wants... | format | Route | Status |
|---|---|---|---|
| a product launch / "show the product working" film with VO + UI, 45-75s | `launch-video` | `/launch-video` | **built, proven** (60s benchmark, 0 critic FAILs) |
| a demo walkthrough of one workflow, from a URL/prompt/assets/reference | `product-demo` | `/launch-video` (its rebuild-UI + thread moves) with `mode: demo`; more depth planned | partial: reuse the playbook; extend story-grammar for a single-workflow demo |
| a silent-first product loop: one shape morphing through 8-12 UI states, cursor-driven, beat-locked (landing page / app-store / Reels loop, 10-20s) | `ui-morph-loop` | `/ui-morph-loop` | **built and verified on a 16 s demo** (structural check, loop seam, every-beat, determinism, critic 0 FAIL); audio unverified by ear |
| a short paid-social / performance ad for ANY platform (hook -> proof -> one ask, silent-first, 6-30s), or "ads for LinkedIn/Meta" | `ad-creative` | **LinkedIn ads with no brief yet -> `linkedin-performance-marketer` agent FIRST** (writes `ad-brief.json`), then `/ad-creative` (universal playbook + platform adapter + `/quality-gate --profile ad-creative`) | **playbook, gate profile, LinkedIn adapter + agent built and tested piecewise; no ad video produced end to end yet**; Meta agent/adapter later |
| a brand / mood film from a brand brief | `brand-film` | `/brand-brief-video` (existing 7-stage pipeline) | existing |
| an explainer from text/topic/article | `explainer` | `/faceless-explainer` | stock |
| captions / graphic overlays on existing footage | `recut` | `/embedded-captions` or `/talking-head-recut` | stock |
| a <10s kinetic type / stat / logo sting | `motion-graphic` | `/motion-graphics` | stock |
| a deck | `deck` | `/slideshow` | stock |
| a REFERENCE VIDEO the user wants recreated in their own brand and message (product use case 3) | `reference-recreation` | `/reference-recreation`: analyzer first (seconds), then the build route its `reference-style.json` points to | **analyzer built + regression-tested on 5 videos; component kit, auto-compare and series reuse not built yet** |
Ambiguous ("a video for my product")? Ask ONE question: *is this a launch/promo film, a single-workflow demo, or a short ad?*

## 2. Ask only what is missing (one message, <=5 items)
1. **Product + source**: URL, and does the user have real UI (screenshots/recording)? If not: "we will design the UI from your product description and mark it illustrative; real screens later replace it".
2. **Hero use case** (the one story the film leads with) and **3-4 proof points** (order = priority), plus the **tagline/CTA** wording.
3. **Assets**: exact logo file (say which background it is for), brand fonts/colours, product/ad imagery, **theme** (light/dark).
4. **Reference** (optional): a video whose *structure* they like. We take structure, never copy or style. EXCEPTION, use case 3: when the user asks for the reference's own style, copy its grammar (rhythm, type roles, motion, colour blocking), never its artwork, sentences or audio: `/reference-recreation`.
5. **Length + destination** (default 60s, 16:9, YouTube) and **music**: ask, and give the search brief (`/launch-video` -> `references/music-brief.md`) if they need to find one.
Non-negotiables to record if stated: things that must/must not appear, competitor names, unreleased features.

Do NOT ask about things you can decide with a receipt (fonts, motion, layout). Recommend, with the reason.

## 3. Write BRIEF.md (stock shape + studio fields)
```
---
workflow: product-launch-video        # the executing engine underneath
format: launch-video                  # THIS router's decision
flow: automation
storyboard: yes
message: "<the one thing>"
destination: youtube
aspect: 1920x1080
language: en
length: 60s
angle: <positioning>
theme: light | dark
ui_source: supplied | captured | designed-illustrative
---
## Intent    (hero use case, proof points [site] vs [illustrative], tagline, tone, what a reference contributed: structure only)
## Assets    (path — what/where; logo variant per background)
## Customizations (rebuild UI as HTML; accent word treatment; music brief/answer)
## Notes     (must / must-not; licence notes; "no skill edits during a video")
```
Then hand off: `/launch-video` (stage 1 onward), or the stock skill named in the table. Do not re-ask anything the brief answers.

## 4. Guardrails that apply to every format
- Every video is designed fresh for the brand. A previous video is a *process* reference, never a style source.
- First draft must pass the critic before the user sees it; state what is unverified by ear.
- Never edit an upstream skill during a video; propose engine changes at the end.
- If a route is "no playbook yet", say so plainly and offer the nearest path; do not pretend the pipeline is proven.
