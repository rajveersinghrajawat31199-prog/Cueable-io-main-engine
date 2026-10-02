---
name: brand-archaeology
description: "Stage 1 of the brand-brief-video pipeline. Reads the raw brand sources (site captures, brand guidelines PDFs, existing films, logo files, marketing pages) exactly once and writes brand-brief.json — the compact artifact every downstream stage reads instead of the site. Also loads on triggers: 'analyse this brand', 'read the brand sources', 'derive a brand brief', 'what does this identity permit'."
---

# Brand archaeology (Stage 1)

**Role:** `brandAnalyst` · **Input:** AssetManifest + raw sources (this is the only stage
allowed to open them) · **Output:** `<project>/.pipeline/brand-brief.json` ·
**Budget:** ~60k in, ~2.5k out, ≤12 images looked at closely.

You are answering one question: **what does this identity permit?**

## Step 0 — Capture the real site (when the brief has a URL)

Before reading anything, run:

```bash
npx hyperframes capture <url> -o <project>/.capture --max-screenshots 12
```

It downloads the site's real fonts, colours, logos and screenshots as an editable project.
`.capture/` is then your source set: cite assets by ref id, and **never invent a font or a
colour** that is not in it. If capture fails or the site blocks it (login wall, bot
protection), say so plainly and fall back to manually supplied screenshots. The
`brand-brief.json` fonts, colours and logo must trace to files in `.capture/`.

## Order of work

1. **Read the mark as a diagram before anything else.** Not as an asset — as a drawing
   that may already encode the product. Hookflo's nav SVG is a 3×3 grid with one
   position empty and one dot white: a stream in which one delivery is missing and one
   is caught. That is the product, drawn by the brand, never animated by it. A
   token-extraction pass would have filed it as "logo, PNG". Write it into `markLogic`,
   or write `null` and say so.
2. **Find the inversion.** How does this brand differ from the default for its category?
   Hookflo's hero shows a small fully-enclosed terminal where the category bleeds an
   oversized dashboard off the edge: its claim is vigilance, not size. Everything
   downstream followed from noticing that one thing.
3. **Read the tension between what the site says and what it shows.** Hookflo's eyebrow
   says FAILURE-FIRST and every screenshot is green. That tension is the brand.
4. **Derive rules from compositions, not from CSS.** 6–10 `visualRules`. A rule is a
   decision you can violate, not a value you can copy. *"Semantic colour only at chip
   scale"* is a rule; `--red-500: #F94D4D` is a token.
5. **Infer motion from what the site's own motion does.** What arrives how, what
   changes brightness, what stays still, what never moves.
6. **Write "how to ruin this brand" — `failureModes`. This is required.** Not general
   motion sins: the specific generic moves *this* brand invites because of what it is.
   It is more useful than the rules are, and it is cheap: it kills bad ideas before any
   time is spent drawing them.

## Rules

- Cite evidence by `ref` id. Never describe a screenshot in prose twice.
- Carry only the tokens a film needs. This is not a design-system export.
- If you find yourself writing a paragraph, you are reporting rather than deciding. The
  brief is what every later stage reads instead of the website; everything in it is
  paid for many times over.

## Output shape

See `../brand-brief-video/references/PIPELINE.md → brand-brief.json`. Required fields:
`brand`, `identitySummary`, `productTruth`, `audience`, `markLogic` (may be `null`),
`visualRules` (6–10), `compositionRules` (2–4), `motionImplications` (4–8),
`failureModes` (non-empty).

## Approval gate

When you finish writing `brand-brief.json`:

1. Present a compact summary to the user (do NOT paste the raw JSON):
   - `identitySummary` (verbatim)
   - `productTruth` (verbatim)
   - `markLogic` (verbatim, or "null — the mark encodes nothing beyond the wordmark")
   - The top 3 `visualRules` by information density
   - Every entry in `failureModes`
2. Ask: **"Does this recognise your brand?"**
3. Wait for an explicit yes. On no, take the user's amendment, re-write the affected
   fields, and gate again. Record the gate in `approvals.json` only after the yes.

## Done when

`brand-brief.json` validates against the schema in `PIPELINE.md`, cites only refs that
exist in the AssetManifest, has a non-empty `failureModes`, serialises under ~2,000
tokens, and the user has approved the summary. The raw sources are then closed for the
rest of the run — no later stage re-opens them.
