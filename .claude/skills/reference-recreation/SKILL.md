---
name: reference-recreation
description: Use when the user supplies a REFERENCE VIDEO and wants the same style/pacing/structure recreated for their own brand and message (product use case 3: "add a reference video, tell us about your brand"). Step 1 is a deterministic analyzer (seconds, no model calls) that turns the reference into reference-style.json + one review sheet; the rest of the pipeline is listed below with an honest built/not-built status. Measuring is automatic at scene level (analyze.py) and element level (measure.py -> motion-spec.json, then build_from_spec.py, beatwarp.py, fidelity.py): read the Fast path section first, ask Faithful vs Exact and state the cost.
---

# Reference recreation (use case 3)

Goal: a customer's reference video becomes a video in THEIR words and brand, in the reference's grammar, in minutes. The first manual run
(Inktober "Relic" -> Cueable "Three takes", 2026-10-03) took ~70 min, ~30 of them reading the reference by hand. This skill removes that part.

## Fast path (read this first; toolkit built 2026-10-05 after the Pinterest copy took 2.4 h, about 313 model calls, $43)
Why it was slow: I built before measuring (v1 thrown away), had no element-level measuring tools (every cursor/card/strip number was a one-off script), checked by eye on 360 px tiles
(render, look, fix, repeat), hand-coded every move, and never said what "exact copy" costs. Machine time was 3 minutes; everything else was iteration.
**1. Ask the tier once and state its cost.** *Faithful*: same structure, cuts, pacing, grammar, type roles, palette and sound shape, sizes within ~10%: build from the analyzer + one sheet, no per-element measuring (target 15 min).
*Exact*: pixel-measured sizes, paths, easings, pointer, type geometry: use the toolkit below (target 45 min; Pinterest by hand took hours).
**2. Exact tier, in this order** (all deterministic, no model calls; `S=.claude/skills/reference-recreation/scripts`):
```bash
python3 $S/analyze.py REF.mp4 --out DIR/analysis                       # scenes, cuts, palette, audio grid (seconds)
python3 $S/measure.py REF.mp4 --out DIR/spec --analysis DIR/analysis/reference-style.json [--ignore-box x0,y0,x1,y1] [--learn-cursor FRAME,X,Y,NAME]   # ~90 s for 19 s: motion-spec.json + spec-summary.md
python3 $S/beatwarp.py --spec DIR/spec/motion-spec.json --bpm 90 --out DIR/warp.json                  # nudge key hits onto the music grid (max 5 frames, stretch 0.8-1.25)
python3 $S/build_from_spec.py --spec DIR/spec/motion-spec.json --out DIR/skeleton --warp DIR/warp.json [--frames A:B] [--template videos/<project>]   # motion skeleton: every element moves exactly as measured
#   ... restyle the skeleton (colours, radii, shadows, fonts, real photos, brand copy; target data-role="card|pill|circle|photo|text") ...
python3 $S/fidelity.py --ref DIR/spec/motion-spec.json --render RENDER.mp4 --out DIR/fid --warp DIR/warp.json   # element-level diff + crops of the worst elements
python3 $S/selftest_measure.py REF_airbnb.MP4                                                      # 30 s regression test of the measuring tools
```
Read ONLY `spec-summary.md` (a dozen lines: segments, element counts by role, pointer intervals, typing, cuts) and the printed `fidelity.py` list. Never open the spec JSON; never compare tiles.
**What measure.py captures:** flat UI regions (cards, pills, circles, bands, buttons) with colour, corner radius and box per frame; photo-like regions (textured, gradient, glow, mosaic); ink lines (text, digits, icons) with OCR text,
ink colour, font-size estimate and typing cadence; the pointer sprite (tip, scale, presses; sprites in `refkit/sprites`, learn a new one with one hint); keyframes with named eases for every box coordinate; hard cuts.
**What it does NOT capture (hand work, listed as `unmodelled` / non-flat segments):** gradient or non-flat backgrounds, globes, 3D type (use `fit_type3d*.py` in the Pinterest project), blurred pixel strips, ripples and glows (they land in the photo-like class
with the right box but not their look), shadows, fonts (Inter stands in), photo content. Accuracy measured against hand numbers on the Airbnb-style reel: boxes within 1-2 px, typing frames exact, pointer tip median 0.6 px, round trip (measure -> skeleton -> render -> measure) median centre error 0.0 px.
**3. Check at element level, once:** `fidelity.py` crops (reference | render) of the worst elements; one failure list, one fix pass. No render-look-fix loops.
**4. Audio:** beat grid and event list come from the spec (cuts, presses, typing frames, appearances); levels checked by numbers (`audio_check.py` in the Pinterest project).
**5. Gate once;** reference-inherited FIXes (tiny UI text, a typing hold) are logged as customer decisions, not silently fixed away from the reference.
**Session hygiene:** scripts return numbers or ONE image; write `STATE.md` (decisions, numbers, next step) at every stage so a compaction or usage-limit resume costs two calls; never spend paid credits (Pollo) without telling the founder the cost first.
**Benchmarks:** Pinterest by hand (exact, no toolkit): v1 45 min / 94 calls / $13 (discarded), rework 92 min active / 211 calls / $28, Pollo 56 credits. Toolkit build: 40 min, 47 model calls, $9.74. First reference run WITH the toolkit: not yet done (targets unmeasured).

