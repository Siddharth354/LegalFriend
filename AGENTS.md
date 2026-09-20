# AGENTS.md — Nyaya-Dost / LegalFriend

> **Read [`hackathon-build-plan-log.md`](hackathon-build-plan-log.md) FIRST, before this file.** It's the live, dated build log — what's downloaded, what's scaffolded, what's decided-but-not-yet-built. This file is the stable rulebook (folder structure, stack, code style); the log is where "where are we right now" lives.
>
> Canonical operational reference for any coding agent (Claude Code, Codex, Cursor) working on this codebase. `CLAUDE.md` at repo root is a thin pointer to this file — this is the source of truth, self-contained, no dependency on the planning repo this was drafted in.
>
> This repo has now been scaffolded — this file is live, not a draft copied from the planning repo. The planning repo (`elite-engineer-guide/hackathons/sarvam/epoch-ai-builder-growthx-hackathon/`) still holds the *why* behind each decision (`pitch.md`, `server.md`, `client.md`, `deployment.md`) — come back here only for the *what*.

---

## Project Overview

**Nyaya-Dost** — a voice-first legal first-responder. A user photographs a predatory-loan threat notice, asks a question out loud in their own language, and gets a spoken, citation-grounded answer on whether the threat is legal, within seconds. One repo, two independently-buildable trees: `frontend/` (Next.js PWA) and `backend/` (FastAPI, modular monolith).

Full design rationale lives in the planning repo — `pitch.md`, `build-plan.md`, `client.md`, `server.md`, `deployment.md`, `LOG.md`. This file states the rules that govern the actual code; it doesn't re-argue the decisions behind them.

---

## Folder Structure

### `backend/` — modular monolith, vertical slices

```
backend/src/
├── core/                              # global infra, NO domain logic
│   ├── config.py                      # Pydantic Settings
│   ├── logger.py                      # structlog, colorized in dev — see Logging below
│   ├── api_errors.py                  # typed error envelope
│   ├── security.py                    # CORS — must allow the frontend's origin
│   ├── sarvam/                        # 3-tier client cascade (folder, not one file)
│   │   ├── client.py                  # tries tier 1→2→3, tenacity-wrapped
│   │   ├── sdk_tier.py                # sarvamai SDK — primary
│   │   ├── mcp_tier.py                # sarvam-mcp — secondary
│   │   └── rest_tier.py               # raw httpx — last resort
│   └── memory.py                      # SQLite — session/turn/fact persistence, survives a crash restart
│   # No cache.py — no shared cache service (single process, in-process lru_cache covers it).
│   # memory.py is a deliberate exception to "no database" — added for crash-survival
│   # conversation memory, decided 2026-07-26, see hackathon-build-plan-log.md. Everything
│   # else (no Redis, no LiteLLM, no WebSocket) is unchanged.
├── modules/
│   └── legal_notice/                  # the one business domain
│       ├── models.py
│       ├── public_api.py              # the ONLY legal cross-module entry point
│       ├── blueprint/
│       │   ├── ports.py
│       │   └── use_cases.py
│       ├── features/
│       │   ├── health.py              # simple: /healthz
│       │   └── analyze/               # complex: the 6-stage pipeline
│       │       ├── router.py          # POST /api/v1/analyze/{voice,text} — thin
│       │       ├── schemas.py
│       │       └── logic.py           # THE PIPELINE: OCR→ASR→extract→retrieve→reason→translate→TTS
│       └── implementations/
│           ├── retrieval_adapter.py   # qdrant-client embedded + keyword-tag match
│           └── use_case_skeleton.py
├── main.py                            # FastAPI app + lifespan
└── runtime_api.py                     # /healthz, /readyz
```

### `frontend/` — feature-based

```
frontend/src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                       # the ONLY route — six screens are useState transitions
│   └── globals.css                    # design tokens: --paper --ink --hair --danger
│   # No app/api/, no features/*/actions/ — Next.js is pure client;
│   # the browser calls the FastAPI backend directly, no BFF layer.
├── features/
│   └── legal-notice-flow/
│       ├── components/                # ArriveScreen, ListenScreen, ShowScreen, ThinkScreen, KnowScreen, ChooseScreen
│       ├── hooks/
│       │   ├── useRecorder.ts         # MediaRecorder wrapper — browser API only
│       │   └── useAnalyzePipeline.ts  # screen-flow state machine — calls shared/lib/api-client.ts, doesn't own the fetch
│       ├── schemas/
│       │   └── analyze.schema.ts      # zod, mirrors backend's schemas.py
│       ├── types.ts
│       └── index.ts                   # barrel
├── shared/
│   ├── ui/
│   │   ├── Orb.tsx                    # Canvas 2D, no library
│   │   ├── ThemeToggle.tsx
│   │   └── icons/                     # hand-drawn inline SVGs
│   ├── hooks/
│   ├── utils/
│   ├── types/
│   └── lib/
│       └── api-client.ts              # the ONE fetch() wrapper — the actual network call lives here
└── config/
    └── site.ts
```

