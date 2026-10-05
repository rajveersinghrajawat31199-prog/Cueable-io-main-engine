# Decided taste and known failures (creator reels)

## What the user has already ruled on (do not re-ask)
- **Type system (EditLobby):** thin geometric sans + italic serif accent, tight tracking (-0.02 to -0.04 em), line-height ~0.9, per-word reveal as the word is spoken (150-200 ms rise, power3.out), accent word 100-200 ms late, hard-cut swaps (no fades), big and small sizes in one frame. Roman script for Hindi (the fonts have no Devanagari). One accent colour taken from the footage.
- **Hook:** a real hook line, not a label ("HYROX tickets story time" was rejected: "nobody writes hooks like this"). Rounded pill for the figure, big italic for the subject, small sans for the twist, top-centre above the head. The hook's spoken words sit in the lower part so the title stays legible. No sound on the title. The teaser audio ends exactly on its last word (a 0.30 s pad leaked the next sentence's "ab aap"; a mid-flow cut kept the start of "marketing").
- **Cuts:** hard cuts with alternating punch-in zoom (100% / 112%, hook up to 120%). No light leaks, flashes, whips, shimmer, whooshes or swishes: rejected three times ("very annoying", "disturb the video"). Do not re-add unless asked.
- **SFX:** soft word-accent taps/pops/ticks only, >= 8 dB under the voice, never at t=0. The user chooses replacements from a numbered sampler (videos/hyrox-creator-reel/sfx-sampler); you cannot judge sound by ear.
- **Music:** supplied by the user; audible, not buried. Start the excerpt on the drum/beat entrance (the quiet intro was rejected), fade in from silence (first 120 ms silent) and out over ~2.4 s, mids (250 Hz-3.5 kHz) ducked ~14 dB while the voice speaks, ~10.8 dB under the voice by the critic. Skip file intros/outros.
- **Figures** on screen must come from the footage (the cart total ₹12,824.73 matched the spoken "12-13 hazaar").
- Pacing: length follows the voice; no static stretch over 0.7 s; every spoken idea has type; mockup/b-roll arrives with its words.

## Bugs already hit (do not repeat)
- `occ` (hook vs story occurrence of the same words) must be set per card in every loop of build.py, or hook text is timed at the story occurrence.
- SVG `vector-effect: non-scaling-stroke` breaks the stroke-dash draw trick (the line shows before its word); a zero-length round cap draws a dot: keep the underline at opacity 0 until it starts.
- ASR word `end` includes trailing silence: use energy edges (`edl_lib.py`). Whisper small is unusable on Hindi (missed 19 s); vibe-server/whisper.cpp large-v3 q5_0 hallucinated "subscribe" and gave no word times.
- The critic classifies audio by tag id: keep `vo`, `sfx`, `bgm` as separate `<audio>` tags (one pre-mixed "mix" is misread as SFX).
- A face-dimming plate that snaps on counts as a flash in the gate: fade it. Light effects were the only flash events.
- `hyperframes render` cancels itself if its parent shell exits: run it as the background command. `render` output goes to `exports/` (the `renders/` dir is deny-listed for `ls`).
- Frame-exact clip windows: never format data-start with `%g`; use the `win()` helper.
- `fromTo` applies its from-state at build time: use `immediateRender:false` and CSS opacity 0 for anything that appears later.
- zsh: `*.mp4` with no match aborts a `&&` chain; `sed -i` needs `-i ''`; `echo ======` is a zsh error.
- Download progress bars flood the context (7k tokens once): redirect to a file.
- GSAP is loaded from a CDN: renders need network (localise it if offline renders matter).
- B-roll from a phone can be portrait 4K with a rotate tag and HLG HDR: ffmpeg autorotates, crop FIRST then tone-map (zscale/tonemap), only if the source is HDR.
- Keep the source files: the HYROX talking-head original left Downloads and was never copied into the project, so a re-cut needs the user to supply it again. `new_project.py` now clones the sources into `assets/source/` (APFS clone, no extra disk); edl.py SRC points there.
