# Critic gates (run before the user sees any cut)

`python3 ~/.claude/skills/video-critique/scripts/critique.py renders/<file>.mp4 --project .` then LOOK at
`snapshots/critique-sheet-*.png` and pull exact-time frames for anything suspicious. Also `hyperframes snapshot --at ...`.

| Finding | Action |
|---|---|
| FAIL abrupt opening | `audio.lead` 0.3s on frame 1 (speech never at 0.00s) |
| WARN static screen > ~0.7s | add purposeful motion (skeleton fill, state change) or trim the frame's hold; a deliberate final hold is fine |
| WARN voice gap 1-3s | expected for UI-action tails; keep <= ~2.5s and fill with SFX; trim if the UI finishes early |
| WARN SFX < 8 dB under voice | lower that cue (typing ticks 0.1-0.16) or move it into a pause |
| WARN SFX density > 5 per 1s | thin the cascade (first of each row, not every element) |
| music 9-18 dB under voice | tune `bgm.volume` (BGM_VOL env), re-run gen_sfx.py |
| music tail fade < 6 dB / opens hot | fade-out/adelay+fade-in already in gen_sfx.py; check `bgm.duration_s` == film length |
| loudness -20..-12 LUFS, peak <= -1 | raise/lower voice or bed; don't clip |
| hard cut vs speech onset (-50..+250 ms) | cuts land just BEFORE the word they introduce |

## Human-taste checks the critic cannot do (do them from snapshots)
- Text never crowded/overlapping mid-transition (e.g. two panel headers overlapping during a swap: sequence exit then entry).
- No dead white area while VO talks. No element cropped at the frame edge. Images uncropped.
- The logo ends on the exact supplied unit (gradient intact).
- Cursor tip lands ON its target; every press changes something.
- Numbers readable at thumbnail size.
- Copy is this brand's, not a reference video's.

## Final message must say
Path + duration; critic result (0 FAIL, N WARN and which are intended); "audio and taste unverified by ear"; licence notes
(music, voice); which figures are illustrative; how to adjust (music louder/quieter, different section).