---

## Stack — locked versions

See `server.md`, `client.md`, `deployment.md` in the planning repo for full pinned-version tables and the reasoning behind every inclusion/exclusion. Headline pins, current as of 2026-07-25:

**Backend**: Python 3.12+, FastAPI 0.140.0, uvicorn[standard] 0.51+, uv 0.11+, ruff 0.16+, ty 0.0.63, tenacity 9.1+, structlog 25.5+, orjson 3.11+, `sarvamai` SDK (latest), `qdrant-client` (embedded mode, latest).

**Frontend**: Node 24+ LTS, Bun 1.3.14, Next.js 16 (App Router), TypeScript 7.0.2, Biome 2.5.5, Tailwind 4.3.3 (layout utilities only), React 19.2.8.

**Deliberately not used** (see `server.md`/`client.md` for the reason each time): PyMongo/Motor, redis.asyncio, LiteLLM, ARQ, OpenTelemetry, shadcn/ui, lucide-react, Motion/Framer Motion, zustand, TanStack Query, Auth.js, WebSocket (anywhere, either side).

---

## Code Quality & Style

- **Zero comments by default.** Add one only when the WHY is non-obvious — a hidden constraint, a workaround for a specific bug, a subtle invariant. Never restate WHAT the code does; type names and function names already say that.
- **Type annotations on every variable**, not just function signatures — types ARE the documentation.
- **No docstrings** unless the signature genuinely cannot convey behavior. Never multi-paragraph.
- **Simple, not easy.** Prefer explicit control flow over clever abstraction — this is a single `async` function chain (see `logic.py` above), not a framework. Don't introduce one to look more sophisticated.
- **Self-explanatory naming carries the weight** comments would otherwise carry. `sdk_tier.py::call_ocr()` beats `client.py::call(tier=1, capability="ocr")`.

---

## Design Principles

- **Module isolation**: cross-module communication only through `public_api.py`. Never import another module's `models.py`, `implementations/`, or `blueprint/` directly. (Moot at one-module scope today — stated now so it's not violated the day a second module is added.)
- **Simple vs. complex feature rule**: no I/O, no business logic → one file (`features/health.py`). Touches DB/LLM/external API/business rules → a folder (`features/analyze/{router,schemas,logic}.py`). No exceptions.
- **Dependency injection via lifespan**: infra clients are created once in `main.py`'s lifespan, exposed to features via typed `Depends()` aliases. Never construct a client per request.
- **Pure ASGI middleware only** — never `BaseHTTPMiddleware` (documented overhead: wraps every request in a new task + `StreamingResponse`).
- **The pipeline is linear control flow, not an agent framework.** `logic.py` is one `async def analyze(...)` awaiting each Sarvam-tier call in order. No LangGraph, no CrewAI, no Sarvam Arya — see `server.md`'s "Agent orchestration — deliberately not a framework" for the full reasoning and the one condition under which that would change.

---

## Logging — first-class, colorized, terminal-visible

The terminal running the backend is the operator console during the live demo — it must be legible at a glance, not just structured-for-a-log-aggregator-nobody-has.

- **structlog**, configured with two renderer modes, selected by environment:
  - **Dev** (`ENV=dev`, the only mode that matters for the hackathon): `structlog.dev.ConsoleRenderer(colors=True)` — colored log levels (red ERROR, yellow WARNING, cyan INFO), colored keys, human-readable timestamps. This is what runs on stage.
  - **Prod** (deferred, see `deployment.md`): JSON renderer via `orjson`, for when there's an actual log aggregator to send to.
