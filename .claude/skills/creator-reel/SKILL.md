---
name: creator-reel
description: Playbook for CREATOR-LED short videos (Instagram Reels / TikTok / Shorts): a talking-head clip plus optional b-roll footage and a music track become a cut, typographic, sound-designed reel. Use for "edit / cut / package this creator video", add b-roll, kinetic type, a hook, background music, jump cuts, "make this reel better". Engine tools FIRST (tools.json), scaffold instead of writing code, every stage has an acceptance check, every deviation is logged. Load after /studio-intake writes BRIEF.md with `format: creator-reel`.
---

# Creator reel playbook

Proven once: the HYROX reel (72 s, Hinglish, 4 review rounds, 2026-10-04). It cost 151 model calls (~$20 API-equivalent) because the pipeline was improvised: the engine's own `hyperframes transcribe / beats / remove-background` and `/media-use`, `/hyperframes-audio` were never tried, and cut, type and audio code was written from scratch. This playbook exists so that never happens again.

## Hard rules
- **R1 Registry first.** Run `python3 .claude/skills/creator-reel/scripts/tools_check.py` at the start. Every stage has a slot in `tools.json`: use its `use_first`. Deviating = one line in `videos/<p>/DEVIATIONS.md` (stage, tool skipped, reason) and a sentence in the hand-off. "I did not check" is not a reason. An unregistered stage is a gap: tell the user.
- **R2 Scaffold, do not write.** `new_project.py` builds the project, copies the proven scripts and runs the analysis. You author DATA in `scripts/edl.py` only. If a script must change, change the template in this skill too.
- **R3 Transcript gate.** Never cut from a transcript that failed `asr_coverage.py`. It checks speech coverage and hallucination ghosts, NOT word accuracy: read the first 20 words in the speaker's language, and verify the hook by re-transcribing its audio (S2).
- **R4 Scripts, not eyes.** A step you do by looking at images 3+ times is a gap to register in `tools.json`, not something to repeat in every job. Never loop on screenshots.
- **R5 Decided taste is not re-asked.** `references/rules-and-failures.md` holds what the user already ruled on (hook, type system, no transition effects or whooshes, music mix). Follow it.
- **R6 Cost.** Batch independent commands; redirect progress bars to a file; run the render as the background command itself; after draft 1 prefer data edits, and remux audio only when visuals did not change.
- **R7 No downloads without a yes** (file, source, size). Never print secrets. Say plainly what is unverified: audio and taste by ear, ASR word accuracy, licences.

## Intake (one message, 5 items max; skip what BRIEF.md already answers)
Speech language(s) and script for on-screen text (Roman Hinglish if Hindi) | platform, length, 9:16 | b-roll supplied? | music supplied (never synthesise it) | reference style (default: the EditLobby type system in `references/rules-and-failures.md`).

## Stages
**S0 Start.** `python3 .claude/skills/creator-reel/scripts/tools_check.py` then
`python3 .claude/skills/creator-reel/scripts/new_project.py <name> --talking-head <file> [--broll <file>] [--bgm <file>] --lang <hi|en|...>`
(starts the job receipt, probes rotation/HDR, extracts `analysis/th_16k.wav`, contact sheets, music analysis, runs `scripts/transcribe.py`). Accept: `analysis/asr_log.json` shows a PASS and `analysis/words.json` exists. No PASS: stop, tell the user which engines failed and why; do not cut.

