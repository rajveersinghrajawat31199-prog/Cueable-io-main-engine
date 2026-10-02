# Pipeline artifact contracts

Every stage reads and writes JSON files under `<project>/.pipeline/`. Each contract
below is the minimum shape a downstream stage assumes. A stage that emits less is a
failed run; a stage that emits more is fine — every schema is `Extensible`.

## brand-brief.json (from `/brand-archaeology`)

```jsonc
{
  "brand": "hookflo",
  "identitySummary": "…",
  "productTruth": "…",
  "audience": "…",
  "markLogic": "…" ,           // or null, with a note explaining why
  "inversions": ["…"],
  "visualRules":       [{ "id": "R1", "text": "…", "evidence": ["ref_12"] }],
  "compositionRules":  [{ "id": "C1", "text": "…", "evidence": ["ref_08"] }],
  "motionImplications":[{ "id": "M1", "text": "…", "evidence": ["ref_03"] }],
  "failureModes":      [{ "id": "F1", "text": "…" }],   // REQUIRED, non-empty
  "tokens": { "ground": "#08080B", "lavender": "#B7A6FF" },
  "signatureRefs": ["ref_01", "ref_04", "ref_12"]
}
```

Budget: aim for < 2,000 tokens serialised. If it does not fit, archaeology reported
instead of decided.

## creative-direction.json (from `/creative-direction`)

```jsonc
{
  "brand": "hookflo",
  "chosenId": "missing-dot",
  "pitch": "≤60 words. The film's whole idea in one paragraph.",
  "mode": "continuity",              // or "edit"
  "format": "16:9",                  // or "9:16", "1:1"
  "duration": 25,                    // seconds
  "heroMotif": "the dot that is missing from the row",
  "spatialLogic": "one panel, centred, held; nothing moves that is not the mark",
  "continuityRules": [
    { "id": "K1", "text": "the row is mounted once and never unmounted" }
  ],
  "forbiddenBehaviours": [
    { "id": "X1", "text": "particles / bloom / any glow", "source": "brief.F3" }
  ],
  "densityArc": [                    // one entry per pacingArc state, 0–1
    { "id": "arrive", "density": 0.35 },
    { "id": "stream", "density": 0.55 },
    { "id": "drop",   "density": 0.95 },
    { "id": "detect", "density": 0.10 }
  ],
  "pacingArc":  ["arrive","stream","drop","detect"],
  "salvaged": [                      // what the losing pitches contributed
    { "from": "scan",         "took": "the detection mechanism" },
    { "from": "silent-night", "took": "the persistent clock"    }
  ]
}
```

Also writes `direction-candidates.json` — the three pitches with scores. Nothing
downstream reads it; it exists for the audit trail.

## storyboard.json (from `/storyboard`)

```jsonc
{
  "brand": "hookflo",
  "directionId": "missing-dot",
  "states": [
    {
      "id": "arrive",
      "beat": "hook",
      "visual": "the mark at rest; the row's third-from-left dot is white; every other dot is muted lavender",
      "copy": null,                  // verbatim if present; nothing invented later
      "persists": ["row", "mark"],
      "entering": [],
      "leaving": []
    }
  ],
  "critique": [                      // findings from the self-critique pass
    {
      "state": "drop",
      "finding": "the state's claim (the system does not know) is invisible in a still",
      "fix": "add a running counter beside the missing dot"
    }
  ]
}
```

## score.json (from `/score`) — continuity mode

