---
name: ui-morph-loop
description: "Playbook + engine for a UI-MORPH LOOP: a 10-20s (vertical 9:16 first) product film where ONE shape never cuts, it morphs size, radius and fill through 8-12 UI states (button, field, loader, check, dashboard, chart, command palette, toast) while a large cursor drives every user-initiated change, locked to a beat grid, with closed-form spring physics, subframe motion blur, a seamless loop and (optional) UI SFX from the same score. Use for 'UI morph', 'product loop', 'one-shape product film', landing-page / app-store / paid-social loops, 'what the product does in 15 seconds'. Not for VO-led launch films (/launch-video) or brand films."
---

# UI-morph loop (engine + playbook)

The most transferable short format from the Opus 5.5 teardown (twoclipping / MakerMap pattern), rebuilt on our render stack. The
film is a **pure function of time**: `render(t)` paints any instant from closed-form springs, so renders are frame-identical
(verified byte-identical across two renders and across 1 vs 4 workers) and a fix is an edit + re-render.

## When it fits (and when it doesn't)
- Fits: silent-first loops for landing pages, app-store previews, Meta/Reels performance ads (hook in <2 s), feature releases, "how it works in one gesture".
- Does not fit: narrated launch films (`/launch-video`), story/brand films, anything whose point is many different scenes. One shape means one continuous world.

