# HyperFrames Composition Project

## Where things live (read this instead of exploring)

- **Work only inside this folder.** Every video is `videos/<project>/`. Start new ones there. Do not search the home directory.
- **Never open or scan** `~/hyperframes` (engine source clone, 2 GB with node_modules) or `~/hyperframes-assets` (28 GB sound library). The engine is the pinned npm package: use `npx hyperframes ...` from inside a project.
- **Sound effects:** search, never list folders: `python3 ~/hyperframes-assets/sfx/_index/search.py <terms> --limit 10`. Full usage, licences and ElevenLabs steps: `~/hyperframes-assets/PROMPT-for-new-projects.md`. Copy only the files a project uses into that project's `assets/`.
- **Pipeline skills** (`brand-brief-video` and its stages) are in `.claude/skills/` here. Reusable finished scenes go in `scene-library/`, brand configs in `brand-kits/`, starter templates in `templates/`.
- **Old projects** live in `~/hyperframes-projects/`. Ignore unless the user names one.
- Per-video `CLAUDE.md` / `AGENTS.md` are duplicates of this file. Do not re-read them.

## New video request → `/studio-intake` FIRST (studio router)

For any **fresh** "make a video / launch video / demo / ad" request, start at **`/studio-intake`** (`.claude/skills/studio-intake`). It classifies the *outcome* the user wants (not the input type), asks only what is missing, writes `BRIEF.md` with `format:` locked, then hands off:

