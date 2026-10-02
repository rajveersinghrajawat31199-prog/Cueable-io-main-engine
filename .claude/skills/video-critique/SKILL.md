---
name: video-critique
description: >
  Use after rendering ANY HyperFrames (or other programmatic) video and BEFORE showing it to the user:
  objectively reviews the rendered MP4 against its project (audio timing, dead air, SFX and music
  levels vs the voice, static screens, cut-to-voice sync, mockup/text co-arrival, orphan SFX, content
  cropped at the frame edge, loudness) and produces contact sheets to look at. Also use when the user
  says the video feels laggy, empty, abrupt, badly synced or has gaps, or asks for a review/critique
  of a cut. Don't use for planning, storyboards, or authoring; this only judges a finished render.
---

# video-critique

The stock HyperFrames flow only has `npm run check` (lint/layout/contrast) and a manual still-frame snapshot. Nothing reviews audio, sync, pacing or dead air, so first cuts shipped with problems the user then had to find. This skill is that missing review. **A first cut must pass it (and your own eyes on the sheets) before the user sees it.**

## Run it

```bash
python3 ~/.claude/skills/video-critique/scripts/critique.py renders/<file>.mp4 --project .
# options: --words assets/vo/vo-words.json  --moments critique.moments.json  --allow-edge  --no-sheets
```

Exit code 1 = at least one FAIL. WARNs are judgement calls: fix them or say why they are intentional.

It reads `index.html` `<audio>` tags (id/src/data-start/data-duration/data-volume) and classifies each as **voice** (id or path contains `vo`/`voice`/`narr`), **music** (`bgm`/`music`/`score`) or **SFX** (everything else). Audio inside sub-compositions is not seen; keep audio in the root `index.html`.

## What it checks

| Area | Check | Pass bar |
|---|---|---|
| Opening | no voice/SFX hit in the first 120 ms (music judged separately) | a cold "abrupt" hit is a FAIL |
| Opening | SFX before the first spoken word | none earlier than 0.25 s before it |
| Voice | silence inside the speech | no gap > 0.45 s (natural sentence pause ~0.3 s) |
| Voice | hold after the last word | < 2.2 s |
| SFX | peak level; margin under local voice peak | <= -9 dBFS and >= 8 dB under the voice |
| SFX | density | <= 5 cues in any 1 s window |
| Music | average level under the voice | 9-18 dB under; covers >= 90% of the video; fades out >= 6 dB; <= -44 dBFS in the first 120 ms (fade it in) |
| Mix | integrated loudness / true peak | -20..-12 LUFS, peak <= -1 dBFS |
| Video | static screen (no visible motion) | none > 0.7 s while the voice is speaking |
| Video | first visible motion vs first word | within 0.3 s |
| Sync | each hard cut vs nearest speech onset | visual lands -50..+250 ms of the onset (on or just ahead) |
| Sync | "arrive together" moments (config) | left/right motion starts within 150 ms, else FAIL |
| Sync | orphan SFX (tap/pop/click/hit) with nothing visibly changing | none |
| Frame | content touching the top/bottom/left/right edge > 0.5 s | none unless `--allow-edge` |

Speech onsets come from the word-timing JSON when there is exactly one voice clip (`assets/vo/vo-words.json` or `transcript.json`, list of `{word,start,end}`), otherwise from voice-track energy.

**Sync moments config** (`critique.moments.json` or `scripts/sync_moments.json`): `[{"label": "phone + first text arrive together", "t": 2.47}]`. For each time `t` it compares when the left half and the right half of the frame first start moving. Add one entry for every place a mockup/graphic must arrive with its text.

## Then LOOK (mandatory)

The script writes `snapshots/critique-sheet-N.png` (0.5 s per cell, 12 s per sheet). Open every sheet, and pull exact-time frames around each cut and each "arrive together" moment. Follow `references/visual-review.md`: it lists what the numbers cannot see (missing word spaces, off-screen mockups, big copy-to-mockup gaps, misaligned effects, empty holds).

## Loop

1. Render. 2. Run the critic. 3. View sheets + exact frames. 4. Fix the source (templates/compositions, never the render). 5. Re-render, re-run. Repeat until 0 FAIL, 0 unexplained WARN, and the frames look right. 6. Deliver.

## Be honest about what it cannot do

It cannot hear. Voice choice, SFX taste and music feel are unverified by ear: say so in the hand-off, give the user the numbers (levels, timing), and offer alternates (other voice takes, alternate SFX). Never claim a cut "sounds good".

## Failure classes it exists to catch (all seen in the wild)

Long pauses between voice lines; mockup arriving after its text; a 3 s screen where nothing moves; an SFX hit at t=0; cinematic booms on a UI-style ad; SFX louder than the voice; a phone positioned off-screen because CSS `translate(-50%,-50%)` was re-parsed by GSAP before the image loaded (centre with flex instead); "Trade smarter" rendering as "Tradesmarter" because inline spans' container had no font-size; text fading in over a same-coloured background failing contrast mid-fade (reveal with clip-path instead of opacity); tap ripples aimed at a button position that was guessed instead of measured.