```jsonc
{
  "storyboardId": "missing-dot",
  "fps": 60,
  "duration": 1500,                  // frames (25s @ 60fps)
  "space": { "w": 1920, "h": 1080 }, // adopt design-file space; scale once at root
  "states": [
    { "id": "arrive", "from": 0,   "to": 300 },
    { "id": "stream", "from": 300, "to": 900 }
  ],
  "cues": {                          // named numbers or arrays (metronomes)
    "travel":     360,               // a single moment
    "beatStep":   12,                // suffix "Step" = per-item interval
    "rowMeter":   [12, 24, 36, 48]   // an array = a metronome
  },
  "geometry": {                      // in `space` units, nested by object
    "row":  { "y": 540, "cell": 96, "count": 9 },
    "mark": { "cx": 960, "cy": 540, "r": 24 }
  },
  "content": {                       // data tables the composition renders
    "labels": ["one","two","three","…","nine"]
  },
  "continuity": [                    // checked by the critic; restate direction rules
    { "id": "K1", "text": "the row is mounted once" }
  ]
}
```

## score.json — edit mode (CompositionPlan-shaped)

```jsonc
{
  "storyboardId": "atomic-teaser",
  "brand": "atomic",
  "format": "16:9",
  "duration": 25,                    // seconds
  "story": [
    { "beat": "hook",
      "pattern": "knockout-statement",
      "content": { "headline": ["…"], "media": [{ "src": "media/…" }] } },
    { "beat": "proof",
      "pattern": "stat-tiles", "transition": "wave",
      "content": { "stats": [{ "value": "300+", "caption": "…" }] } },
    { "beat": "close",
      "pattern": "logo-outro", "transition": "fade",
      "content": { "logo": { "src": "media/logos/…" }, "cta": "…" } }
  ]
}
```

## render-state.json (from `/hyperframes-build` and `/visual-critique`)

```jsonc
{
  "buildId": "2026-01-14T12:00Z",
  "artifacts": {
    "brief":     "brand-brief.json@sha:…",
    "direction": "creative-direction.json@sha:…",
    "storyboard":"storyboard.json@sha:…",
    "score":     "score.json@sha:…"
  },
  "scenes": [
    { "id": "arrive", "file": "compositions/scene-01-arrive.html",
      "lint": "passed", "check": "passed",
      "qaFrame": "compositions/qa/arrive.png",
      "approvedAt": "2026-01-14T12:04Z" }
  ],
  "contactSheet": "out/contact-sheet.png",
  "critique": {
    "status": "changes-requested",   // or "passed"
    "findings": [
      { "state": "drop",
        "violates": "direction.forbiddenBehaviours[3]",
        "finding": "the meter reads as a generic particle system",
        "fix": "rebuild as two orthogonal legs" }
    ]
  }
}
```

## approvals.json (the router writes this)

```jsonc
{
  "runId": "2026-01-14T11:00Z",
  "gates": [
    { "stage": "brief",       "at": "2026-01-14T11:12Z", "note": "identity summary matches; failureModes complete" },
    { "stage": "direction",   "at": "2026-01-14T11:24Z", "note": "chose missing-dot over scan and silent-night" },
    { "stage": "storyboard",  "at": "2026-01-14T11:41Z", "note": "critique fixes applied" },
    { "stage": "storyboard-stills", "at": "2026-01-14T11:46Z", "note": "stills grid approved; build may start" },
    { "stage": "score",       "at": "2026-01-14T11:50Z", "note": "" },
    { "stage": "scene.arrive","at": "2026-01-14T12:04Z", "note": "" }
  ]
}
```

## Gate protocol

At every gate the router presents a *compact* summary of the artifact (not the raw JSON)
and one specific yes/no question. Examples:

- **Brief gate:** "Does this recognise your brand? (identity, product truth, failure modes)"
- **Direction gate:** "Is this the film? (heroMotif + densityArc)"
- **Storyboard gate:** "Are these the beats, in this order?"
- **Stills gate:** "Are these the frames?" (rendered grid, one still per state; required before build)
- **Score gate:** "Does the timing feel right? (duration, per-state seconds)"
- **Scene gate:** "Ship scene <id>?"

A `no` returns to the same stage with the user's amendment; a `yes` writes the gate to
`approvals.json` and advances. Never coalesce two gates into one question.
