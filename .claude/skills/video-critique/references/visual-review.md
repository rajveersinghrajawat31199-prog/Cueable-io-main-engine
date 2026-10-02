# Visual review checklist (do this after the script, every time)

The metrics are blunt. The sheets are where layout and polish bugs show. Look at every cell.

## Get the pictures

```bash
# contact sheets are already in snapshots/ (critique-sheet-N.png, 0.5 s per cell, row-major, 4 columns)
# exact frames around a cut at time T (seconds); view them together as a strip:
for t in 3.70 3.90 4.10 4.20 4.25 4.30 4.40; do ffmpeg -y -v error -ss $t -i render.mp4 -frames:v 1 -vf scale=480:270 f_$t.png; done
ffmpeg -y -v error -pattern_type glob -i "f_*.png" -filter_complex "tile=4x2" strip.png
```

Tile order from a glob is alphabetical, not chronological: name files so they sort right, or label them. Sheet sampling can be a frame or two off: confirm anything suspicious with an exact-time frame before "fixing" it (a "missing text" cell was just sampling).

## What to check in the pictures

1. **Word spacing**: every phrase reads with normal spaces ("Trade smarter", not "Tradesmarter"). Inline-block spans need a container with an explicit font-size, or the space glyph inherits 16 px.
2. **Nothing cropped or off-screen**: mockups, logos, numbers fully inside the frame at every sampled time. Centre with flex, not CSS percent-translate that GSAP re-parses.
3. **Copy-to-mockup gap**: with copy left and a phone right, the gap should look intentional and margins roughly symmetric. If a block is narrow, enlarge its type rather than leaving a hole.
4. **Text and mockup arrive together**: same tween start; never text first then image.
5. **Cut frames**: the first frame after a hard cut may be one frame short of content; more than that is a bug. No overlap of the outgoing and incoming text.
6. **Effects hit real targets**: tap ripples/glows on a button must use the button's measured centre in screen px (find the pixels in the source PNG, scale by the image's display scale), not a guess.
7. **Holds have life**: any moment longer than ~0.7 s should have drift, float, count-up, or an event. Drift must return to 0 by the end of the frame so hard cuts don't pop.
8. **Mid-fade legibility**: text revealing over a similar colour (white on white button) fails contrast mid-fade; reveal with clip-path or scale instead of opacity.
9. **Numbers/data correct**: what is on screen matches the brief (figures, names, legal line).
10. **Brand assets**: logo not stretched, clipped or low-res; brand colours only where intended.
11. **Duplication**: visual, mockup and voice should not all repeat the same fact (captions of the voice are fine when the user asked for them).

## Audio: what to state, since you cannot hear

Report the measured numbers (loudness, SFX margin under voice, music level) and list what the user should listen for: voice clarity vs SFX, whether taps feel too busy, whether the music bed fights the voice. Offer swaps (other voice takes, quieter SFX volume, no music).
