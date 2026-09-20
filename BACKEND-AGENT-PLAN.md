# LegalFriend Backend Agent Plan

## 1. Decision

LegalFriend will move from its current single linear reasoning pipeline to a bounded multi-agent graph for legal-answer requests.

The purpose is not to make every turn expensive or complex. The purpose is to answer each intent with the smallest safe path, then apply independent evidence checks before exposing a legal answer.

## 2. What exists today

| Capability | Current implementation | Limitation |
|---|---|---|
| Voice intake | Saarika verbatim transcription and Saaras English translation | Every voice input proceeds toward legal retrieval. |
| Session memory | SQLite sessions, turns, and extracted facts | Memory is available but not used to route intent. |
| Fact extraction | Sarvam 30B extracts lender, amount, and threat type | Extraction occurs even when the user is greeting the product. |
| Retrieval | Local Qdrant hybrid dense and sparse retrieval with RRF | Retrieval is invoked without first establishing whether legal evidence is needed. |
| Draft answer | Sarvam 105B receives history, facts, and retrieved chunks | No independent claim-coverage or citation-sufficiency critique occurs. |
| Localization | Sarvam translation and TTS | The output can sound confident even if evidence is incomplete. |

## 3. Failure modes this plan fixes

| User input | Wrong current behavior | Required target behavior |
|---|---|---|
| `Hi` | Sends a greeting through legal retrieval and legal reasoning. | Reply with a short product greeting. No retrieval. |
| `What can you help me with?` | Spends tokens on statutory retrieval. | Explain supported use cases and limits. No retrieval. |
| `Can they arrest me for missing a loan payment?` | Produces an answer directly after retrieval. | Retrieve, draft, critique evidence coverage, then judge before answering. |
| `My lender threatened my family` | Treats it only as a general legal query. | Route to urgent-safety guidance, then offer legal analysis if requested. |
| Vague or incomplete legal question | Retrieves arbitrary chunks and answers with confidence. | Ask one focused clarification or state that evidence is insufficient. |

## 4. Target graph

```text
Voice audio
    ↓
STT and English normalization
    ↓
Intent Agent
    ├── Greeting or capability question → direct bounded response
    ├── Urgent safety request → safety response
    ├── Ambiguous request → clarification response
    └── Legal question
            ↓
        Fact Agent
            ↓
        Retrieval
            ↓
        Legal Advocate Agent
            ↓
        Evidence Critic Agent
            ├── revise once → Legal Advocate Agent
            └── sufficient
                    ↓
                Final Judge Agent
                    ├── accept → translate and TTS
                    ├── revise once → Legal Advocate Agent
                    └── abstain → safe evidence-insufficient response
```

Rule 1: A greeting, capability question, safety response, or clarification must never invoke Qdrant retrieval.

Rule 2: A legal answer may have one critic-driven revision and one judge-driven revision at most.

Rule 3: A failed or unsupported answer becomes an explicit abstention. It must not become a more confident rewrite.

## 5. Agent roles

| Agent | Primary model | Input | Structured output | Can retrieve law? | Can answer user directly? |
|---|---|---|---|---|---|
| Intent Agent | Sarvam 30B | Normalized English query, recent session context | `intent`, `needs_retrieval`, `needs_clarification`, `urgency` | No | Only for greeting, capability, safety, and clarification branches. |
| Fact Agent | Sarvam 30B | Legal query and existing facts | Lender, amount, threat, notice details, unknown facts | No | No |
| Legal Advocate Agent | Sarvam 105B | Question, facts, history, retrieved chunks | Draft answer with claim-to-citation map | Receives chunks only | No |
| Evidence Critic Agent | Sarvam 30B | Draft, claim map, retrieved chunks | `sufficient`, `defects`, `repair_instructions` | Receives chunks only | No |
| Final Judge Agent | Sarvam 105B | Draft, critique, chunks, revision count | `accept`, `revise`, or `abstain`, plus final answer | Receives chunks only | Yes, only after accepting evidence. |

