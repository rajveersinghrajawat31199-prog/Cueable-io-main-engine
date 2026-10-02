# Feel notes: steering vocabulary

Plain words the user can say, and the GSAP recipe each maps to. Match cuts and pull back
also live in `/cut-the-curve` and `/seam-craft`; use those for seams. `T` is the global
timing scale (see bottom).

| Phrase | Meaning | Recipe |
|---|---|---|
| **push in** | camera moves toward the subject | `tl.fromTo(stage,{scale:1},{scale:1.15,duration:1.2*T,ease:"power2.inOut"})`, transform-origin on the subject |
| **pull back** | reveal context, scale down | inverse of push in; see `/cut-the-curve` mirrored zoom |
| **pan** | slide the stage sideways/up | `tl.to(stage,{x:-240,duration:1.4*T,ease:"power2.inOut"})`; never pan and scale on a CSS transform that also holds a static one (`gsap_css_transform_conflict`) |
| **hard cut** | instant swap, no easing | set visibility with `tl.set(next,{autoAlpha:1},t).set(prev,{autoAlpha:0},t)` |
| **match cut** | next scene starts where the last ended, same shape/position | `/cut-the-curve` velocity-matched seams |
| **motion blur** | blur proportional to speed on a fast move | `tl.to(el,{filter:"blur(10px)",duration:0.08*T,yoyo:true,repeat:1})` around the move; 10px text, 18-20px full frame |
| **easing** | how a move accelerates | fast in, slow settle: `power3.out`; slow-fast-slow: `power2.inOut`; snap: `expo.out` |
| **cursor enters from off-screen** | pointer travels in, never spawns | start the cursor outside the frame, animate to the tip target; see `/oversized-cursor` |
| **outgoing leaves left, next enters right** | directional continuity | outgoing `x:-W*0.12` + fade with `power4.in`, incoming from `x:+W*0.12` with `power4.out` (vector law, `/motion-doctrine`) |
| **slow every zoom and pan to 0.7x** | global speed multiplier | change `T` once; durations of camera moves scale, content does not |

## Global timing scale

Define one variable in the score/scene (`S.timingScale`, default `1`; `--timing-scale` CSS
var if CSS uses it) and multiply **every camera-move duration** by it (`duration: d * S.timingScale`).
Do not multiply cue times or content durations; only camera moves. Retiming a whole film is
then one number, not a hunt through tweens.