- **launch video / product-in-use film** → **`/launch-video`** (`.claude/skills/launch-video`): rebuilt-UI launch playbook, one-take VO, config-driven SFX + measured music, critic-gated. Proven on the ShopOS benchmark. Scripts: `.claude/skills/launch-video/scripts/` (`build_all.sh <project> --render high`).
- other formats → the stock skills listed below (intake's table says which, and which formats have no playbook yet).
- **Editing an existing project** (BRIEF.md / hyperframes.json present) → skip intake; just do the edit.

- **a reference video to recreate in the user's brand** ("make it like this", use case 3) → **`/reference-recreation`**: run its analyzer first (`reference-style.json` in seconds); never hand-measure a reference again.

Studio rules for every video: **every job opens with `job_receipt.py start` and its final message carries `job_receipt.py report` (time, tokens, dollars from the pricing sheet, credits: `/job-receipt`)**; designed fresh for the brand (a previous video is a process reference, never a style source); the critic (`/video-critique`) runs before the user sees any cut and the final message says audio/taste are unverified by ear; **never edit an upstream skill during a video** (`HYPERFRAMES_SKIP_SKILLS=1`); engine improvements go in `.claude/skills/` here and are proposed at the end of a video.

## Skills — USE THESE FIRST

**Always invoke the relevant skill before writing or modifying compositions.** Skills encode framework-specific patterns (e.g., `window.__timelines` registration, `data-*` attribute semantics, shader-compatible CSS rules) that are NOT in generic web docs. Skipping them produces broken compositions.

**Doing anything with HyperFrames?** Start at `/hyperframes` — it tells you what HyperFrames can do and which skill or workflow handles your intent (make a video, TTS / BGM, prep footage, author / animate, render, install blocks), confirms your brief up front (the intent layer), and routes every "make me a…" request (a video, a deck, a composition port) to the right workflow. Read it first, especially when there's no project context to orient you. The workflows it routes to:

- `/product-launch-video` — any **website** URL or brief / script → a product launch / SaaS / promo video, or a site tour / showcase featuring the site's own captured visuals.
- `/faceless-explainer` — arbitrary text (topic / article / notes), **no URL, no website capture** → 60-90s faceless explainer.
- `/embedded-captions` — an existing talking-head video (MP4) → the same footage with captions / subtitles added (rail + embed, or pure-cinematic embed); the footage itself is untouched.
- `/talking-head-recut` — an existing talking-head / interview / podcast video (MP4) → the same footage **packaged with designed graphic overlays** (kinetic titles, lower-thirds, data callouts, pull-quotes, side panels, pip) synced to the transcript; the clip plays unchanged underneath. (Plain captions/subtitles → `/embedded-captions`.)
- `/pr-to-video` — a GitHub PR (URL / `owner/repo#N` / "this PR") → 30-90s code-change explainer (changelog / feature reveal / fix / refactor).
- `/motion-graphics` — a short (typically under 10s) design-led **motion graphic**, motion-is-the-message, no narration: kinetic type, a stat / number count-up, a chart, a logo sting, a lower-third / overlay, or an animated tweet / headline / captured-page highlight; rendered to MP4 or a transparent overlay. Longer / narrated / custom → `/general-video`.
- `/music-to-video` — a **music track** (audio file, video to pull audio from, or one generated from a mood brief) → beat-synced video (lyric / slideshow / kinetic promo). Music drives pacing; user-supplied images / videos are cut onto the same beat grid.
- `/slideshow` — a **presentation / pitch deck / interactive deck** — discrete slides, fragment reveals, branching, hotspot navigation, presenter mode. Output is a navigable deck, not a rendered video.
- `/general-video` — fallback for any other video (title card, longer brand / sizzle reel, multi-scene montage, static loop, custom composition) and the home of **companion mode** — co-create with the full HyperFrames toolbox; the original hyperframes authoring flow, any length.

**Porting an existing composition?** `/remotion-to-hyperframes` translates a Remotion (React) composition into HyperFrames HTML — a source migration, separate from the creation workflows above.

The domain skills (`/hyperframes-core`, `/hyperframes-animation`, `/hyperframes-keyframes`, `/hyperframes-creative`, `/hyperframes-cli`, `/media-use`, `/hyperframes-audio`, `/hyperframes-registry`, `/figma`) and the full capability map live inside `/hyperframes` — it is the single source of truth for which skill handles which intent.

**Changing how real footage or images look or reveal?** Load `/media-use` and read its `references/media-treatments.md` before editing, even when the request only says dark, flat, boring, retro, private, or “make the reveal cooler.” It governs how footage is treated, never whether media may be used. Use canonical media treatments and seek-safe motion; do not improvise equivalent CSS/SVG filters or overlays.

**Need a generated scene image or short video clip** (creative-direction mood frames, storyboard reference images, background plates, b-roll)? Use `/pollo-generate` (`.claude/skills/pollo-generate`, driving the user's own Pollo AI account/credits via the `pollo` CLI) — it is the default generator for this studio. Higgsfield stays available but only for its own dedicated workflows (avatars, ads/Marketing Studio, virality prediction) or when the user names it explicitly.

> **Tailwind v4 projects** (`hyperframes init --tailwind`): see `/hyperframes-core` → `references/tailwind.md`.

> **Skill missing or stale?** Run `npx hyperframes skills update <name>` to install/refresh
> the specific skill you need (the `/hyperframes` router does this automatically before
> entering a workflow), or bare `npx hyperframes skills update` to refresh the core set plus
> everything already installed — neither pulls the full set. Restart the agent session so
> newly installed skills load.

## Commands

```bash
npm run dev          # human-operated foreground preview (blocks until stopped)
npx hyperframes preview --background  # agent-safe persistent Studio preview
npx hyperframes preview --status      # verify the persistent preview is listening
npx hyperframes preview --stop        # stop it when review is finished
npm run check        # lint + runtime + layout + motion + contrast (one command)
npm run render       # render to MP4
npm run publish      # publish and get a shareable link
npx hyperframes lint --verbose  # include info-level findings
npx hyperframes lint --json     # machine-readable output for CI
npx hyperframes docs <topic> # reference docs in terminal
```

> **Agents must use `npx hyperframes preview --background` for Studio handoff.** Do not rely
> on a shell/tool `run_in_background` wrapper around `npm run dev`: that foreground process
> remains owned by the invoking session and can disappear while the browser stays open,
> leaving refreshes at `ERR_CONNECTION_TIMED_OUT`. Verify with `preview --status`, keep it
> alive through review, and stop it explicitly with `preview --stop` afterward.

> **Pinned CLI version.** These scripts pin an exact `hyperframes@X.Y.Z` so this project re-renders identically over time. Weeks later that pin lags fixes shipped since. To move up: `npx hyperframes@latest upgrade --project . --check` (shows the delta), then `npx hyperframes@latest upgrade --project .` to rewrite the pins. Always unpinned — the pinned script re-runs the old version against itself.

## Documentation

**For quick reference**, use the local CLI docs command (no network required):

```bash
npx hyperframes docs <topic>
```

Topics: `data-attributes`, `gsap`, `compositions`, `rendering`, `examples`, `troubleshooting`

**For full documentation**, discover pages via the machine-readable index — do NOT guess URLs:

```
https://hyperframes.heygen.com/llms.txt
```

## Project Structure

- `index.html` — main composition (root timeline)
- `compositions/` — sub-compositions referenced via `data-composition-src`
- `meta.json` — project metadata (id, name)
- `transcript.json` — whisper word-level transcript (if generated)

## Linting — ALWAYS RUN AFTER CHANGES

After creating or editing any `.html` composition, **always** run the full check before considering the task complete:

```bash
npm run check
```

Fix all errors before presenting the result. Warnings should be reviewed before rendering.

## Key Rules

1. Every timed element needs `data-start` and a duration. `data-start` is what marks it as timed; `data-track-index` is an optional Studio display lane the render never reads
2. Give timed visual elements `class="clip"`. The framework keys visibility off `data-start`, not the class, but the shared `.clip` CSS is what gives a scene its full-frame box, and `lint` warns without it
3. Register one paused root timeline per composition on `window.__timelines`:
   ```js
   window.__timelines = window.__timelines || {};
   window.__timelines["composition-id"] = gsap.timeline({ paused: true });
   ```
   Scene timelines manually added to this root must not be paused. A paused
   child does not advance when the root is seeked. The runtime activates
   registered composition siblings, not arbitrary nested scene timelines.
4. Videos use `muted` with a separate `<audio>` element for the audio track
5. Sub-compositions use `data-composition-src="compositions/file.html"` to reference other HTML files
6. Only deterministic logic — no `Date.now()`, no `Math.random()`, no network fetches
