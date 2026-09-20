<p align="center">
  <img src="https://em-content.zobj.net/source/apple/391/balance-scale_2696-fe0f.png" width="100" alt="Nyaya Dost" />
</p>

<h1 align="center">Nyaya Dost</h1>

<p align="center">
  <strong>Hear your legal rights, in your own language.</strong>
</p>

<p align="center">
  A voice-in, voice-out legal-aid agent for people getting threatened by predatory<br/>
  loan recovery agents — no typing, no forms, no reading English legal text.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?style=flat" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Next.js-16-black?style=flat" alt="Next.js 16">
  <img src="https://img.shields.io/badge/LangGraph-multi--agent-orange?style=flat" alt="LangGraph multi-agent">
  <img src="https://img.shields.io/badge/voice-Sarvam%20AI-purple?style=flat" alt="Voice: Sarvam AI">
</p>

<p align="center">
  <a href="#product-tour">Product Tour</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#stack">Stack</a> •
  <a href="#folder-structure">Folder Structure</a> •
  <a href="#run-locally-with-docker-compose">Run locally</a>
</p>

---

Speak the situation in Hindi (or another Indian language), and a grounded, cited legal answer is spoken straight back. A LangGraph multi-agent pipeline classifies the intent, extracts the facts, retrieves the relevant statutes, drafts an answer, checks every claim against the retrieved excerpts, and only releases what it can actually cite — abstaining rather than fabricating.



## Architecture

```
spoken question
      │  speech-to-text + translate (Sarvam)
      ▼
  intent (LLM) ──► facts (LLM) ──► retrieval (Qdrant hybrid dense+sparse)
                                          │ statutory excerpts
                                          ▼
                                     advocate (LLM) ──► critic (LLM) ──► judge (LLM)
                                                                              │
                                                          accept / revise / abstain
                                                                              ▼
                                                        translate + text-to-speech (Sarvam)
```

1. **Intent** — classifies the query (legal question, urgent safety, greeting, capability).
2. **Facts** — extracts case facts (lender, loan amount, interest rate, threat type, contact timing).
3. **Retrieval** — hybrid dense+sparse search (`zeroentropy/zembed-1` + BM25 via Qdrant RRF fusion) over a corpus of the Bharatiya Nyaya Sanhita, the Negotiable Instruments Act, and the RBI Digital Lending Directions, 2025.
4. **Advocate** — drafts an answer, citing only what the retrieved excerpts actually support.
5. **Critic** — rejects any claim without an exact supporting citation.
6. **Judge** — makes the final release decision; only accepts claims it can verify against the excerpts, revises what it can, and abstains rather than fabricates.

The final answer is translated and spoken back via Sarvam TTS, chunked to respect the API's per-request character limit and stitched back into one continuous audio clip.

## Stack

### Backend

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph — intent → facts → retrieval → advocate → critic → judge |
| Voice | Sarvam AI — speech-to-text, translation, chat, text-to-speech |
| Retrieval | Qdrant — hybrid dense (`zeroentropy/zembed-1`) + sparse (BM25) search, RRF fusion |
| API | FastAPI (Python 3.12), Server-Sent Events streaming |
| Deployment | Docker Compose — distroless, non-root, read-only container filesystems |

### Frontend

| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router), React 19, TypeScript |
| UI/UX | Voice-first PWA, live agent-step visualization, light/dark themes |
| Integration | Streaming API client wired to the backend's SSE pipeline |

## Folder Structure

```
nyaya-dost/
├── backend/          # FastAPI service, agent graph, retrieval adapter
├── frontend/         # Next.js voice-first PWA
├── legal-corpus/     # source statutes + chunking pipeline
└── docs/assets/      # screenshots, demo media
```

### `backend/`

```
backend/
├── src/
│   ├── core/
│   │   ├── sarvam/          # Sarvam API tiers — REST, SDK, MCP clients
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── memory.py        # SQLite conversation memory
│   │   ├── security.py
│   │   └── api_errors.py
│   ├── ingestion/           # statute PDF → chunked corpus pipeline
│   │   ├── chunk_bns.py
│   │   ├── chunk_ni_act.py
│   │   ├── chunk_rbi_directions.py
│   │   ├── chunk_rbi_recovery_agents.py
│   │   ├── chunk_usurious_loans_act.py
│   │   └── pdf_text.py
│   ├── modules/
│   │   └── legal_notice/
│   │       ├── features/analyze/         # intent → facts → advocate → critic → judge
│   │       └── implementations/retrieval_adapter.py   # Qdrant hybrid retrieval
│   ├── main.py              # FastAPI app entrypoint
│   └── runtime_api.py       # agent graph runtime, SSE streaming
├── tests/
├── Dockerfile
└── pyproject.toml
```

### `frontend/`

```
frontend/
├── src/
│   ├── app/                 # Next.js App Router entry (layout, page, globals.css)
│   ├── features/
│   │   └── legal-notice-flow/
│   │       ├── components/  # ArriveScreen, ConversationScreen
│   │       ├── hooks/       # useAnalyzePipeline, useRecorder
│   │       └── schemas/     # analyze.schema.ts
│   ├── shared/
│   │   ├── hooks/           # useCanUseLiveCamera
│   │   ├── lib/             # api-client, citationSources, languages, turnAudioPlayer, uiStrings
│   │   └── ui/              # Orb, AgentSteps, Citation, LanguageSwitcher, ThemeToggle, icons
│   └── config/site.ts
├── public/
├── Dockerfile
└── package.json
```

## Run locally with Docker Compose

1. Add a real `SARVAM_API_KEY` to `backend/.env`:

   ```dotenv
   SARVAM_API_KEY=your-key-here
   ```

2. Build and start the complete app:

   ```bash
   docker compose up --build
   ```

3. Open `http://localhost:3000`. The FastAPI service is available at
   `http://localhost:8000`, with health checks at `/healthz` and `/readyz`.

The first image build downloads the embedding models and builds the embedded Qdrant index.
Docker caches those layers, so later builds skip that work unless the backend dependencies
or retrieval setup changes. Docker volumes persist the model cache, Qdrant index, and
SQLite conversation memory across restarts.

The Docker profile defaults to `sentence-transformers/all-MiniLM-L6-v2` for a compact
CPU-only image. The direct host profile keeps the backend's existing `zeroentropy/zembed-1`
default. Set `DENSE_MODEL_NAME` before `docker compose up --build` if the container should
use a different Sentence Transformers model.

Both services run as non-root users on distroless runtime images. Compose also makes the
container filesystems read-only, drops every Linux capability, enables no-new-privileges,
and limits process counts. Only the three backend data volumes and bounded temporary
filesystems remain writable.

To stop the app, press `Ctrl+C`, then run:

```bash
docker compose down
```

For access from another device on the same network, build with the laptop's LAN address:

```bash
NEXT_PUBLIC_API_BASE_URL=http://YOUR_LAN_IP:8000 docker compose up --build
```

Add `http://YOUR_LAN_IP:3000` to `CORS_EXTRA_ORIGINS` in `backend/.env` as a JSON array.

<!--
## Demo

<video src="docs/assets/nyaya-dost-demo.mp4" controls width="430">
  Your browser does not support inline video. <a href="docs/assets/nyaya-dost-demo.mp4">Download the demo (MP4)</a>.
</video>

*Real end-to-end run: a spoken question ("A recovery agent called me at midnight and said I would be sent to jail if I do not pay interest at 1% per day on my loan...") goes through the full multi-agent pipeline and comes back as a cited, spoken answer.*
-->
