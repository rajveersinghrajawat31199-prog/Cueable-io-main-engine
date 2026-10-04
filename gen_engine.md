Integrate  video-generation engine (in ./engine) with this Next.js + Supabase app as an ADMIN-ONLY feature, so I can start generating videos from the admin panel. Work in phases. After each phase, stop, summarize what changed, and tell me exactly how to test it. Do not touch unrelated features (billing/Dodo, Settings including Interface language, Help Center). Never print or commit secrets from .env.local.

STEP 0 - UNDERSTAND (no code yet)
Read engine/README.md, engine/STUDIO.md, engine/CLAUDE.md, engine/scripts/video-studio.sh, engine/package.json, and list engine/.claude/skills. Then inspect my app: how admin access is checked (ADMIN_EMAILS env), existing /admin routes and UI components, Supabase client helpers (server + service role), storage buckets, migration naming (supabase/migrations/2026MMDDNNNN_name.sql), and the design system (DESIGN.md). Reply with a short summary of what the engine is, what you found in my app, and your plan. Wait for my "go".

WHAT THE ENGINE IS
It is NOT a library. It is a Claude Code project: skills in engine/.claude/skills driven by the `claude` CLI. Flow: studio-intake -> BRIEF.md (with `format:`) -> launch-video / ad-creative / motion-graphics -> critic -> render with `npx hyperframes render`. Projects live in videos/<project>/ (BRIEF.md, brand-brief.json, design-direction.md, assets/, compositions/, renders/). It needs Node, Python 3, ffmpeg, Chrome (for render), the `claude` CLI, ANTHROPIC_API_KEY, and optionally ELEVENLABS_API_KEY. Known issues: video-studio.sh hard-codes WORKSPACE=$HOME/hyperframe-studio, uses `grep -oP` (fails on macOS), and the SFX library (~/hyperframes-assets) is not available, so SFX/music must be optional. Do NOT edit files in engine/; wrap them.

ARCHITECTURE (must follow)
Vercel cannot run this, so: Admin UI -> API route -> `video_jobs` table in Supabase -> a separate long-running WORKER (Node script in ./worker, run locally on my Mac first, Docker/VPS later) that claims jobs, runs the engine, uploads the MP4 to Supabase Storage, and updates status. The web app never runs the engine itself.

PHASE 1 - DATABASE (new migration file, same naming style)
- video_jobs: id uuid, created_by, status (queued|running|needs_review|done|failed|cancelled), input_type (prompt|url), prompt, source_url, format (motion-graphics|launch-video|ad|explainer), duration_seconds, brand_kit jsonb, asset_paths jsonb, current_stage, progress int, output_url, error, token_usage jsonb, created_at, started_at, finished_at.
- video_job_events: id, job_id, ts, level, message.
- RLS on, admin-only (match how my existing admin tables/migrations enforce admin). The worker uses the service role key.
- Private storage bucket(s) for job inputs and outputs.
Stop and tell me to apply the migration.

PHASE 2 - ADMIN API (reuse my existing admin check on EVERY route)
- POST /api/admin/video-jobs (validate with zod, store uploaded assets, insert queued job)
- GET /api/admin/video-jobs (list) and GET /api/admin/video-jobs/[id] (status, events, signed output URL)
- POST .../[id]/cancel and .../[id]/retry
Test: creating a job from a request shows it as `queued`; a non-admin gets 403.

PHASE 3 - WORKER (./worker, TypeScript or Node, own package.json, runnable with `npm run worker`)
- Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY, ELEVENLABS_API_KEY (optional), ENGINE_DIR=./engine, JOBS_DIR=./.jobs, MAX_CONCURRENCY=1, ENABLE_SFX=false.
- Loop: poll every few seconds, atomically claim one queued job (UPDATE ... WHERE status='queued' RETURNING). Then:
  1. Create a per-job workspace by copying engine into JOBS_DIR/<job_id> (or point the engine's WORKSPACE env at it) and init videos/<job_id> with `npx hyperframes init ... --non-interactive --example=blank --skill=<workflow>` where workflow comes from the job format.
  2. Write BRIEF.md (with `format:` and `workflow:` set, so studio-intake's questions are already answered), brand-brief.json and design-direction.md from the job input and brand kit, following the engine's sample files. Download the job's assets into assets/.
  3. Run `claude -p "<stage prompt>" --output-format stream-json --verbose --max-turns <N>` in the project dir with a minimal env. Check `claude --help` for the right permission flags in my installed version; skip-permission mode only inside the isolated job dir. Parse the stream into video_job_events, update current_stage/progress/token_usage.
  4. Run lint/check, then render with `npx hyperframes render`, verify the MP4 with ffprobe, upload to Storage, save output_url, set status done. On any failure set failed with the error plus last log lines.
- Add per-job timeout, cancel support, and old-job-folder cleanup.
- Do NOT use `engine/scripts/video-studio.sh build` as is (macOS grep -oP bug and hard-coded paths); write the equivalent steps in the worker, or a thin wrapper.
- Add a `worker:preflight` script that checks node, python3, ffmpeg, claude, chrome, and the API key, and prints what is missing.
Test: run the worker locally, create a 10-second motion-graphics job, watch it reach `done`.

PHASE 4 - ADMIN UI
- New admin-only page /admin/video-engine in my existing admin layout and design system: form (prompt or URL, asset upload, brand colors/logo, format, duration), jobs table with status badges, job detail page with live-updating logs (polling is fine), stage progress, video player, Cancel/Retry. Include loading, empty and error states.

PHASE 5 - DEPLOY PREP
- .env.example additions, worker Dockerfile (Node, Python, ffmpeg, Chromium deps, claude CLI), README section for running the worker on a VPS. Vercel only hosts the web app.

RULES: minimal, typed, secure changes; reuse existing helpers and components; no secrets in code or logs; list every file you create or modify at the end of each phase.