---
name: launch-video
description: "Playbook for a product LAUNCH video (45-75s, VO + UI, light or dark) where the product's own UI is REBUILT as designed HTML (never pasted screenshots), with a calibrate-then-propagate build, one-take voice-over, light UI SFX, a measured music bed and a critic-gated first cut. Use for 'launch video for <product>', 'promo that shows the product working', 'make a video like this reference' (structure only). Every video is designed fresh for the brand; nothing here is a reusable visual style. Load AFTER /studio-intake has written BRIEF.md with format: launch-video."
---

# Launch video (project playbook)

This layers on the stock `/product-launch-video` pipeline. It **does not edit any upstream skill**. Where the stock
pipeline's defaults fail for a rebuilt-UI launch video, this playbook names the override and the reason. Proven on a
60s benchmark (ShopOS, 12 frames, 0 critic FAILs, built without touching a skill).

## Non-negotiables (learned the hard way)
1. **Every video is designed from scratch for its brand.** The shot *grammar* in `references/story-grammar.md` is a menu of
   moves, not a template. Never reuse a previous video's layout, copy, art or palette. A reference video informs
   *structure* only.
2. **Rebuild the brand's own UI as HTML/CSS/SVG.** Never paste or crop a screenshot of the site or app. Screenshots are
   reference only (copy, real row names, tokens). Third-party marks come from `/media-use` (official logos), never redrawn.
   (`references/rebuild-ui.md`)
3. **Frame workers never read BRIEF.md.** Whatever the brief promises (rebuild UI, light theme, data world) must be
   restated in each frame's `ui:` block in STORYBOARD.md, or it will not reach the builder.
4. **The critic runs before the user sees anything.** `video-critique` on every render; fix FAILs, and every WARN you can.
   State plainly: *audio and taste are unverified by ear.* (`references/critic-gates.md`)
5. **Never edit an upstream skill or template mid-video.** Project-level changes go in this folder. `init`/`skills update`
   refresh skills from GitHub: run with `HYPERFRAMES_SKIP_SKILLS=1` inside a video.
6. **No synthesized music, no invented facts.** Numbers on screen are either the brand's own published claims (label them
   in the storyboard) or illustrative demo data (label those too).

## Stages (user gates marked ◆)
| # | Stage | Output | Notes |
|---|---|---|---|
| 0 | Intake | `BRIEF.md` (`format: launch-video`) | `/studio-intake`. Ask for hero use case, 3-4 proof points, tagline, UI source. |
| 1 | Source | `capture/` | Fallback ladder below. Live capture of WebGL-heavy sites can hang: it is a hard stop, ask before substituting. |
| 2 | Design system | `frame.md` | `build-frame.mjs` remixes from the site's *dominant* colours: **verify the canvas/ink/accent against the brief's theme and hand-correct**. `references/design-system.md` |
| 3 | Story ◆ | `STORYBOARD.md` + `SCRIPT.md` | Value claim by beat 2. One idea per frame. Per-frame `ui:` block. `references/story-grammar.md`. If BRIEF has `figures:` or `orbs:`, give each a frame slot (hook / metaphor between UI frames / section break / end) and write `ui: hairline <name>` (or `ui: orb <states>`, state times aligned to the VO) + the gesture in that frame. |
| 4 | Sketch sheet ◆ | `storyboard.html` | Static layouts with real fonts/copy. Revise only named frames. |
| 5 | Audio | `audio_meta.json`, `assets/vo/` | One continuous take. `scripts/gen_vo.py` -> `scripts/pad_vo.py` -> `audio.mjs sync-durations`. `references/audio.md` |
| 6 | Calibrate ◆ | 2-3 frames + draft render | Build the frames that SET the UI standard (usually the first UI frames, not the logo/cards). Render, critique, get approval before propagating. |
| 7 | Propagate | all frames | Reuse the calibrated standard. `scripts/lv_lib.py` for wrap/caption/cursor helpers. Orb frames: `/thinking-orbs` (`orbs_scene.py make`, ink/bg from `frame.md`). Figure frames: `/hairline-figures` (`hairline_scene.py make`, colours from `frame.md`; cursor path to `/oversized-cursor` when the beat is UI-driven). |
| 8 | Sound | SFX + music | `scripts/gen_sfx.py` (config-driven), `scripts/measure_music.py` to choose a bed. Ask before adding music; `references/music-brief.md` has the keywords. |
| 9 | Final | `renders/*.mp4` | `scripts/build_all.sh <project> --render high`. lint + check + snapshots + critique. With figures also run `python3 tools/hairline/check_figures.py renders/<x>.mp4 <project>`; with orbs add `assets/orbs` as the third argument (all PASS). |

### Source fallback ladder (URL-only briefs)
1. User-supplied screenshots / recording (best; always ask). 2. Public pages, docs, an earlier capture of the same URL
(reference only). 3. Design the UI from the product description in the brand's tokens, labelled illustrative. Never fake
"real data": use the brand's own published numbers or clearly demo figures.

## When the user supplies music (or asks for a music-driven film) - only then
Write the beat grid before the storyboard: `scripts/beat_grid.py track.mp3 --out grid.json` (tempo, beats, bars, sections, loop splices; numpy only). If the track is shorter than the film, lengthen it by repeating a bar-aligned phrase (see the ShopOS project's `scripts/extend_music.py`), never by shortening the film. Trim the lead-in so film t=0 is a beat, fade in, and place scene cuts and hits on the 8th-note grid. Voice stays the clock for UI frames: only cuts and hero hits are beat-locked. This is not a default: films without supplied music keep the normal flow.

## Files
- `references/`: story-grammar, rebuild-ui, design-system, audio, music-brief, build-gotchas, critic-gates
- `scripts/`: `lv_lib.py` (frame builder parts), `gen_vo.py`, `pad_vo.py`, `gen_sfx.py` + `sfx_palette.json`, `measure_music.py`, `build_all.sh`
- `templates/launch.config.example.json`: per-video audio config (voice, lead-in, tails, SFX cues, music)

## Definition of done
Storyboard + sketch approved; calibration approved; `build_all.sh` ends with lint 0 errors, check passed, critique 0 FAIL;
music level 9-18 dB under voice; last frame holds ~1.4s; the final message lists what is unverified by ear, any licence
notes (music, voice), and which numbers are illustrative.