The named roles are agents because each has an isolated objective, structured input and output, and a decision that changes graph routing. STT, translation, TTS, SQLite, and Qdrant are supporting services, not agents.

## 6. Intent contract

```json
{
  "intent": "greeting | capability | legal_question | urgent_safety | clarification | unsupported",
  "needs_retrieval": false,
  "needs_clarification": false,
  "urgency": "normal | urgent",
  "reason": "short internal explanation"
}
```

| Intent | Retrieval | Critic and judge | User response |
|---|---|---|---|
| `greeting` | No | No | Welcome and invite a legal question or notice. |
| `capability` | No | No | Explain supported loan-notice questions, citations, languages, and limitations. |
| `urgent_safety` | No | No | Immediate safety guidance without unsupported legal claims. |
| `clarification` | No | No | Ask one minimal clarifying question. |
| `unsupported` | No | No | State the boundary of the product. |
| `legal_question` | Yes | Yes | Evidence-checked legal response or abstention. |

## 7. Evidence contract

The Legal Advocate Agent must not return free-form prose alone. It must return a typed claim map.

```json
{
  "draft_answer": "Do not panic. A lender cannot lawfully use an unsupported arrest threat to collect a civil debt.",
  "claims": [
    {
      "claim": "The arrest threat is unsupported on the facts provided.",
      "citation_ids": ["BNS 2023 · Section 308(5)"],
      "evidence_strength": "direct"
    }
  ],
  "missing_information": ["Whether a cheque was issued and dishonoured"],
  "answer_scope": "general legal information, not representation"
}
```

The Evidence Critic Agent must reject a draft when any of the following is true.

1. A material legal claim has no citation.
2. A citation does not support the wording or scope of its claim.
3. The retrieved chunks do not contain enough information to answer safely.
4. The draft ignores a required qualification or missing fact.
5. The answer is inconsistent with the routed user intent.

## 8. Judge contract

```json
{
  "verdict": "accept | revise | abstain",
  "final_answer": "string or null",
  "revision_instructions": ["string"],
  "abstention_reason": "string or null",
  "citation_ids": ["string"]
}
```

The Final Judge Agent is not a truth oracle. It cannot prove legal correctness merely by re-reading another model's work. The system therefore combines model critique with deterministic checks.

1. Every displayed citation ID must exist in retrieved chunks.
2. Every material claim must map to at least one citation.
3. The judge may only accept an answer when the critic marks evidence sufficient.
4. A judge rejection produces a revision or abstention, never an unbounded loop.

## 9. Proposed implementation structure

```text
backend/src/modules/legal_notice/features/analyze/
├── router.py
├── schemas.py
├── logic.py
├── graph.py
├── state.py
├── policies.py
└── agents/
    ├── intent_agent.py
    ├── fact_agent.py
    ├── legal_advocate_agent.py
    ├── evidence_critic_agent.py
    └── final_judge_agent.py
```

`graph.py` owns graph construction and legal-path routing. `state.py` owns the typed graph state and every node's structured outputs. `logic.py` remains the endpoint-facing adapter that performs STT, invokes the graph, then performs translation and TTS.

The proposed orchestration runtime is LangGraph because the flow now has explicit branching, bounded repair edges, and terminal abstention states. The graph remains small and deterministic. It is not a planner-worker swarm.

## 10. Build sequence

| Step | Deliverable | Validation |
|---|---|---|
| 1 | Add typed intent, critique, judge, and graph-state schemas. | Parse valid and invalid structured model outputs. |
| 2 | Implement Intent Agent and direct no-RAG branches. | `hi`, capability, safety, ambiguous, and legal-query route tests. |
| 3 | Move existing fact extraction into Fact Agent. | Persisted facts retain only grounded extracted values. |
| 4 | Implement Legal Advocate claim map. | Every legal draft exposes its citations and missing facts. |
| 5 | Implement Evidence Critic and one bounded repair edge. | Unsupported claim causes one revision, then abstention if still unsupported. |
| 6 | Implement Final Judge and deterministic evidence checks. | Accept, revise, and abstain paths are all exercised. |
| 7 | Integrate graph after STT and before translation and TTS. | Voice and text endpoints retain their existing public response schema. |
| 8 | Add trace logging and evaluation fixtures. | One request ID exposes intent, retrieval decision, critique verdict, judge verdict, and final branch. |

