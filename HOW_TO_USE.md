# How to test the API yourself

## 1. Set your real Sarvam key

```bash
echo "SARVAM_API_KEY=<your-real-key>" > backend/.env
echo "ENV=dev" >> backend/.env
```

## 2. Start the server

```bash
make api
```

First boot downloads/loads `zembed-1` and builds the Qdrant index — takes ~2-3 min. Watch for `qdrant_index status=built chunk_count=80` in the terminal.

## 3. Health check

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

## 4. Test retrieval only — free, no Sarvam credits spent

```bash
cd backend && uv run python -c "
from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter
r = RetrievalAdapter()
r.build_index()
for row in r.retrieve('recovery agent called my brother and threatened to kill me'):
    print(round(row['score'], 3), row['citation_string'])
"
```

## 5. Test the full pipeline via text — spends real Sarvam credits, no audio needed

`analyze/text` shares the exact same orchestration as `analyze/voice` (retrieval → reasoning →
translate → TTS) minus STT — the fastest way to check the whole pipeline end-to-end.

```bash
curl -X POST http://localhost:8000/api/v1/analyze/text \
  -H "X-Session-Id: test-session-1" -H "Content-Type: application/json" \
  -d '{"query": "IndiaLend app is threatening to kill me if I dont pay 50000 rupees", "target_lang_code": "hi-IN"}'
```

Send a second request with the **same** `X-Session-Id` to test memory continuity — the reply
should build on facts from the first turn without you re-explaining them.

`source_lang_code` defaults to `en-IN`; set it if your `query` isn't already English (Sarvam
translates it first). `target_lang_code` controls the spoken-reply language; use `en-IN` to skip
translation entirely.

## Request/response pairs — paste the request, compare against the real recorded response

Each of these was actually run against `analyze/text` with live credits (not written by hand)
— `summary_card` wording will vary slightly on re-run since it's LLM-generated, but the
citation(s) and the core legal claim should match every time. Use a fresh `X-Session-Id` per
pair unless you're deliberately testing memory continuity.

**Pair 1 — fake §138 arrest threat**

```json
{"query": "Recovery agent sent me a fake court notice under section 138, saying I will be arrested tomorrow", "target_lang_code": "en-IN"}
```

Expected: top citations include `Section 138, Negotiable Instruments Act, 1881` and `Section 308, BNS 2023` (extortion by false accusation). Answer should state that §138 requires a 15-day notice period before any criminal complaint can even be filed — arrest "tomorrow" off a bare notice is legally false, and should call out the recovery agent's own conduct as likely criminal.

**Pair 2 — loan app harvesting contacts/photos**

```json
{"query": "The loan app is accessing my contacts and photos without permission and threatening to share them", "target_lang_code": "en-IN"}
```

Expected: top citations from `RBI (Digital Lending) Directions, 2025`, Para 12/17 range (data-access restrictions, CIMS reporting). Answer should state this access is a Directions violation, not a legal recovery tactic.

**Pair 3 — morphed photo blackmail**

```json
{"query": "They morphed my photo and are threatening to send it to my family and defame me if I dont pay", "target_lang_code": "en-IN"}
```

Expected: top citation `Section 308(1), BNS 2023` (extortion by fear of injury — "injury" includes reputational harm), with `Section 356` (defamation) and `Section 319` (personation) as supporting citations depending on phrasing.

**Pair 4 — late-night abusive recovery calls**

```json
{"query": "Recovery agent is calling me at 11pm every night and using abusive language", "target_lang_code": "en-IN"}
```

Expected: top citations from `RBI (Digital Lending) Directions, 2025` Para 5/8 (recovery agent conduct, calling-hours restriction).

**Memory continuity pair — run after Pair 3, same `X-Session-Id`**

```json
{"query": "what if they also send it to my employer?", "target_lang_code": "en-IN"}
```

Expected: answer references "the morphed photo" / "the payment demand" from Pair 3 directly, without you re-explaining what happened — this is the actual proof memory works, not just a unit test.

## 6. Test the full pipeline via voice — the real product path

Needs an audio file. Fastest way to make one on Mac (no mic needed):

```bash
say -o test_query.aiff "Woh mujhe dhamki de rahe hain ki agar maine paise nahi diye toh mujhe maar denge"
afconvert test_query.aiff test_query.wav -d LEI16 -f WAVE
```

`afconvert` ships with macOS, no install needed. `ffmpeg -i test_query.aiff test_query.wav` works too if you already have it.

```bash
curl -X POST http://localhost:8000/api/v1/analyze/voice \
  -H "X-Session-Id: test-session-1" \
  -F "audio=@test_query.wav"
```

## Sample voice queries (Hindi/Hinglish, same scenarios as the request/response pairs above)

| Say this | Maps to |
|---|---|
| "Woh mujhe maarne ki dhamki de rahe hain agar maine loan nahi chukaya" | Pair 3 scenario (BNS §308) |
| "Recovery agent ne mujhe fake court notice bheja hai, section 138 bola" | Pair 1 scenario (NI Act §138) |
| "Loan app mere contacts aur photos access kar raha hai" | Pair 2 scenario (RBI DLD Para 12/17) |
| "Recovery agent raat 11 baje call kar raha hai aur gaali de raha hai" | Pair 4 scenario (RBI DLD Para 5/8) |

## Troubleshooting

- `python-multipart` missing → `uv add python-multipart` (already pinned, re-run `uv sync` if a fresh clone).
- Slow first request → embedding model + Qdrant index build happens once at startup, not per-request.
- Crash mid-test → restart `make api`, resend with the same `X-Session-Id`, memory reloads from `backend/legalfriend.db`.
