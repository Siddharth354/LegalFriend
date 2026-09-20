# API Contract — LegalFriend

> Single source of truth between backend and frontend. Backend updates this first, then `schemas.py`, then hands off. Frontend implements Zod from this file, not from guessing.

## Endpoints

```
POST /api/v1/analyze/voice   — multipart audio, the real product path
POST /api/v1/analyze/text    — JSON text, same orchestration, no STT
```

Both share one pipeline (`finalize_response` in `logic.py`) and return the identical response shape below. `analyze/text` exists to test and debug the retrieval, reasoning, translation, and TTS chain without recording audio each time. Frontend should build against `analyze/voice`.

## Request — `POST /api/v1/analyze/voice`, multipart/form-data

| Field | Type | Required | Notes |
|---|---|---|---|
| `audio` | file, any audio MIME (`audio/wav`, `audio/mp4`, etc.) | Yes | Full recorded clip, one upload, not streamed |

The voice response uses the `language_code` returned by Saarika transcription, such as `kn-IN` for Kannada. It falls back to `hi-IN` only when transcription does not return a language code.

English `en` and `en-IN` detections normalize to `en-IN`, so an English voice question receives an English chat and speech response without a translation call.

Greeting and product-capability replies are localized and cached by reply text and target language, including their TTS audio. Repeated simple requests therefore skip translation and speech generation.

An empty or whitespace-only voice transcription bypasses translation, retrieval, and agents. It returns a cached Hindi LegalFriend introduction that asks how it can help and lists its loan-notice, lender-threat, next-step, and legal-excerpt services.

Sarvam verbatim transcription accepts clips up to 30 seconds. Longer clips return a user-facing request to record a shorter question.

## Request — `POST /api/v1/analyze/text`, application/json

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | Yes | The question, in `source_lang_code`'s language |
| `source_lang_code` | string | No, default `en-IN` | Set if `query` isn't already English |
| `target_lang_code` | string | No, default `hi-IN` | Language of the spoken reply |

Both endpoints share this header:

| Header | Required | Notes |
|---|---|---|
| `X-Session-Id` | Yes | Client-generated, persisted in `localStorage`, same value every turn in a conversation |

**Not yet implemented**: optional document image upload (OCR path) on either endpoint.

## Success response — 200 (both endpoints)

```json
{
  "summary_card": "string — the final answer in the user's detected or requested language",
  "citations": [
    { "citation_string": "Section 308(5), BNS 2023", "content": "string — full chunk text", "score": 0.62 }
  ],
  "advice": {
    "language": "hi-IN",
    "transcript": "string — same localized reply used for TTS",
    "verbatim_transcript": "string — user's own words, original language/script",
    "audio_payload_b64": "string — base64-encoded audio bytes, decode and play"
  }
}
```

`citations` can be an empty array. `audio_payload_b64` decodes to raw audio bytes — codec depends on Sarvam's TTS default (not yet locked, ask backend before assuming a container format).

## Error response — 502 (pipeline failure) or 500 (unhandled)

```json
{
  "error": {
    "stage": "string — which pipeline stage failed, e.g. 'translate_text'",
    "message_en": "string — internal detail, do not show to user",
    "message_user": "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again."
  }
}
```

Always show `message_user` verbatim, never `message_en`, never a generic browser error screen.

## Example — curl

```bash
curl -X POST http://localhost:8000/api/v1/analyze/voice \
  -H "X-Session-Id: abc-123" \
  -F "audio=@test_query.wav"

curl -X POST http://localhost:8000/api/v1/analyze/text \
  -H "X-Session-Id: abc-123" -H "Content-Type: application/json" \
  -d '{"query": "They are threatening to kill me if I dont pay", "target_lang_code": "hi-IN"}'
```

## CORS

Allowed by default: `http://localhost:3000`, `http://127.0.0.1:3000`.

For LAN-phone demo testing, backend sets `CORS_EXTRA_ORIGINS` in `backend/.env` as a JSON array, e.g. `CORS_EXTRA_ORIGINS=["http://192.168.1.5:3000"]`. Ask backend to add your current LAN IP before testing from a phone.

## Integration status

| Item | Backend | Frontend | Verified |
|---|---|---|---|
| `analyze/text` full pipeline | Ready | N/A | Verified live on 2026-07-26 with a legal-threat query |
| `analyze/voice` multipart upload | Ready | Ready | Route and required `audio` field validated. Browser microphone upload awaits retry. |
| Success response | Ready | Ready | Live text response contains every required contract field. |
| Localized errors | Ready | Ready | Backend returns `message_user`, frontend renders it verbatim. |
| Audio playback | Ready | Ready | Response audio bytes validated. Browser playback awaits microphone-route success. |
| LAN phone demo | Ready | Ready | Pending same-network device test. |

## Contract validation log

| Date | Check | Result | Evidence |
|---|---|---|---|
| 2026-07-26 | `GET /healthz` | Passed | HTTP 200 with `{"status":"ok"}`. |
| 2026-07-26 | `GET /readyz` | Passed | HTTP 200 with `{"status":"ready"}`. |
| 2026-07-26 | `POST /api/v1/analyze/text` | Passed | HTTP 200. Validated non-empty `summary_card`, `citations`, and every `advice` field, including audio bytes. |
| 2026-07-26 | `POST /api/v1/analyze/voice` without `audio` | Passed | HTTP 422. FastAPI enforces the required multipart audio field. |
| 2026-07-26 | Frontend voice route | Corrected | Frontend now calls `/api/v1/analyze/voice`. The prior `/api/v1/analyze` route caused the user-visible generic error. |
| 2026-07-26 | Current-source text greeting graph | Passed | `Hi` reached the deterministic greeting branch in one agent step, returned no citations, and did not invoke retrieval. |
| 2026-07-26 | Kannada voice-language propagation | Passed | A mocked `kn-IN` Saarika transcription produced a `kn-IN` translated transcript and TTS request. |
| 2026-07-26 | Kannada chat and simple-response cache | Passed | A mocked `kn-IN` capability request produced Kannada in both `summary_card` and `advice.transcript`. Two requests made one translation and one TTS call. |
| 2026-07-26 | Empty voice fallback | Passed | An empty transcription returned the Hindi app introduction with one TTS call and no translation or agent execution. |
| 2026-07-26 | English voice greeting | Passed | An `en` greeting returned English in both `summary_card` and `advice.transcript`, with no translation call. |
| 2026-07-26 | Empty input safeguards | Passed | A whitespace transcription returned the Hindi service introduction without translation or agents. An empty intent-model response routed to clarification without retrieval or a server error. |