## 11. Evaluation set required before enabling the graph

| Category | Minimum examples | Pass criterion |
|---|---|---|
| Greeting and capability | 10 | Zero retrieval calls. |
| Legal answerable questions | 20 | Every material claim has valid retrieved citation coverage. |
| Insufficient evidence | 10 | Safe clarification or abstention, no fabricated answer. |
| Urgent safety | 10 | No legal overclaim and no retrieval call. |
| Critic repair cases | 10 | Critic catches injected unsupported claim. |
| Judge rejection cases | 10 | Judge rejects flawed draft or chooses abstention. |
| Multi-turn facts | 10 | Follow-up uses correct persisted facts without leaking another session. |

## 12. Non-negotiable operating limits

1. Maximum legal-path model calls are Intent, Fact, Advocate, Critic, one Advocate revision, and Judge.
2. Maximum legal draft revisions are two total drafts.
3. No RAG for non-legal intents.
4. No final legal answer without a valid claim map and citation coverage.
5. No silent fallback from a failed judge to an unreviewed draft.
6. No model receives legal corpus data unless the Intent Agent has selected `legal_question`.

## 13. Hard graph execution budget

Every graph state must contain these fields.

```json
{
  "agent_steps": 0,
  "draft_count": 0,
  "critic_revision_count": 0,
  "judge_revision_count": 0
}
```

| Branch | Maximum agent steps | Maximum drafts | Terminal condition |
|---|---:|---:|---|
| Greeting, capability, safety, clarification, unsupported | 1 | 0 | Intent Agent returns its bounded response. |
| Legal answer accepted on first pass | 5 | 1 | Judge accepts the Advocate draft. |
| Legal answer repaired by critic | 7 | 2 | Judge accepts or abstains after the repaired draft. |
| Legal answer repaired by judge | 8 | 2 | Judge accepts the revised draft or abstains. |
| Any malformed output, timeout, or budget breach | 8 | 2 | Return a localized safe fallback response. |

Rule 1: `agent_steps` increments before every agent node executes.

Rule 2: The graph must check `agent_steps >= 8` before taking any edge. At that limit it must route directly to `safe_abstention`.

Rule 3: `draft_count` increments whenever the Legal Advocate Agent generates a draft. If `draft_count >= 2`, neither the critic nor judge may route back to the Advocate Agent.

Rule 4: The Evidence Critic Agent has one repair edge only. If it finds defects after the second draft, it routes to `safe_abstention`.

Rule 5: The Final Judge Agent has one repair edge only. If it rejects the second draft, it routes to `safe_abstention`.

Rule 6: `safe_abstention` is terminal. It cannot call an agent, retrieval, translation model, or judge again. It returns a short localized message that says the available information is not sufficient for a reliable answer and asks for the minimum missing fact.

```text
Intent → Fact → Advocate → Critic → Judge → terminal
                       ↑          │
                       └──────────┘ one critic repair only

Intent → Fact → Advocate → Critic → Judge → Advocate → Critic → Judge → terminal
                                              ↑                           │
                                              └───────────────────────────┘ one judge repair only

Any attempt to take a third Advocate edge → safe_abstention
Any attempt to execute step 9 → safe_abstention
```

## 14. Migration rule

The existing linear pipeline remains the baseline until the new graph passes the evaluation set. The graph should be enabled behind `AGENT_GRAPH_ENABLED` so the backend can compare linear and multi-agent results on the same request set before making the graph the default.
