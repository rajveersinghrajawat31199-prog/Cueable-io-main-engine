---
name: thinking-orbs
description: Use when a demo or launch video is for an AI / agent / automation / voice product and wants the modern "something is thinking" motif: a dotted 3D orb (9 states: working, searching, solving, listening, connecting, weaving, composing, breathing, shaping) as a hero object, an agent-status indicator inside rebuilt UI, or a state sequence that mirrors what the agent does. thinking-orbs by Jakub Antalik (MIT), seek-exact in renders, recoloured to the brand.
---

# Thinking orbs in videos

What they are: dotted, honestly-3D spheres/rings/ribbons drawn on a 2D canvas (depth by dot size and ink weight). Upstream (`thinking-orbs` 0.3.2, MIT, github.com/Jakubantalik/thinking-orbs) is an AI-UI loading indicator. Its engine is a **pure function of time** (`MODE_FRAMES[mode](size, t, opts)` -> finished dots), so unlike Hairline no virtual clock is needed: `seek(t)` draws exactly frame t. Vendored in `tools/orbs/` with our driver (`src/driver.js`): brand tint, state timeline with cross-fades, GSAP binding.

## The nine states (what each says)
| state | looks like | say it when the agent is... |
| --- | --- | --- |
| working | particles on tilted orbits | running a job in the background |
| searching | scan line sweeps a dotted globe | searching / retrieving / researching |
| solving | bands scramble, click back solved | reasoning, debugging, optimizing |
| listening | waveform rolling through rings | hearing voice / calls / meetings |
| connecting | a constellation wires itself | pulling in tools, integrations, a knowledge graph |
| weaving | three strands plait | orchestrating / merging threads or agents |
| composing | undulating sash | writing, drafting, generating |
| breathing | ring slowly morphing | idle, ready, calm |
| shaping | outline circle -> triangle -> square | designing, building, modelling |
Two tunings: `size: 64` (hero / avatar) and `size: 20` (inline next to text). They are separate designs, not a scale: render the 64 big for a hero, use 20 only small (about 40-80 px) beside a label.

## Automatic use (the engine decides; the user runs nothing)
Called from `/studio-intake` step 2b and `/launch-video` stages 3, 7, 9.
1. **Pick**: `python3 tools/orbs/orbs_scene.py pick "<message + proof points + tagline + category>"`. It only answers for an AI / agent / automation / voice story ("no orb" otherwise: the orb means *something is thinking*; a boutique sale or a payments rail does not get one). It suggests a 2-3 state sequence; reorder to the story (the order the agent does things).
2. **Decide** (all must hold): AI/agent story; the brand tone fits a calm, technical dot-matrix motif; a slot exists: (a) **hero**: hook or end card, large (520-700 px), states stepping with the voice-over; (b) **status in rebuilt UI**: a 40-80 px size-20 orb in the chat bubble / button / status pill, driven by the same timeline as the UI action; (c) **section break** between proof points. Budget with Hairline combined: at most 2 decorative objects per 60 s. The orb never replaces the rebuilt product UI. For (b) the visible state must match what the UI text says ("Searching CRM…" = `searching`).
3. **Build**: `python3 tools/orbs/orbs_scene.py make --project videos/<p> --states "searching:0,solving:2.4,composing:4.8" --start <s> --dur <s> --box x,y,px --ink <brand accent or white> --bg <the colour behind the orb, from frame.md> [--size 20] [--fade 0.3]`. Installs `assets/orbs.bundle.js`, writes `assets/orbs/<id>.html` + `.json`. Paste the fragment into the beat, load the bundle in `<head>` after GSAP, call `window.__ORBS.bind(tl, TOTAL)` ONCE, last. State times are in film seconds; align them with the VO words (voice is the clock). `bg` must really be the colour behind the orb: far dots fade into it.
4. **Gate** before the critic: `python3 tools/hairline/check_figures.py renders/<x>.mp4 videos/<p> assets/orbs` prints only PASS.
5. Record `orbs:` in BRIEF.md (state sequence, beat, why) and `ui: orb <states>` in the storyboard frame.

## Colour
`ink` = nearest dots, `bg` = the colour far dots dissolve into, depth ramp in between. One brand accent on the dark plate (orange in the proof) or white on a brand colour reads best; avoid ink and bg with low contrast. Light themes: dark ink on a light bg.

## Verified
- All 9 states x 2 sizes draw and move; identical canvas for the same t after seeking anywhere (hashed).
- HyperFrames 0.8.34: lint clean, 7.2 s 1080p draft render 10 s, hero + inline orb through three states, gate PASS.
## Not verified
- 4K render time, nested sub-compositions, Studio scrubbing UI, taste/audio.
- `dots` / `dotSize` density props and the cursor "gravity" effect of 0.3.2 are not wired (raw engine knobs go through `opts: {...}` in `scene.add`; gravity needs the live pointer: for a video, fake it with `/oversized-cursor` instead).
- A previous-version note: the library's own `color` tint is a different ramp; ours mixes ink into bg.

## Refresh
`npm view thinking-orbs version`, re-copy `dist/engine.es.js`, `dist/index-*.js` (fix the import name in `lib/engine.es.js` if the chunk hash changes) and `dist/engine/*.d.ts` into `tools/orbs/lib/`, rebuild: `npx --yes esbuild tools/orbs/src/driver.js --bundle --format=iife --global-name=Orbs --outfile=tools/orbs/dist/orbs.bundle.js`, re-run `tools/orbs/test/catalog.html` (serve `tools/orbs`, launch config `orbs-test`).
