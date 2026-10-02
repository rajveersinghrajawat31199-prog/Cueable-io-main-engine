# Design system step: what the stock script gets wrong, and the fix

## Step 2 of the stock pipeline: `build-frame.mjs --preset <name>`
It copies a shipped preset's FRAME.md and **remixes it onto the capture's brand colours by role**. Two failure modes seen:

1. **It remaps from usage statistics (`colorStats`), not from `tokens.json` `colors`.** A dark marketing site + a light-theme
   brief produced a black canvas, grey text and a green "muted" colour, with no warning. Editing `tokens.json` does not help.
2. **All 13 shipped presets are stylised editorial looks** (poster, brutalist, riso, picture-book...). None is a clean
   product-UI look. The closest (`blue-professional`: warm cream, restrained, soft cards, no shadows) works as a *base* only.

### Procedure
1. Run `build-frame.mjs` with the closest preset. Record the preset as a preference.
2. **Read the resulting `frame.md` colours and compare to the brief's theme.** Check: canvas luminance matches light/dark;
   text is the darkest ink on light (or lightest on dark); accent is the brand accent; muted is a neutral grey.
3. **Hand-correct the frontmatter `colors:` block** (documented as allowed by the workflow) and leave a comment saying it was
   hand-corrected and why. Prose that says "cobalt"/"cream" means whatever the frontmatter says.
4. Source canvas/ink/neutrals from the **app's own CSS variables** (`--page-bg`, `--primary`, `--foreground`), not the
   marketing page; the product UI is what the video shows. Take accents from the logo/brand.
5. Add extra named tokens (e.g. `accent-*`) for a brand gradient. Ration them: icon chips, highlight underlines, the final
   logo. Never full-frame backgrounds.

## Typography
- Fonts must exist as staged files (`assets/fonts/*.woff2` referenced by frame.md `@font-face`). Use `lv_lib.Project.fonts()`.
- **One primary family for UI. One secondary face for a single emphasised word** (e.g. an italic serif from the brand's own
  font set). Use it at most once per frame and at most ~3 times per film (claim word, caption-closing word). It is set
  ~1.15-1.2em, weight 500, tight tracking.
- **Highlight = thin gradient underline, 4px** (rounded), drawn left-to-right (`scaleX`) on the word's VO onset. The same
  4px everywhere it appears (claim, caption, in-UI highlight). 8px reads heavy.

## Logo
- Use the supplied file exactly. Never redraw. Make a recoloured copy for the background (e.g. white wordmark -> ink on
  light); leave the gradient/colour part untouched.
- To animate parts, inline the SVG: letters as separate paths, the accent as its own group.
- **Accent animation rule:** translate and scale on *nested* groups; set `svgOrigin` once with `gsap.set`, never repeat it
  across consecutive tweens on the same group (GSAP mis-compensates and the mark ends up off-canvas). Colour travel: tween the
  gradient's `x1/x2` (attr) from an offset position to its ORIGINAL values so the mark ends on the exact supplied gradient.
- SVG `overflow: visible` when a scaled part exceeds the viewBox.