## Pipeline and status
| # | Step | Status |
|---|---|---|
| 0 | `job_receipt.py start` (see `/job-receipt`): time, tokens, credits per job | **built** |
| 1 | `analyze.py VIDEO` -> `reference-style.json` + `sheet-N.png` + `transcript.json` | **built, regression-tested** (8 videos, 4.7-24 s) |
| 2 | Look at `sheet-1.png` ONCE, name each scene's moves (chat-bubble typing, card flip, halftone hero, ...) | model, 1 image |
| 3 | Copy: the customer's message in the reference's rhetorical shape (3 options in parallel, they pick) | done by hand in chat (3 ideas, founder picks); not built |
| 4 | Build from a tested component kit (move name + params from the json -> HTML) | **built twice by hand** (Pinterest spec ad: v1 rejected as not faithful, v2 rebuilt from full-resolution measurements): the moves live in that project's `scripts/` (`lib.py` helpers: every-frame keyframe sampler `K`, beat warp, PCHIP paths; `build.py`: 3D cylinder type, globe hero, typing, pill -> pixel-strip -> card morph, calendar drag, slide-off + photo window, landscape card row with focus scale and a measured whip, click ripple, push-in, logo draw + type + closing icon). The generic part (motion player + skeleton builder) now lives in `build_from_spec.py`; restyling is still by hand |
| 2b | `measure.py`: element tracks from reference pixels -> `motion-spec.json` (+ `refkit/`, `selftest_measure.py`) | **built, regression-tested** (9 checks vs hand numbers, ~90 s per 19 s of video) |
| 2c | `beatwarp.py`: key hits onto the music grid | **built** |
| 5 | Element-level fidelity check vs the reference (`fidelity.py`: centre/size/timing per element, missing/extra, pointer, typing, crops of the worst) | **built**; the older project `scorecard.py` is the scene-level seed: (`scorecard.py` in the Pinterest project: size/fps match, hard cuts on the same beats, per-scene activity correlation through the beat warp, duplicate-frame share); gate profile `reference-recreation` exists |
| 6 | `job_receipt.py report` goes into the hand-off | **built** |

Default fidelity is "faithful, not forensic": same palette, type roles, scene lengths (+-0.1 s), move types and sound shape. Frame-exact is an
opt-in slower mode.

## Run step 1
```bash
python3 .claude/skills/reference-recreation/scripts/analyze.py <video> --out videos/<project>/analysis/<name>
python3 .claude/skills/reference-recreation/scripts/selftest.py <inktober video>     # regression vs hand-measured truth (14 checks)
```
Read the printed summary, then `sheet-1.png` (one image). Do NOT open the keyframes or the json unless a number is needed.

## What reference-style.json holds
- `source` (size, fps, frames, audio), `cuts[]` (frame, score), `transitions[]` (flash/dip shorter than 0.3 s, not scenes).
- `scenes[]`: frames, seconds, `bg` hex, `bg_flat`, exact `palette`, `motion` (mean/p90 diff, static share, effective fps, `step_period_frames`
  = boil/cadence, `loop_period_frames`, bursts, activity box, fade-in), `tags`, `regions[]` (hero/cards/circles: box, colour), `text[]` (OCR line,
  box, colour, align, size estimate), `key_frames` (native PNGs), `color_concentration`.
- `audio`: LUFS/LRA/peak, tempo + beat phase, `cut_beat_lock` (largest group of cuts sharing one offset to the beat; negative = cut early),
  strongest `events` by band, `level.continuous` (does sound ever drop), `speech` (local Whisper: yes/no, word count; words in `transcript.json`).
  `speech.kind` tells narration from song: `voice-over` / `sparse voice-over` / `sung vocals / lyrics (suspected ...)` / `none`, from Whisper's `no_speech_prob`
  (narration 0.01-0.03, sung vocals 0.36-0.57). Lyrics are NOT a script to copy: the music carries them.