- **Every Sarvam tier transition logs explicitly** — which tier was tried, whether it succeeded, and if it fell through, why. This is the single most useful thing on the terminal during a live demo: watching `tier=sdk status=failed → tier=mcp status=ok` scroll by IS the resilience cascade proving itself in real time, visible to you without instrumenting anything extra.
- **Every retry attempt logs** (tenacity's own `before_sleep` hook, wired to structlog, not silently swallowed).
- **`DEMO_MODE` activation logs loudly** — if the cached-response fallback ever fires live, you need to see it happen, not discover it after the fact from a suspiciously-identical response.
- **`request_id` on every log line** for one request's full pipeline trace — grep one ID, see the whole 6-stage journey for that turn.

---

## Error Handling

- Typed error envelope (`core/api_errors.py`) for every non-2xx response — never a raw FastAPI default 500 with a stack trace leaking to the client.
- **The one failure path that must be designed, not improvised**: what the user sees if all 3 Sarvam tiers *and* `DEMO_MODE` fail. This should be one honest, calm message in the user's language ("कुछ गड़बड़ हो गई, दोबारा कोशिश करें" / "Something went wrong, please try again") — not a generic error screen, since the whole product's premise is calm authority under a scared user's panic.

---

## Secrets & Security

Day-1 checklist, per this repo's own architecture template (`architecture/01_scaffolding.md` §"AI Coding Agent Setup"):

1. `SARVAM_API_KEY` only via Pydantic Settings, loaded from `.env` — never `os.getenv()`, never hardcoded.
2. `.env.test` committed with a dummy key value, real key in `.env` (gitignored).
3. `.gitignore` covers `.env`, `.env.local`, `*.pem`, `*.key`, `secrets/`.
4. Pre-commit gitleaks hook — catches a key pasted into a config file by accident before it reaches history.
5. `.claude/settings.json` (project-level, committed) allowlists the safe dev commands (`uv run *`, `pytest *`, `ruff *`, `docker compose up/down/build/logs`, `git status/diff/log/add/commit`) and denies destructive ones (`docker compose rm`, `docker volume rm`).

---

## Testing

Minimal, scoped to the hackathon window — see `server.md`'s "Testing" section. `ruff check` + `ty check` + a handful of smoke assertions: one per Sarvam-tier wrapper, confirming the cascade actually falls through when a tier is forced to fail. No coverage gates, no full suite — there's no time budget for it and no team to protect from regressions yet.

---

## Commit Discipline

- **WHAT / WHY / HOW** body for every non-mechanical commit. One-line subject only for pure mechanical changes (typo, rename).
- **Atomic and concise.** One logical change per commit — a single file touched by two unrelated concerns gets two commits, not one bundled one.
- Never `git add -A` / `git add .` — stage explicitly by path.
- Never `git push --force` or `git reset --hard` without explicit request.
- Never push without being asked — local commits, reviewed, pushed manually.

---

## Deployment Strategy

**The local machine is the server for the demo.** Full reasoning in `deployment.md` — restated here as the operative rule:

- Backend: `uv run uvicorn src.main:app --host 0.0.0.0 --port 8000`
- Frontend: `bun run build && bun start` (production build for demo speed, not `bun dev`)
- Phone connects to the laptop's LAN IP over the same WiFi hotspot — no cloud, no deploy pipeline, no Docker for the demo itself.
- If a public URL is required: Cloudflare Tunnel, one command, not ngrok (free-tier URL churn is one more thing to re-share mid-event).
- Docker, CI/CD, and a real hosting target are a deferred post-hackathon roadmap — don't build them before the localhost demo has worked live once. See `deployment.md`'s pinned-version table for when that day comes.

---

## Things easy to miss

- **CORS is not optional here** — set `CORS_EXTRA_ORIGINS` in `backend/.env` (JSON array) for the LAN-phone demo IP, or every request silently fails in the browser console, not the terminal. Full contract: `docs/api-contract.md`.
- **iOS Safari's microphone/autoplay permission model is stricter than Android Chrome** — test the actual demo phone's browser specifically, not just "a phone." A permission prompt appearing mid-demo, un-rehearsed, is a real failure mode.
- **`DEMO_MODE`'s cache needs to be populated before it can save you** — it only works if the locked-in demo document has been run through the real pipeline at least once during the validation window. An empty cache is not a fallback.
- **Timestamps in logs should be local time (IST), not UTC** — you're debugging live, at a specific wall-clock moment, not correlating against a server fleet in another timezone.
- **Clean up scratch/test audio and image files before the demo** — they'll otherwise show up in a file picker or directory listing if anyone glances at the laptop screen during setup.
- **The venue WiFi client-isolation check** (already flagged in `deployment.md`) — test phone-to-laptop LAN connectivity the night before, not in the room.
