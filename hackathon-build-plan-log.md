# Hackathon Build Plan Log — read this FIRST in any new session

> Append-only, newest entry at the bottom, same convention as the planning repo's `LOG.md`
> (`elite-engineer-guide/hackathons/sarvam/epoch-ai-builder-growthx-hackathon/LOG.md`).
> If you are a fresh agent picking this up mid-event: read this file top to bottom, then
> `AGENTS.md` for the operational rules, before writing any code.

---

## 2026-07-26 — Live build started, backend scaffolding in progress

**What this project is**: Nyaya-Dost / LegalFriend — voice-first legal-aid app, full product
rationale in `elite-engineer-guide/hackathons/sarvam/epoch-ai-builder-growthx-hackathon/pitch.md`.
This repo (`~/Workspace/LegalFriend`) is the REAL on-site build — not the `sarvam-hack`
rehearsal repo from last night, which cannot be reused per the Builder Handbook's rules.
`AGENTS.md`/`CLAUDE.md` here are the copied-and-now-canonical operational reference.

**Done so far:**

1. **Acts downloaded, verified, sourced** — `legal-corpus/raw/` (both here and mirrored in
   the planning repo's `research/legal-corpus/raw/`):
   - `bns_2023.pdf` — BNS 2023, India Code, 112 pages.
   - `rbi_digital_lending_directions_2025.pdf` — RBI/2025-26/36, Axis Bank mirror (RBI's own
     `rbidocs.rbi.org.in` blocks `curl` with a bot-detection JS challenge), 24 pages.
   - `negotiable_instruments_act_1881.pdf` — India Code, 32 pages, §138 confirmed present.
   - `SOURCES.md` in the same folder — exact URLs + how each was verified. **One bad fetch
     was caught and discarded**: a `.gov.in`-hosted PDF that claimed to be the NI Act was
     actually an unrelated university course-note PDF — always verify text content, not
     just that the URL looks official.
   - **Not yet downloaded**: DPDP Act 2023, IT Act 2000, Karnataka interest-cap act (stretch
     goals, see `server.md`'s prioritized act list — MVP is the 3 acts above only).

2. **Backend scaffolded** — `backend/`, `uv init`, Python 3.12, FastAPI stack installed.
   Folder structure follows `AGENTS.md`'s modular-monolith layout exactly.
   **One correction to `server.md`'s locked-versions table**: it claimed `structlog 26.1.0`
   "doesn't exist" (a stale note from an earlier freshness sweep) — it installed cleanly
   today and is genuinely real. Use `structlog==26.1.0`, not the 25.5+ floor previously
   noted.

3. **In progress** (this session, check `git log` in `backend/` for exact state):
   `core/config.py`, `core/logger.py`, `core/api_errors.py`, `core/security.py` written.
   Sarvam 3-tier cascade, SQLite memory module, Qdrant retrieval adapter, and the
   structural chunkers for RBI (Para-based) and NI Act (single-section) are the immediate
   next steps — check `backend/src/` directly for what actually landed vs. what's still a
   plan.

**Memory design (crash-survival)** — decided, not yet built: SQLite file
(`backend/legalfriend.db`), tables `sessions`, `turns`, `facts`, keyed by a `session_id` the
client persists in `localStorage` and sends as `X-Session-Id`. This supersedes the
"no database" line in the original `server.md`/`AGENTS.md` for this one piece only —
everything else in those files (no Redis, no LiteLLM, no WebSocket, linear pipeline not a
framework) still holds.

**Retrieval design** — decided, validated last night against BNS only: Qdrant on-disk mode,
hybrid dense (`zembed-1`, local) + sparse (BM25 via `fastembed`) fused with native RRF,
top-5, no reranker (confirmed twice to OOM on this machine and architecturally unneeded —
full writeup in the planning repo's `server.md`).

**When resuming**: read this file, then `AGENTS.md` (folder structure, stack, code style),
then `backend/src/` directly to see what's actually implemented vs. still planned. Do not
re-read the planning repo's `server.md`/`build-plan.md` for the stack decisions — they're
already condensed into `AGENTS.md` here; only go back to the planning repo for the *why*
behind a decision, not the *what*.

---

## 2026-07-26 11:20 IST — Backend MVP done and verified live, real key confirmed

**Backend is ready.** Everything below actually ran, not just written:

- Full pipeline module tree exists: `core/{config,logger,api_errors,security,memory}.py`,
  `core/sarvam/{client,sdk_tier,mcp_tier,rest_tier}.py`, `modules/legal_notice/features/
  analyze/{router,schemas,logic}.py`, `implementations/retrieval_adapter.py`,
  `ingestion/{chunk_bns,chunk_rbi_directions,chunk_ni_act,pdf_text}.py`. `ruff check` +
  `ty check` both clean.
- Corpus: 80 chunks across 3 acts (BNS 43, RBI Digital Lending 34, NI Act 3) — verified by
  a live Qdrant hybrid (dense+sparse+RRF) query, correct citations surfaced.
- App boots end-to-end via a real lifespan test — Qdrant index builds, structlog renders
  colorized, cascade logging fires.
- **Real `SARVAM_API_KEY` confirmed live** — `identify_language` call authenticated
  successfully. Only tier 1 (`sarvamai` SDK) is wired; tiers 2/3 are stubbed, not
  fallback-tested, and not planned to be built out (see reasoning below).
- CORS fixed for real: `CORS_EXTRA_ORIGINS` env var wired end-to-end for the LAN-phone
  demo, not just documented.
- `docs/api-contract.md` written from the actual running schemas — this is the frontend
  agent's single source of truth, update it first on any request/response shape change.
- `HOW_TO_USE.md` at repo root — exact curl commands, a free retrieval-only test path,
  and 5 sample Hindi/Hinglish queries mapped to the exact chunk each should retrieve.
- Root `Makefile`: `make api` (backend only), `make web` (backend + frontend once it
  exists), `make ingest` (re-run all 3 chunkers), `make test`/`make lint`.
- Two real SDK corrections found by introspection, not docs — logged in the planning
  repo's `server.md`: `structlog==26.1.0` is real; Saaras STT needs **two** calls
  (`transcribe(mode="verbatim")` + `translate()`), not one, doubling STT cost/turn.

**Decided, not built**: tier 2 (`sarvam-mcp`)/tier 3 (raw REST) fallback wiring — scoped
out deliberately, insurance against a failure mode unlikely in a 6-hour local demo; time
is better spent hardening tier 1.

---

## 2026-07-26 11:40 IST — Orchestration gaps closed + a real chat-completion bug caught live

Fixed the two gaps flagged in review: `PipelineError` is now actually raised on Sarvam
failures (verified live — a bad model name correctly surfaced as `PipelineError(stage=
"chat_complete")`, not a bare exception), and a real entity-extraction stage now runs
after every user turn, writing `lender_name`/`loan_amount`/`threat_type` into
`memory.set_fact()` — verified live, facts persist correctly.

**Real bug caught while wiring extraction, would have broken the live demo silently**:
`sarvam-30b`/`sarvam-105b` are reasoning models — they spend the token budget on hidden
`reasoning_content` first and only reach the actual `content` field afterward. At the
original defaults (`max_tokens=512`, no `reasoning_effort`), **every chat completion
returned `content=None`** — confirmed for both the extraction call and the main answer
call. Fixed with `reasoning_effort="low"` + `max_tokens=2048` (reasoning) / `1536`
(extraction). This means the pipeline was silently broken end-to-end until this fix —
worth re-testing the moment any prompt or token budget changes.

**Not yet done — next session's starting point**:

1. **Still no full live end-to-end `/api/v1/analyze` run with real audio.** Individual
   Sarvam calls (`identify_language`, `chat_complete` with both models) are now verified
   live in isolation. STT (`transcribe`/`translate`) and TTS (`speak`) are wired but
   untested — run `HOW_TO_USE.md` §5 (the `say`/`afconvert` trick) next.
2. Frontend not started — `frontend/` doesn't exist yet.
3. Stretch acts (DPDP, IT Act, Karnataka interest-cap) not downloaded.
4. `DEMO_MODE` cached fallback has no cached data.
5. No smoke tests written yet.
6. Tier 2/3 cascade still stubbed only, deliberately.

---

## 2026-07-26 11:45 IST — First full live pipeline success, via a new `analyze/text` endpoint

Split `/api/v1/analyze` into `/api/v1/analyze/voice` (multipart audio, the real product path)
and `/api/v1/analyze/text` (JSON `{query, source_lang_code, target_lang_code}`) — both call
the same `run_pipeline()` core in `logic.py`, only the input stage differs (STT vs. none).
`analyze/text` exists to verify the whole retrieval→reasoning→translate→TTS chain without
recording audio every time.

**First real end-to-end success, against live credits**: asked "IndiaLend app is threatening
to kill me if I dont pay 50000 rupees" — got back a correct §308(1) BNS citation, an accurate
Hindi translation, and real synthesized audio (1.15MB). A same-session follow-up ("what if
they also send my morphed photo to my family?") built directly on the first answer without
re-explaining context — memory continuity confirmed live, not just unit-tested.

**Two more real bugs found by this live run, both fixed**:
- `mayura:v1` rejects any translate input over 1000 characters — our full legal answers
  routinely exceed that. Fixed with `translate_for_speech()`, a sentence-boundary chunker
  that translates in <950-char pieces and joins them.
- Requesting `target_lang_code="en-IN"` crashed with "source and target languages must be
  different" (translate always sources from `en-IN`). Fixed by skipping translation entirely
  when the target is already English.

`docs/api-contract.md` and `HOW_TO_USE.md` updated to document both endpoints, with
`analyze/text` now the recommended first stop for testing.
