---
name: pollo-generate
description: "Generate scene images and short video clips via the Pollo AI CLI (the user's own Pollo Pro account/credits). Use this for any HyperFrames scene that needs a generated (non-captured, non-mockup) image or short video clip — creative-direction mood frames, storyboard reference images, background plates, b-roll inserts. Preferred over Higgsfield for scene image/video generation in this studio; Higgsfield stays available for its own dedicated workflows (avatars, ads, marketing studio) but should not be the default image source here."
---

# pollo-generate

Thin wrapper around the official `pollo` CLI (`npm i -g @pollo-ai/cli`), authenticated
to the user's own Pollo account. Use it whenever a HyperFrames project needs a
**generated** image or short video clip (not a captured screenshot, not a
brand asset, not a UI mockup) — e.g. creative-direction mood images, storyboard
reference frames, background plates, atmospheric b-roll.

Do not use this for footage capture, UI mockups, brand logos, or audio — those
stay in `/media-use`. Do not reach for Higgsfield for this purpose: this
studio's Pollo account is the default for scene image/video generation;
Higgsfield remains available only when the user names it explicitly or the
task is one of its dedicated workflows (avatars, Marketing Studio ads, virality
prediction).

## Setup (once per machine)

```bash
pollo account status   # confirms login + shows availableCredits
```

If it reports not logged in: `pollo auth login` (opens a browser — stop and
wait for the user to finish signing in). Never print or store the auth token.

## Workflow

1. **Pick a model** — don't guess brand/alias names, they change:
   ```bash
   pollo model list --type text2image     # or text2video / image2video / ref2video
   pollo model get <brand>/<alias> --fields   # confirm input fields before building the call
   ```
2. **Check cost before an expensive run**, especially if credits are limited:
   ```bash
   pollo generate cost <brand>/<alias> --prompt "..." --aspectRatio 16:9
   ```
3. **Submit and poll**:
   ```bash
   pollo generate create <brand>/<alias> --prompt "..." --aspectRatio 16:9 --json
   # -> { "taskId": "...", "status": "waiting" }
   pollo generate wait <taskId> --json
   # -> { "generations": [{ "status": "succeed", "url", "mediaType" }] }
   ```
   Image/video input fields (`image`, `images`, `refs`) take either a local
   file path (auto-uploaded) or an HTTPS URL.
4. **Download and freeze** the result into the project's `assets/` folder
   (same convention as `/media-use` — copy only what the project uses, don't
   leave it pointing at a remote URL).

## Credits

`pollo account status` → `availableCredits`. If a generation would exceed
available credits, or `generate create` fails with `insufficient credits`,
treat it as terminal: tell the user the shortfall and point to
`<host>/pricing` (from `pollo profile current`). Don't retry or silently
switch models.

## Reference

Full CLI surface: `pollo --help` / `pollo <command> --help`. Prompt phrasing
differs per underlying model vendor (Kling, Veo, Seedance, Sora, Vidu, Wan,
Pixverse, etc.) — check `model get --fields` for what the model actually
accepts rather than reusing a prompt style across vendors.
