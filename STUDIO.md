# Video Studio: how a request becomes a video

One rule: **route by the outcome the user wants, not by the input they gave.** A URL, a script and a reference video can each
be a launch film, a demo or an ad; only the outcome decides the process.

```
new request ──► /studio-intake ──► BRIEF.md (format: …) ──► the playbook for that format ──► critic-gated first cut
   (asks only what's missing)      (one file, locked)        (stages + user gates)          (0 FAIL before you see it)
```

## Formats and their status
| Format | Route | Status |
|---|---|---|
| **Launch video** (product in use, VO + UI, 45-75s) | `/launch-video` | **Built and proven** (ShopOS benchmark: 60s, 12 frames, 0 critic FAILs) |
| Product demo (one workflow) | `/launch-video`, `mode: demo` | Partial: reuses rebuilt-UI + thread moves; story grammar for single-workflow demos still to extend |
| **UI-morph loop** (one shape morphs through 8-12 UI states, cursor + beat driven, 10-20s, loops) | `/ui-morph-loop` | **Built and verified** (demo `videos/ui-morph-demo`: 16 s, 60 fps + subframe blur, deterministic, critic 0 FAIL). Engine: `.claude/skills/ui-morph-loop/lib/morph.js` |
| **Performance ad** (any platform; hook -> proof -> one ask, silent-first) | `/ad-creative` (+ `linkedin-performance-marketer` agent for LinkedIn strategy) | **Built, tested piecewise, not yet proven on a real ad**: universal playbook, platform adapter (LinkedIn verified from LinkedIn's docs), brief validator + variant naming, gate profile. Meta agent later. |
| Brand film | `/brand-brief-video` | Existing 7-stage pipeline |
| Explainer / recut / motion graphic / deck | `/faceless-explainer`, `/embedded-captions`, `/talking-head-recut`, `/motion-graphics`, `/slideshow` | Stock upstream skills |

## Launch-video pipeline (what actually runs)
brief → source (capture fallback ladder) → design system (verified against the brief's theme, hand-corrected) → story +
per-frame `ui:` blocks ◆ → static sketch sheet ◆ → one-take voice → calibrate 2-3 UI frames ◆ → propagate → SFX + measured music →
lint · check · snapshots · render · critique. ◆ = you approve. Details: `.claude/skills/launch-video/SKILL.md`.

Rebuild command for any launch project (after the storyboard exists and `launch.config.json` is filled):
```bash
.claude/skills/launch-video/scripts/build_all.sh videos/<project> --render high
```

## Quality gate (every format)
`/quality-gate`: machine axes (hook, dead time, variety, loop seam, beat aliveness, technical, audio numbers) + true-aspect review sheets + a structured review round for the taste axes, one verdict per tier: **fast = PREVIEW** (taste unreviewed, said so), **standard / studio = SHIP or FIX**. Tiers change how much taste review exists, never the machine floor. Also logs per-stage time/tokens (`stage_timer.py`) so "minutes" is measured. Run after every render, before the user sees a cut.

## Performance marketing layer (ads)
Strategy and production are separate. A **performance agent** (per platform) writes an `ad-brief.json`: offer hypothesis, personas (function x seniority), sourced proof, 3-6 radically different concepts, test plan. `/ad-creative` makes the video (universal playbook, platform-free), a **platform adapter** (`ad-creative/platforms/*.json`) holds only that destination's limits, `/quality-gate --profile ad-creative` judges it, `export_for.py` delivers it. Shared method: `/performance-core` (validator, variant names, results sheet, AIDA diagnosis, evidence grades V/S/O/U/X). We never promise ROI: we ship a test pack that can be traced back when results arrive.

## Principles
1. Every video is designed from scratch for its brand. Never reuse a previous video's style, layout or copy.
2. The product's own UI is rebuilt as HTML, never pasted screenshots.
3. The critic runs before you see a cut; the final message states what is unverified by ear (audio, taste) and every licence/illustrative-figure note.
4. Nothing upstream is edited mid-video. Engine improvements live in `.claude/skills/` and are proposed at the end.
5. Music: ask first; choose by measurement; real tracks only.

## Layout
```
hyperframe-studio/
├── CLAUDE.md, AGENTS.md            router rules for agents
├── STUDIO.md                       this map
├── .claude/skills/                 studio-intake, launch-video, brand-brief-video + stages, motion/seam skills
├── brand-kits/, templates/, scene-library/
└── videos/<project>/               BRIEF.md · STORYBOARD.md · SCRIPT.md · frame.md · launch.config.json · storyboard.html
                                    · compositions/frames/ · assets/ · renders/ · scripts/ (project builders)
```
Sound effects: `python3 ~/hyperframes-assets/sfx/_index/search.py <terms> --limit 10` (search, never list).
Benchmark record and engine findings: `videos/shopos-mora-benchmark/BRIEF.md` ("Benchmark log").
