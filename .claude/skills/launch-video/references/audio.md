# Audio: voice, SFX, music (numbers are evidence; taste is unverified by ear)

## Voice: one continuous take
Stock `audio.mjs` makes one TTS call per frame; every clip gets its own edge pacing and end-of-utterance decay. Instead:
`scripts/gen_vo.py` sends the whole SCRIPT.md as ONE call with timestamps, respells brand names for TTS (config
`voice.respell`, e.g. "ShopOS" -> "Shop O S"; merged back so word times stay per script word), cuts per-frame clips at the
midpoint of the gaps, writes `audio_meta.json`, and warns if the final word is >=15 dB quieter than a mid-take word.
- Voice choice: pick by metadata (I cannot listen); American, calm/confident for SaaS launch. Record in `launch.config.json`.
- Balance counter lags real usage; a 60s script is ~650 characters.
- Uncommon proper nouns: hyphenate/respell for TTS rather than re-rolling.

## Timing
- **Never start speech at t=0**: `audio.lead` (0.3s on frame 1) adds silence + a 50ms fade-in. Critique FAILs otherwise.
- **Length follows the voice.** `pad_vo.py` only appends trailing silence per frame (`audio.targets` are floors), giving UI
  frames time to act. Then `audio.mjs sync-durations` writes the durations into STORYBOARD.md. Frame files' internal
  `data-duration` MUST equal those durations: rebuild frames after changing targets.
- Keep silent tails <= ~2s and filled with SFX; the critic warns on 1-3s voice gaps: that is expected for UI action.
- Cuts land 0-250ms BEFORE the word they introduce (critic PASS window -50..+250ms).

## SFX (light UI only)
Palette: `scripts/sfx_palette.json` (Kenney CC0 + Sonniss UI, from `~/hyperframes-assets/sfx`), all peak-normalised to -11 dBFS,
each with a volume cap. Cue list lives in `launch.config.json` (`sfx.cues`, `sfx.recipes`), e.g. a `stagger` recipe for "one pop per element".
- Map: press -> `click`; typing -> `tick` every 3rd char; chip flip / checklist -> `toggle`; element arrival -> `pop2/pop2a/pop2b`
  rotated (one per element, on its entrance beat); seam -> soft `slide`; count-up -> `up`; accent lands -> `pop`.
- **Never** cinematic booms/risers/sci-fi whooshes; **nothing at t=0**; every cue tied to a visible event or a word.
- Critic limits: <= 5 cues in any 1s window; each cue >= 8 dB under the voice where they overlap (typing ticks over speech
  need volume ~0.1-0.16, or move them into pauses).
- Search the library, don't list it: `python3 ~/hyperframes-assets/sfx/_index/search.py <terms> --limit 10`.

## Music bed
- **No synthesised music. Ask before adding.** The HeyGen catalog needs sign-in; the shared library has no music. Real tracks
  come from the user (Downloads, Epidemic Sound, Artlist, Pixabay) or the user's own licence.
- Choose by **measurement**: `scripts/measure_music.py [--ref reference.mp4] tracks...` reports pulse density, steadiness,
  brightness and the best steady window. The character of an upbeat modern launch bed: pulse ~4/s, tempo ~110-125, brightness
  ~2.4-3.2 kHz, level swing < ~3 dB, no drop. "Corporate/business event" beds measure dark (~1.4 kHz) and read traditional.
- Mix: adelay 0.3s + fade-in ~1.4s, fade-out ~2.6s, `bgm.volume` tuned until the critic says **9-18 dB under the voice**
  (target ~10-12 for an upbeat bed; ~0.115 for a track of about -11 dB RMS). Bed length = film length.
- Flag the licence in the final message every time.
