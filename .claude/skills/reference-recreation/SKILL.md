---
name: reference-recreation
description: Use when the user supplies a REFERENCE VIDEO and wants the same style/pacing/structure recreated for their own brand and message (product use case 3: "add a reference video, tell us about your brand"). Step 1 is a deterministic analyzer (seconds, no model calls) that turns the reference into reference-style.json + one review sheet; the rest of the pipeline is listed below with an honest built/not-built status. Do not hand-measure a reference any more.
---

# Reference recreation (use case 3)

Goal: a customer's reference video becomes a video in THEIR words and brand, in the reference's grammar, in minutes. The first manual run
(Inktober "Relic" -> Cueable "Three takes", 2026-10-03) took ~70 min, ~30 of them reading the reference by hand. This skill removes that part.

## Pipeline and status
| # | Step | Status |
|---|---|---|
| 0 | `job_receipt.py start` (see `/job-receipt`): time, tokens, credits per job | **built** |
| 1 | `analyze.py VIDEO` -> `reference-style.json` + `sheet-N.png` + `transcript.json` | **built, regression-tested** (8 videos, 4.7-24 s) |
| 2 | Look at `sheet-1.png` ONCE, name each scene's moves (chat-bubble typing, card flip, halftone hero, ...) | model, 1 image |
| 3 | Copy: the customer's message in the reference's rhetorical shape (3 options in parallel, they pick) | not built |
| 4 | Build from a tested component kit (move name + params from the json -> HTML) | **not built** (next) |
| 5 | Automatic scorecard vs the reference (cuts exact, per-scene motion, text boxes, colours; show only failing frames) | not built |
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
- `style`: `cadence_fps` (e.g. 15 on a 30 fps file = animation "on twos": quantise motion time in the build),
  `imagery` (scenes with colour-rich regions: a heuristic that can false-positive, look at the sheet).
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
