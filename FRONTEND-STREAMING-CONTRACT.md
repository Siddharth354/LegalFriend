# Frontend Streaming Contract — Live Agent Pipeline Status

> For the backend agent. The frontend's `AgentSteps` panel currently **fakes** progress with a client-side timer (2.2s per step, 6 fixed steps) because there is no live signal from the backend today. This file specifies the real SSE contract needed to replace that fake timer with the actual `graph.py` execution trace.

## Why this is needed

`docs/api-contract.md`'s existing `POST /api/v1/analyze/voice` and `/text` are blocking — one request, one response, only after the *entire* LangGraph run finishes (`graph.invoke(...)`). The frontend has no visibility into which node is running until everything is done. The UI now shows agents appearing one at a time, stacking downward as each completes — that pacing is currently simulated, not real.

## New endpoints — additive, do not remove the existing ones

```
POST /api/v1/analyze/voice/stream   — same multipart audio body as /voice
POST /api/v1/analyze/text/stream    — same JSON body as /text
```

Same request shape, headers, and auth as the existing endpoints (see `docs/api-contract.md`). Response `Content-Type: text/event-stream`.

**Why POST, not a plain SSE `GET` via `EventSource`**: the browser's native `EventSource` API cannot send a POST body or custom headers, and we need to send audio/JSON + `X-Session-Id`. The frontend will consume this via `fetch()` + `response.body.getReader()`, parsing SSE-formatted lines manually — not the `EventSource` class. Backend just needs to stream standard SSE-formatted bytes; the transport mechanics are the frontend's problem.

## Event format

Standard SSE: each event is `event: <type>\ndata: <json>\n\n` (note the blank line terminator). Emit and **flush** after every event — do not buffer the whole response.

### `event: agent_start`

Fired the moment a node begins executing.

```json
{"node": "intent"}
```

### `event: agent_done`

Fired the moment a node finishes. `detail` is optional, short, human-readable — surfaced under the step label in the UI (e.g. "Classified as legal_question").

```json
{"node": "intent", "detail": "Classified as legal_question"}
```

### `event: result`

Exactly one, always last. Carries the **exact same JSON shape** the blocking `/voice` and `/text` endpoints already return (`AnalyzeResponse` — `summary_card`, `citations`, `advice`). Terminates the stream.

```json
{"summary_card": "...", "citations": [...], "advice": {...}}
```

### `event: error`

If the pipeline fails mid-stream, emit this **instead of** `result` and close the stream. Same shape as the existing blocking-endpoint error body (`docs/api-contract.md`'s 502 response), just delivered as an SSE event instead of an HTTP status code (the HTTP response itself is already `200` with `text/event-stream` — errors can't use status codes once streaming has started).

```json
{"stage": "advocate", "message_user": "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again."}
```

## Node IDs — must match `graph.py` exactly

The frontend maps these IDs to display labels itself (`intent` → "Intent Agent"). Send the raw node ID only, nothing else:

`intent`, `direct`, `facts`, `retrieval`, `advocate`, `critic`, `critic_revision`, `judge`, `judge_revision`, `safe`

The frontend does **not** assume a fixed 6-step path — `route_after_intent`/`route_after_critic`/`route_after_judge` in `graph.py` are conditional, so a real run might be as short as `intent → direct` or loop through `advocate` multiple times via `critic_revision`/`judge_revision`. Send exactly the nodes that actually ran, in the order they actually ran, however long that turns out to be. The UI stacks whatever it receives.

## Suggested implementation shape (LangGraph)

`graph.stream(initial_state, stream_mode="updates")` yields `{node_name: state_delta}` right after each node completes — that's `agent_done` for free. There's no native "about to start" hook without wrapping each node function, but since transitions are synchronous and sequential, the simplest correct approach: **emit `agent_start` for node N+1 immediately after emitting `agent_done` for node N** (you already know the next node from the edge/routing function you just evaluated). Emit the very first `agent_start` (for `intent`) before calling `.stream()` at all.

```python
async def analyze_stream(...):
    yield sse("agent_start", {"node": "intent"})
    async for update in graph.astream(initial_state, stream_mode="updates"):
        node_name, delta = next(iter(update.items()))
        yield sse("agent_done", {"node": node_name, "detail": summarize(node_name, delta)})
        next_node = ...  # whatever your routing already computed
        if next_node is not None:
            yield sse("agent_start", {"node": next_node})
    yield sse("result", final_response.model_dump())
```

Use `graph.astream(...)` (async) not `graph.stream(...)` inside a FastAPI `StreamingResponse`/async generator, so the event loop isn't blocked between yields.

## What the frontend will do once this exists

Replace `AgentSteps`'s internal `setInterval` timer with real `agent_start`/`agent_done` events consumed from the stream. No other UI change needed — the stacking/reveal/border-beam behavior already matches this event shape exactly, it's just fed by a timer today instead of your events.
