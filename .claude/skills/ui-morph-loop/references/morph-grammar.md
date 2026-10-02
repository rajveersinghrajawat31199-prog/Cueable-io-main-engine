# Morph grammar (what we learned building it)

## Timing model
- **Beat grid:** 120 bpm = 0.5 s/beat, 4 beats/bar, 8 bars = 16 s. States start on half-beats (`check_morph.py` WARNs otherwise). Downbeats for the big moments (dashboard, palette, final logo), beats for the rest.
- **Spring settle times (to 1%, computed):** snappy k320/d30 0.25 s (0.8% overshoot), default k170/d26 0.51 s (none), heavy k90/d20 0.79 s (none), trail k140/d22 0.48 s, playful k220/d14 0.60 s (18.6% overshoot). Use `HFMorph.settle(preset)`. A cursor `arrive: beat` key starts moving `settle` seconds earlier so the tip is ON target by that beat.
- **Click -> morph:** click lands `cursor.lead` = 0.16 s before the morph beat: press-down 0.10 s (power2.in) + release 0.22 s (power2.out); the shape itself dips 3.5% on every click. Everything the click reveals (a toggle moving, a highlight) must happen in the 0.06 s before the layer starts clearing.
- **Content swap:** in after 0.14 s (+0.16 s fade) so the text arrives when the shape is about 90% grown, out from 0.10 s to 0.04 s before the next morph, with up to 8 px blur at the ends. That leaves about 0.18 s of "shape only" at each morph: the intended blink. Override per state with `swap:{inDelay,inDur,outLead,outDur}`.

## Loop rules (checked by `check_morph.py` + `check_loop.py`)
1. Last state has the same geometry, fill and layer as the first (reuse `layer:` + same numbers).
2. Last morph starts >= 1.0 s before the end (residual at t=DUR < 0.5%).
3. Cursor parked off-screen at 0 and at DUR (same pose = same velocity = 0).
4. Anything periodic must have a period dividing the duration (a 4 s orbit in a 16 s film), or be a one-shot that ends at 0 (`bumpCurve`).
5. Seam metric: last->first change must be within 2x the largest ordinary step near the seam.

## Every beat alive
Ways to give a beat something to do without adding noise: cursor travel (a 130 px sprite changes many pixels), count-ups, staggered bars, typing, a highlight stretching between rows (`indicator`), a ping ring from a data point, a beat `pulse` on hold states (0 at the beat's start and after 0.45 s so morphs stay clean). The checker counts changed pixels per 1/30 s at 216 px wide (default floor 20 px); tune with `--dead-px`.

## Motion blur (subframes) and what it breaks
- `render_blur.sh` renders at fps x sub (max 240) and averages `SHUTTER*sub/360` subframes with `tmix`, keeping one per output frame. Output is worker-count independent (byte-identical 1 vs 4 workers).
- **Ghosting:** anything that changes value between subframes double-exposes. Digits and typed characters must be constant within an output frame: use `api.q(lt)` (floor to `FILM.fps`). Real motion (cursor, morph edges, spinner) should NOT be quantised: that is what blur is for.
- **Second ghosting cause (found in review, fixed):** the renderer's capture times are not exact multiples of 1/(fps*sub) (up to about 1 ms off at 240 fps). A plain `floor(t*fps)` put 1 in 3 group boundaries one subframe late, so two different numbers were averaged. `api.q` adds a 0.12-frame bias. Symptom: digits look double-printed on some frames only. Verify with the phase test: render at fps*sub, find where a digit region changes; every change must fall on `frame_index % sub == 0`.
- 180 deg is film-style; 360 deg smears about twice as much. Do not blur text you want read: quantise it and it stays sharp.

## Layout and content
- Every layer is authored at its state's final size and centred; the shape clips it mid-morph (`data-layout-allow-overflow` on `.layer`).
- Text >= 48 px on a 1080-wide canvas (readable at 360 px). One accent. No corner labels, no frame borders, no glow on chrome.
- Fill morphs are straight RGB lerps, so ink -> paper passes through grey. Accept it (physical) or route through a mid colour by adding an intermediate key.
- Shadow scales with a per-state `shadow` (0..1); small shapes get less.

## Formats
- 9:16 (1080x1920) is the design target: stage centre about (540, 900), shapes <= 940 wide.
- 1:1 and 16:9: change `w,h`, `stage`, each state's geometry and the cursor coordinates (they are absolute). Keep one `film.js` per aspect that shares `states` ids and beats; do not crop a 9:16 render.

## Lessons from the demo build (each one a real bug or finding)
- The engine docs' "width/height tweens are forbidden" is really "avoid for perf": lint/runtime/layout/contrast pass with a proxy `onUpdate` driving width/height/radius.
- `data-layer` is a deprecated attribute name in lint; we use `data-mlayer`. The timeline must be registered by an inline script in `index.html` (lint cannot see registrations inside external JS).
- The cursor must live inside `#world` or a camera push misaligns it from its targets.
- First tooltip clipped by the card edge; palette had 100 px of dead space; content appeared while the shape was 73% grown: all caught from the beat sheet, not from code.
- The critic's "dead beat" check first used mean luma change and mislabelled typing beats; pixel-count activity separates them. It is normalised to 1/30 s so the threshold does not depend on render fps.
