---
name: quality-gate
description: "Scored critique + stage timing for ANY finished video, before the user sees a cut. Machine-scores what a machine can judge (hook speed, dead stretches, variety, loop seam, beat aliveness, technical checks, audio numbers) from a format profile's score curves, makes true-aspect review sheets (hook, phone-width, contact, action strips, seam), requires a structured agent review round for taste axes (first 2 s, phone readability, motion quality, composition, brand accuracy, message clarity) with problems that must be closed out, and returns one verdict per tier (fast = PREVIEW, standard/studio = SHIP or FIX). Also logs per-stage wall time and token cost so 'minutes' is measured. Use after any render, alongside /video-critique (which owns audio numbers)."
---

# Quality gate (all formats)

The teardown's finding: viral pieces were separated from "mid" ones by a scored self-critique loop, not by the prompt. The product
constraint: users cannot wait hours. So the loop is split by cost:

| Layer | Cost | Who |
|---|---|---|
| Machine axes (`machine_scores.py`) + sheets (`make_sheets.py`) | about 3 s | scripts, deterministic, always run |
| Structured review round (`review/round-N.json`) | one model pass over 6-8 images | the agent, only as many rounds as the tier needs |
| Human ear / taste | the customer | nobody else can do it; the gate says so every time |

**Tiers change how much taste review must exist, never the machine floor** (`rubric/tiers.json`):
`fast` = machine axes only -> verdict **PREVIEW** (honestly labelled "taste not reviewed"); `standard` = 1 round, vision axes >= 7, no open problems -> **SHIP**;
`studio` = 3 rounds, all >= 8, each round shows what it fixed -> **SHIP**. The customer picks the model; `model_hint` is only a hint.

## Run it
```bash
bash .claude/skills/quality-gate/scripts/run_gate.sh videos/<p> renders/final.mp4 --profile ui-morph-loop --tier standard   # machine axes + sheets, timed
# LOOK at videos/<p>/quality/sheets/*.png, then write quality/review/round-1.json  (python3 scripts/gate.py template --profile ui-morph-loop)
python3 .claude/skills/quality-gate/scripts/gate.py evaluate --tier standard --profile ui-morph-loop --project videos/<p>   # exit 1 = FIX
python3 .claude/skills/quality-gate/scripts/stage_timer.py report --project videos/<p>
```
Profiles: `rubric/profiles/` (`default`, `ui-morph-loop`, `launch-video`, `launch-fast`, `ad-creative`, `reference-recreation`); each overrides score curves per format. `reference-recreation` (use case 3) runs the critic with `--allow-edge` and declares two warning classes intentional (no voice-over, one-file SFX mix read as a cue at 0.00 s): the reference's own grammar bleeds type, cards and ripples off the frame. Add a profile when a new format gets a playbook (performance-ad next: it needs a hook curve stricter than 1.0 s).

## Axes
Machine (score curves in the profile): `flashes` (whole-frame brightness pulses = a 'white flash'; any one fails the floor unless the profile sets `machine.flashes.allow`; added after the Cueable v2 review), `hook` (first real change, an idle pulse does not count), `dead_time`, `variety` (longest gap between real events), `loop_seam`, `beat_alive`, `technical` (`--run-check`), `audio` (video-critique numbers; skipped for silent films).
Vision (1-10, anchors in `rubric/axes.json`): `first_2s`, `phone_readability`, `motion_quality`, `composition`, `brand_accuracy`, `message_clarity`. Full protocol: `references/review-protocol.md`.

## Restraint axes (opt-in per profile)
`coverage` (share of the frame that differs from the canvas, p90) and `movers` (separate moving things at once, busiest 3 s window) judge *quietness*: motion and timing scores cannot see a frame that is simply too busy. A profile turns them on by defining `machine.coverage` / `machine.movers` (see `launch-video.json`, with measured reasons). Not enabled elsewhere: a dense dashboard film may want its density. Calibration: the cluttered ShopOS cut scored coverage 3.4 / movers 1.2; the restrained rebuild 8.2 / 8.5.

## Rules
1. A review round lists real problems with timestamps, an axis, and the exact fix. Never pad to three; never write "looks good" with no problems.
2. Every problem is `open`, `fixed` or `accepted` (with a reason). Open problems block SHIP. Never mark `accepted` on the customer's behalf unless they said so in chat.
3. Scores are integers. A score below the tier minimum needs a problem entry for that axis.
4. Fix the source, re-render, re-run the machine axes, then a new round if the tier needs one.
5. The reviewer states what it cannot judge: **audio and taste by ear are never verified by this gate.**

## Measured behaviour (so the numbers can be trusted)
- Discrimination: the ui-morph demo scores hook 9.9 / seam 10 / beat-alive 10; the same film with a 2 s frozen intro scores hook 3.0, dead-time 2.7, beat-alive 6.4; a film whose loop pops scores seam 0.0.
- Calibration: a logo pulse moves about 0.5% of the pixels, a real morph 4%+; hook counts >= 1.8%, variety counts >= 0.6% (typing, counts, draws are real events). Activity is measured over 1/30 s so results do not depend on render fps.
- The review found a defect no machine axis can see (double-exposed count-up digits, see `ui-morph-loop/references/morph-grammar.md`). That is why vision rounds exist.

## Known limits
- Machine scores judge motion and timing, not beauty. A film can score 10 on every machine axis and still be dull.
- No token counting here: `stage_timer.py` only logs tokens someone gives it (the SaaS backend's API usage fields, or the agent). No tokens = no cost line. Prices come from the job-receipt pricing sheet (`prices.json` is generated by `job-receipt/scripts/pricing_from_sheet.py`); this log counts input and output tokens only, `job_receipt.py` has the cache-aware dollars.
- Authoring time for a NEW brand is not yet measured; wrap real work in `stage_timer.py start/stop --stage authoring` on the next video.
- `video-critique` still crashes on films with no audio stream; `machine_scores.py` skips it for silent films.