## Non-negotiables
1. **One shape, never cut.** State changes are geometry + fill + content swap, not scene cuts. The last state == the first (loop).
2. **Every user-initiated change has a click; every click ignites a state change on its beat.** System changes (loader -> check -> data) are automatic. The cursor lives off-screen at both ends and physically enters/leaves (`/oversized-cursor` laws).
3. **Hook in the first second.** A logo pulse is not a hook: the first real morph starts by beat 2 (<= 1.0 s), the logo end-card gets the freed time at the tail. (User feedback on the demo, 2026-09-29: a 1.5 s logo-only opening felt slow.)
4. **Something happens on every beat.** A beat with no visible change fails `check_loop.py`. Hold states get `pulse:`; other beats get a cursor move, a count, a stagger.
5. **Real product data and words only.** Rebuild the client's UI as HTML in their tokens; never redraw from imagination. Numbers are the brand's own published figures or labelled illustrative (the demo's `$48,290` is illustrative).
6. **Discrete text (digits, typed characters) goes through `api.q()`** so it stays sharp under motion blur (see grammar, "ghosting").
7. **No synthesized music. Ask before adding any track.** SFX only from the curated palette. Audio is unverified by ear: say so.
8. Designed fresh for the brand. The demo's look (Northwind, cobalt on mineral) is a fixture, never a style to reuse.

## Pipeline (gates marked ◆)
| # | Stage | Command / output |
|---|---|---|
| 0 | Intake ◆ | `/studio-intake` -> `BRIEF.md` (`format: ui-morph-loop`). Ask: product + URL, 8-12 states that tell its story, the real data in each, tokens + fonts + ONE accent, format(s), duration, music yes/no |
| 1 | Source | real UI reference (screens, tokens, copy). Fallback ladder: `/launch-video` -> Source |
| 2 | Scaffold | `bash .claude/skills/ui-morph-loop/scripts/new_project.sh <name>` -> `videos/<name>/` (project-local copy of `lib/morph.js`) |
| 3 | State list on the grid ◆ | edit `film.js` `states` + `cursor.path/clicks`; show the state list against beats BEFORE building content (spec: `references/spec-template.md`) |
| 4 | Layers | `index.html` layer markup (one `.layer[data-mlayer]` per content) + `film.js` `layers` functions |
| 5 | Grid | nominal 120 bpm by default, or measure a real track: `python3 scripts/beat_grid.py track.mp3 --len 20` -> `beats.js` before `film.js` |
| 6 | Structural check | `python3 scripts/check_morph.py` (2 s, no render): loop closes, cursor parked, last morph settled, clicks on state beats |
| 7 | Stills ◆ | `python3 scripts/still.py --beat 3 5 9 ... --sheet` (about 1 s per still, no video render). Approve the states' look |
| 8 | Sound (optional) | give states `sfx:[{dt,name,vol}]`, `cursor.clickSfx`; `python3 scripts/sfx_from_film.py --mount` |
| 9 | Draft render | `npx hyperframes@0.8.55 render --quality draft --fps 30` (about 10 s for 16 s) -> `check_loop.py --sheet` |
| 10 | Final | `bash scripts/render_blur.sh . --fps 60 --sub 4 --shutter 180 --out renders/final.mp4` (about 60 s, 4 workers) |
| 11 | Gate | `check_loop.py renders/final.mp4 --bpm 120 --compare <2nd render>`; then `/quality-gate` (`run_gate.sh ... --profile ui-morph-loop --tier fast|standard|studio`): machine axes + sheets + a review round. LOOK at the sheets |
| 12 | Formats | 1:1 and 16:9 are re-authored, not cropped: change `w/h`, `stage`, state geometry per aspect (see `references/morph-grammar.md`, "Formats") |

## Engine API (`lib/morph.js`, `window.HFMorph`)
- `spring(t,k,d)`, `sp(t,preset)`: exact closed form for under/critical/over-damped. Presets (settle to 1%): `snappy 320/30` 0.25 s (cursor, buttons), `default 170/26` 0.51 s (containers), `heavy 90/20` 0.79 s (big numbers), `playful 220/14` 0.60 s with 18.6% overshoot, `trail 140/22` 0.48 s.
- `track(t, [[time,value,preset?],...])`: multi-target spring. One spring per retarget, motion stays continuous. `indicator(t, stops, size)`: lead/trail edges stretch (tab pills, highlights).
- `swapAlpha`, `typed(str, lt, t0, cps)`, `press(t, tClick)`, `bumpCurve`, `settle(preset)` (time to 1%).
- `build(FILM)` wires DOM + one paused GSAP timeline whose single linear proxy tween calls `render(t)`. `index.html` registers it: `window.__timelines["ui-morph"] = window.__film.timeline`.
- FILM contract: `states[{id, layer?, beat, w,h,r, fill, x?,y?, shadow?, pulse?, sfx?, size?/radius?/fillP? presets, swap?}]`, `cursor{size,tip,lead,path[{arrive|beat,x,y,preset}],clicks,clickSfx}`, `camera?[{beat,scale,x,y}]`, `layers{id:(lt,api,el,t)=>{}}`, `fps` (for `api.q`).
- Page params: `?report` prints `window.__morphReport` into the DOM (for the checks); `?t=9.5` paints that instant (for `still.py`).

## Files
`lib/morph.js` · `template/` (index.html, film.js, fonts, gsap: a working 16 s demo, "Northwind", illustrative data) · `scripts/`: `new_project.sh`, `check_morph.py`, `still.py`, `check_loop.py`, `beat_grid.py`, `sfx_from_film.py`, `render_blur.sh` · `references/`: `spec-template.md`, `morph-grammar.md`

## Definition of done
`npm run check` 0 errors · `check_morph.py` 0 FAIL/WARN · `check_loop.py` 0 FAIL/WARN (hook: first real morph by 1.0 s, seam, every beat alive, no still run > 0.75 s) · two renders frame-identical · critic 0 FAIL · you LOOKED at `beats.png` and exact frames at each click/morph · final message states: path + duration, what is illustrative, that **audio and taste are unverified by ear**, and any licence note if a track was added.

## Known limits (measured, not guessed)
- **The renderer's capture times jitter by up to about 1 ms at 240 fps** (not exact multiples of 1/240). Found via ghosted count-up digits; `api.q()` therefore floors with a +0.12-frame bias (verified: 35/35 digit changes on the 4-subframe boundary, was 2 of 3). Any new snap-to-frame logic must tolerate this.
- Render cost: 16 s @ 1080x1920 = about 10 s draft (30 fps), about 60 s final at 60 fps x 4 subframes with `--workers 4` (auto picked 1 worker on the fast-capture path and took about 170 s; force `--workers 4`). On this machine (M-series); measure yours.
- `video-critique` crashes on a video with **no audio stream**. Workaround until fixed: run it on a temp copy with `anullsrc` audio. It also lays vertical contact sheets on 16:9 cells (squashed but readable); use `snapshots/beats.png` for true aspect.
- SFX-only cuts read as about -29 LUFS integrated (sparse cues). That is expected: loudness gates only mean something with a music bed or VO.
- Beat grid from a track is uniform-tempo with about +-10 ms error (validated on a 128 bpm click fixture and a real 120 bpm track). Rubato tracks need per-beat snapping (not built).
- `camera` keys render (verified in a still) but no proven film uses them yet. The cursor sits inside `#world` so camera moves keep it aligned.
- Width/height are animated directly by the engine (proxy `onUpdate`). HyperFrames docs call this "avoid, not forbidden"; lint, runtime, layout, contrast all pass and renders are deterministic.
