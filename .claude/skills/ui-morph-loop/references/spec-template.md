# Spec template (state list, not a vibe)

Adapted from the XML spec that twoclipping / verbove used, made to fit our pipeline. Fill it in `BRIEF.md`; the **state list on the
beat grid is the approval gate** (stage 3), before any content is built. An agent then turns it into `film.js` + `index.html`.

```xml
<inputs>
Product + URL: ...
8-12 UI states that tell its story (in order): ...
Real data shown in each state (brand's own published figures, or mark ILLUSTRATIVE): ...
Tokens: canvas, ink, paper, ONE accent; display + UI fonts (licensed for video): ...
Formats: 9:16 first, then 1:1 / 16:9 (re-authored per aspect)
Duration: 16 s = 8 bars @ 120 bpm (or measured track: <file>, bpm, first downbeat)
Sound: silent | SFX from palette | SFX + a track the user approved
</inputs>

<direction>
One container never cuts: every state is the same element changing size, radius and fill while its content swaps behind a
short blur. A cursor drives every user-initiated change. Springs with at most a tiny overshoot on UI, none on type.
Banned: bouncy easing, glows, gradients on UI chrome, particle bursts, dead beats, corner labels, centred title on a gradient.
</direction>

<structure>
Beat  State      Shape (w x h, r, fill)   Content / what moves                        Cursor            Sound
0     logo       240x240 r120 accent      ring pulse (one beat only: the hook is the first morph)  parked off-screen  -
1     cta        700x170 r85 ink          "Get started"                               enters, arrives b4.6  pop
3     email      820x170 r44 paper        types the address b5.4 -> b8                aside, then arrow   click (b5-0.16), tick x6
...   ...
28    logo       == first state (loop), end card holds the freed beats                                                 off-screen          -
</structure>

<build>
1. film.js is the score: beats, geometry, cursor, per-state content functions. index.html holds only layer markup.
2. Text inside a morphing shape enters after the morph starts (default 0.14 s) and leaves just before the next (0.04 s early).
3. Discrete text through api.q(). Everything a pure function of t: no timers, no Math.random, no CSS transitions.
4. Last state == first state; last morph starts >= 1.0 s before the end (residual < 0.5%); cursor off-screen at both ends.
5. Render: draft 30 fps for iteration; final 60 fps x 4 subframes, 180 deg shutter (scripts/render_blur.sh).
</build>

<gotchas>
- Never `will-change` on anything the camera scales (blurry text).
- A click lands `lead` (0.16 s) BEFORE the morph beat, and its content reaction must be visible before the layer fades.
- Hold states need `pulse:`; typing/count beats are alive only if the pixels really change (check_loop measures it).
</gotchas>

<start>
Ask for the inputs, then show me the state list on the beat grid (the <structure> table) and STOP for my OK before writing content.
</start>
```

## Prompt to hand the agent (after the state list is approved)
> Using `/ui-morph-loop`: scaffold `videos/<name>`, implement the approved state list in `film.js` and the layer markup in `index.html`
> in the brand's tokens (rebuild the UI, never paste screenshots), then run `check_morph.py`, `still.py --beat ... --sheet` and show me
> the stills. Do not render video until I approve the stills.
