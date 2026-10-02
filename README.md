# Video Studio engine

The studio's production engine: Claude Code skills, scripts, templates and rules that turn a brief into a finished,
critic-checked [HyperFrames](https://hyperframes.heygen.com) video. Read [STUDIO.md](STUDIO.md) first (how a request becomes
a video), then [CLAUDE.md](CLAUDE.md) (the rules agents follow in this repo).

## What is in this repo

| Path | What it is |
|---|---|
| `.claude/skills/` | **The engine.** `studio-intake` (router), `launch-video`, `ui-morph-loop`, `quality-gate`, `ad-creative`, `performance-core`, `brand-brief-video` + its stages, `motion-doctrine` / `seam-craft` / `cut-the-curve`, `pollo-generate`, `video-critique`, ... |
| `.claude/agents/` | `linkedin-performance-marketer` |
| `scripts/video-studio.sh` | Stage runner: `init`, `build`, `verify`, `preview`, `render`, `status` |
| `templates/`, `brand-kits/` | Starter templates and brand briefs |
| `package.json`, `hyperframes.json`, `skills-lock.json` | CLI pin, project config, pinned third-party skill |

## What is deliberately NOT in this repo

- **The `videos/` folder.** Git-ignored entirely: ~6 GB of renders, media and site captures, and GitHub rejects files over 100 MB.
  Create it locally; nothing inside it ever reaches GitHub. `STUDIO.md` still mentions past projects there
  (`ui-morph-demo`, `shopos-mora-benchmark`); those exist only on the author's machine.
- **Third-party libraries.** `node_modules/`, `vendor/` and `*.min.js` are ignored. The UI-morph template loads GSAP from
  `assets/vendor/gsap.min.js`: download 3.15.0 from `https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js` into
  `.claude/skills/ui-morph-loop/template/assets/vendor/`. The (empty) `scene-library/` folder is also local-only.
- **Secrets.** Scripts read `ELEVENLABS_API_KEY` from the environment. On the author's machine it is loaded from
  `~/.config/hyperframes/secrets.env`. Never commit keys.
- **Audio and video files** (`*.mp4`, `*.wav`, `*.mp3`, ...) are ignored everywhere.

## Outside the repo, but the engine needs it

| Dependency | Where it lives today | Used by |
|---|---|---|
| `video-critique` skill (the studio's own critic) | A copy is in `.claude/skills/video-critique/`, but the scripts call it at `~/.claude/skills/video-critique/`. Install with `cp -R .claude/skills/video-critique ~/.claude/skills/` | `launch-video/scripts/build_all.sh`, `quality-gate/scripts/machine_scores.py`. Needs `numpy` and `ffmpeg`. |
| `product-launch-video` skill (stock HyperFrames) | `~/.claude/skills/product-launch-video/` | `build_all.sh` calls its `audio.mjs` and `assemble-index.mjs`. Install with `npx hyperframes skills update product-launch-video`. |
| Sound-effects library (~28 GB) | `~/hyperframes-assets/sfx` | `gen_sfx.py`, `sfx_from_film.py`, `sfx_palette.json`. Share it separately and check each pack's licence. |
| ElevenLabs key | `ELEVENLABS_API_KEY` env var | `launch-video/scripts/gen_vo.py` |
| `claude` CLI, `pollo` CLI | `~/.local/bin/` | `video-studio.sh build` runs `claude -p`; `pollo-generate` drives a Pollo AI account |

Built and run with: Node 26.8.1 / npm 11.19.0, Python 3.9.6 (numpy 2.0.2, used by the critic), ffmpeg 6.0, on macOS. The `hyperframes` CLI itself comes from `npx`.

## Settle these during integration

1. **Which `hyperframes` version.** Root `package.json` pins `0.8.34`; the newest project (superleap-launch, not in this repo) was built on `0.8.109`. Pick one and pin it everywhere.
2. **Hard-coded paths.** `scripts/video-studio.sh` sets `WORKSPACE="$HOME/hyperframe-studio"`, and the scripts above expect `~/hyperframes-assets` and `~/.claude/skills/...`. These need to become configurable (or provisioned) on a server.
3. **How the engine runs.** Stages are skills driven by Claude Code (`/studio-intake` -> `/launch-video` -> ...). After a storyboard and `launch.config.json` exist, `.claude/skills/launch-video/scripts/build_all.sh <project> --render high` rebuilds deterministically. The backend has to orchestrate those runs.

## Keeping it in sync

Engine owner: commit and `git push` whenever the engine changes (work in progress is fine). Backend: `git pull` to get updates.
Keep backend code in its own folder (for example `backend/`) so engine changes and backend changes never touch the same files.
When the engine is in a state the backend should build against, tag it: `git tag v0.1.0 && git push --tags`.
