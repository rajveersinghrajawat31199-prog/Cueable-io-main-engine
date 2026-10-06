---
name: aspect-recompose
description: Derive a NATIVE vertical (9:16), 4:5 or square cut from an already-approved horizontal HyperFrames project without re-doing voice, music, SFX, timing or story. Reuses audio and every scene timeline; only the layout layer is rewritten per scene (CSS override + a few measured JS constants), then snapshotted at true aspect, rendered, critic-gated. Use when the user wants a vertical / Reels / Shorts / Stories / 4:5 / square version of a finished film, or when a launch-video / ad is delivered and a second aspect is wanted. Never crop the master.
---

# Aspect recompose (horizontal master -> native vertical)

**Principle.** A cut is: audio + timing + copy + animation choreography + layout. Only *layout* depends on the aspect. The scene files
in this engine already key every GSAP tween to element IDs and mostly animate `opacity` / `y`, so the layout can be replaced by a
CSS override appended to each scene, leaving the approved timeline untouched. Audio is byte-identical (zero TTS / music / SFX credits).
Never centre-crop the master (half the UI is lost) and never letterbox it (phone viewers see a 16:9 strip).

## When to offer it
At delivery of any 16:9 launch video / ad / demo, ask once: **"Do you also want a vertical (9:16) version?"** (studio-intake does this;
see its question 5). If yes, run this skill on the *approved* master (changing the horizontal after the fact means re-running `build`).

## Tools (this folder, `scripts/`)
```bash
R=.claude/skills/aspect-recompose/scripts
python3 $R/recompose.py init  --src videos/P --aspect 9:16        # sibling videos/P-9x16: assets + audio + index copied, root retargeted, one stub per scene
python3 $R/recompose.py build --dst videos/P-9x16                 # (re)generate compositions/frames/* from SRC scenes + dst/recompose/<scene>.css|.json
python3 $R/recompose.py list  --dst videos/P-9x16                 # scenes, window in timeline, override size
python3 $R/snap.py --dst videos/P-9x16 [--scene 04 05] [--rel 0.6,1.5,2.4] --out DIR   # true-aspect scene sheets (scene-relative times), ~10 s each
```
`recompose/<scene>.css` is appended after the scene's own CSS (wins the cascade). `recompose/<scene>.json` is an ordered list of
`{"find","replace"[,"count"]}` edits to the scene HTML/JS; a find that does not match is an ERROR. The source scene is never edited.

## Method (per scene, ~2-5 min each once practised)
1. `init`, then `list`. Keep scene order, durations, audio. Drop scenes the master does not use.
2. **Read the scene** (CSS + body + JS). Make a layout table: hero element, what stacks, what is dropped (rarely), where the caption goes.
3. **Re-lay-out, do not scale.** Landscape pattern -> portrait pattern:
   - side-by-side panels -> stacked (chat above result panel);
   - wide table -> card rows (name over price, status chip right);
   - 5-wide tile grid -> 2 columns (10 tiles = 5 rows), logos left of label;
   - row of 4 images -> 2x2 grid (`object-fit: contain`, never crop product photos);
   - big dashboard window -> same window with fonts raised (see sizes), not shrunk;
   - side-by-side stat tiles stay side by side only if the big number still fits; otherwise stack.
4. **Type floor at 1080 px width** (phone shows it at ~1/3): body >= 34 px, UI labels/chips >= 28 px, headings 56-110 px, captions 54-64 px (wrap with `white-space:normal; text-wrap:balance`). Anything smaller is decoration only (the "chaos" hook windows).
5. **Safe zone** for Reels/Shorts/TikTok on 1920 px height: keep readable content in y 250-1540 and x 60-1020 (platform UI covers the top ~13 % and bottom ~20 %). Captions at ~1380-1450.
6. **Audit the JS for hard-coded geometry** (the only thing the CSS cannot fix). `grep -n "x:[0-9]\|y:[0-9]\|1560\|1150\|limit\|offsetTop"`:
   - cursor entry/exit points (landscape used x 1560, y 1150) -> off-frame bottom-right for the new size;
   - cursor targets: use measured positions (`offsetLeft/Top` walk to `#root`, or the scene's own `pos()` helper) instead of constants; subtract any chat scroll offset;
   - chat / list scroll limits (`const limit = 586`, `- 586`) -> visible height minus composer;
   - if a shorter chat now clips a message the cursor must hit, add the scroll tween and the initial `gsap.set(msgs,{y:-S})` in the next scene (scenes hand off state);
   - SVG stitch paths / masks / gradients / viewBox, orbit centres, `transformOrigin` in pixels;
   - GSAP `x`/`y` in pixels that were tuned for a zoomed element (see below).
7. **`zoom` for dense decorative clusters**: `.win{zoom:1.45}` scales an element and its own transforms, so existing `y:-10` stacking offsets scale with it. Re-anchor wrappers, and divide any absolute-pixel `place()` maths by the zoom factor.
8. **Continuity**: a logo/star that hands off between scenes must land on the same screen pixel in the next scene (compute from the SVG viewBox ratio, not by eye).
9. `build`, `snap` the scene at 3 times (early, mid, end state), look at the sheet, fix, repeat. Then `npx hyperframes check` (0 errors; info-level overlaps from animated swaps are normal).
10. Draft render, then `critique.py` and read the true-aspect sheets (the critic's own sheets are squashed to landscape cells). Audio warnings are inherited from the horizontal master; judge only what is new: text size, clipping, safe zone, cursor landing, dead space.
11. Final render at the master's spec (`--resolution portrait-4k --fps 60 --quality high` if the master is 4K60), then `scripts/master.sh` (loudness) from the source project. Hand-off: `job_receipt.py report`, and say audio/taste are unverified by ear.

## Rules learned on ShopOS (first use)
- Layout-only recompose kept 100 % of the approved audio and animation timing; no new TTS, music or SFX credit.
- Cursor and chat-scroll constants are where recompose silently breaks: always snapshot the *end* state of every scene.
- The hook's pile/orbit/stitch used pixel centres; one table (CARDS, C0, STAR, R0, stitch path) re-targets it.
- `data-layout-allow-*` flags already on elements carry over; the layout checker flags only genuinely new overlaps (a stat number whose line-height < font-size).
- `renders/` is deny-listed for reads in this workspace: render finals to `exports/`.

- **Client review round 1 (ShopOS) - three things a snapshot check missed, now rules:**
  1. *Logo lockups and brand units are smaller in portrait than a "fill the width" reflex suggests.* Keep a wordmark unit <= ~2/3 of frame width (720 of 1080) with >= 180 px side margins; the CTA button and URL under it shrink with it. The same lockup appears in the hook's end star, the intro scene and the end card: change all three together and recompute the star's screen pixel (`left + 134.66*W/181`, `top + 20.16*W/181`) so the cut stays invisible.
  2. *Decorative outlines (stitch / frame / highlight) must contain the whole cluster including rotated and zoomed windows.* Size them from the cluster's measured extent plus >= 35 px padding, symmetric about the cluster's visual centre, and look at the frame where the outline finishes drawing, not only mid-draw.
  3. *Review at true aspect, at the end state of each animation,* before showing the client: edge proximity and clipped tabs only show there.

## Not covered yet
Scenes that need a different *story* in vertical (re-cut, new hook), 4:5 / 1:1 recipes (same tools, new table), automatic layout (the per-scene design step is manual and is where the time goes).