- `transitions[]` also merges runs of flashes into one "rapid-change cluster (scroll / whip / strobe), not scenes" with a count, so a scroll is not counted as 18 cuts.
- `style`: `cadence_fps` is reported ONLY when the scene really alternates a spike of change with 1-3 near-repeat frames all through its motion (at least 30% near-repeats, thresholds relative to
  the scene's own p90, repeats interleaved with moving frames, no long low runs): animation "on twos/threes". A file that animates every frame returns null: do not quantise its motion. (An earlier
  version tagged the 30 fps Airbnb-style reel as "15 fps on twos" from a periodic pattern in soft, low-contrast motion; the build then stepped on twos and the founder rejected it as choppy.
  The fps number is approximate: reel C's scene 3 reads 15 fps, its exact repeats actually come every 3rd frame = 20 fps.) `imagery` (scenes with colour-rich regions: a heuristic that can false-positive, look at the sheet).
- `feasibility`: `tier` (type-graphics 3-6 min / ui-graphics 10-15 / graphics-no-text 8-12 / footage = no clone promised), `tier_confidence`,
  reasons. The minute bands are TARGETS, not measurements.
- `timings`: seconds per analyzer stage.

## Measured (2026-10-03, this Mac)
Inktober ref 16.6 s: 4.7 s | r1 (23 s, 30 fps, VO) 9.4 s | r2 (66 s, VO, UI) 23.8 s | r3 (57 s, VO, UI) 22.7 s | stock footage 20 s: 10.4 s.
2026-10-04, three motion-graphics reels (1080x608, 30 fps; 19.0 / 14.6 / 17.6 s): 8.9 / 8.0 / 6.2 s.
Hand analysis of the first one took ~25-30 min. Whisper runs in parallel with the pixel pass, so speech detection costs ~0-2 s of waiting.
Whisper word counts matched the earlier pipeline on r1/r2/r3 (43/135/144 vs 45/135/144).

## Limits (say them to the customer)
- It measures, it does not understand: naming what a scene IS is step 2 (a model looking at one sheet).
- OCR is macOS Vision (compile `scripts/ocr.swift` once: `swiftc -O scripts/ocr.swift -o bin/ocr`, ~80 s). On Linux use another OCR; the rest works without it.
- Whisper: `tiny` detects speech, `base.en` transcribes (English). Other languages need `--asr-model small`.
- Cut detection merges nothing across real scenes; flashes under 0.3 s become `transitions`. Gradual dissolves are not cuts.
- Tier is a heuristic (colour concentration + text density + flat borders). Abstract text-free motion graphics land in "footage" with low confidence: check the sheet.
- Variable frame rate sources are treated as constant fps.
- A creator's fixed end-card (here a 5.2 s black outro with a blur-revealed wordmark, the same in all three references) is reported as an ordinary scene; recognising "same scene in every reference" is what the component kit will do.

## Lessons from the first two use-case-3 builds (Pinterest spec ad)
- "Copy the reference" fails on details you cannot see in a thumbnail sheet: my v2 first pass had the search pill 16% too big, the text 2x too large, the hand cursor 30% too big and a calendar card 5% too wide, all invisible in 360 px tiles. Compare 1:1 crops (reference | render) of every UI element and measure sizes from pixels before building.
- Measure with pixels, not eyes: bounding boxes of the white card against the page background give exact card slides; a template match of the cursor (scale-aware, tip = reference point) gives its whole path (`scripts/track_cursor*.py` in the Pinterest project); cross-correlation of 1-D column profiles gives a strip's per-frame travel (calibrate the total against two or three known card positions: it ran 9% high).
- A low "mean frame change" does not mean "static": a slow zoom of a pale pill moves less than 0.06 on a grey-scale mean. Check the extents (bbox per frame) before calling a stretch a hold.
- Frame 0 gotcha: a seek to t=0 does not replay zero-length `tl.set` calls, so the first frame of the whole film can be blank while frame 1 is right. Draw the first frame from the markup (inline style), keep the sets as well.
- A critic/gate FIX can be inherited from the reference (tiny UI text at the reference's own scale, a 1.4 s typing hold). Log it as a customer decision with the reason, do not "fix" it silently away from the reference.