**S1 Story and hook.** `python3 scripts/edl.py words` (index|start|word). Write the story in 5 lines. The hook is a real hook LINE (stakes + twist, in the audience's language, built on a figure that exists in the footage, never invented) plus a teaser: the speaker's strongest confession pulled to the front as cuts `H1..Hn`.

**S2 Cuts** (`CUT_DEFS`). Cut on speech edges (energy dips) with small pads; do not cut inside continuous speech without a dip (keep natural stutters); drop only fillers and false starts that sit in a dip; use `a_abs/b_abs` when the gap is under 100 ms. The hook must end exactly on its last word. Accept: `python3 scripts/edl.py` table sane; after `cut_master.py`, re-transcribe the first 6 s of `assets/audio/vo.wav` (`transcribe.py ... --accept-anyway`) and confirm the hook text with no leaked word.

**S3 Type** (`CARDS`). EditLobby system, words anchored to word indices: hook title card id `htitle` (top-centre: pill with the figure + big italic + small twist), the hook's spoken words in the bottom zone, story cards alternating top-left / bottom-right, accent word delayed ~120 ms, every card ends at its cut end. Fonts: Instrument Serif Italic + DM Sans. One accent colour.

**S4 B-roll** (`BROLL`, `BROLL_CLIPS`). Look at `analysis/br_sheet.png` ONCE; pick moments by what is being said; look for on-screen numbers that match spoken ones. `full` = 9:16 crop of a scene or hand; `card` = landscape crop of a screen in a rounded frame over a dimmed face. Crops are in the ROTATED frame; HDR is tone-mapped by `prep_broll.py`; lift dark UI with `eq`. Crops of hand-held footage drift: prefer card mode.

**S5 Sound.** Voice chain is in `cut_master.py`. SFX: `prep_sfx.py` = soft word-accent sounds only (the user's picks go in `assets/sfx/picks/<role>.mp3`). Nothing at t=0, nothing on the hook title, no whooshes. Music (user-supplied): read `analysis/bgm_analysis.txt` and run `npx hyperframes@0.8.113 beats` on it; find where the drums/beat enter; `build_audio.py --bgm-from <entrance - 0.5>`; skip file intros/outros/skits (whisper segments reveal them); default level -9.5 reads as ~10.8 dB under the voice (critic window 9-18). Flag the licence.

**S6 Transitions.** Hard cuts and the alternating punch-in zoom only. No light leaks, flashes, whips or transition sounds unless the user asks.

**S7 Build.** `python3 scripts/prep_sfx.py; python3 scripts/prep_broll.py; python3 scripts/cut_master.py; python3 scripts/write_words.py; python3 scripts/build.py; python3 scripts/build_audio.py [--bgm-from X]` then `npx --yes hyperframes@0.8.113 check` (0 errors) and `snapshot --at ...` on the hook, every b-roll and the end; look at the contact sheet once.

**S8 Render.** `npx --yes hyperframes@0.8.113 render -o exports/<name>.mp4 > build/render.log 2>&1; echo "exit: $?" >> build/render.log` as the `run_in_background` command itself (it cancels if its parent shell exits); poll the log; ~3.5 min per 72 s. Then `ffmpeg -crf 23` preview for the chat.

**S9 QA, 0 FAIL required.** `python3 ~/.claude/skills/video-critique/scripts/critique.py exports/<name>.mp4 --project . --words assets/vo/vo-words.json --allow-edge`; `bash .claude/skills/quality-gate/scripts/run_gate.sh videos/<p> exports/<name>.mp4 --profile default --tier fast` (with no light effects the flash axis is 10); frame strip at the hook, each b-roll, the end. Say audio and taste are unverified by ear.

**S10 Hand-off.** Files (full + preview), what changed, QA numbers, the unverified list, what you need from the user, `job_receipt.py report`. Update memory. Propose engine improvements as a list; never edit upstream skills during a job.

## Adding a tool the user brings
Run `scripts/asr_bench.py` (ASR) or the equivalent bake-off on the same clip, record the verdict in `tools.json` under `installed`, and only then change `order` / `use_first`. Registered so far: ElevenLabs Scribe (wins on Hinglish), openai-whisper small, `hyperframes transcribe`, vibe-server + whisper large-v3 q5_0 (rejected on Hinglish: recall 23-24% vs Scribe, segment-level only).

## Files
`tools.json` registry | `scripts/` tools_check, new_project, transcribe, asr_coverage, asr_bench | `template/` the proven build scripts + fonts | `references/rules-and-failures.md` decided taste and the bugs already hit.
