from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

import orjson
import pytest
from pytest import MonkeyPatch

from src.core.api_errors import PipelineError
from src.core.memory import Memory
from src.modules.legal_notice.features.analyze import graph, logic
from src.modules.legal_notice.features.analyze.agents import (
    issue_planner_agent,
    legal_advocate_agent,
)
from src.modules.legal_notice.features.analyze.graph import (
    AgentGraphOutcome,
    AgentNodeEvent,
    stream_agent_graph,
)
from src.modules.legal_notice.features.analyze.state import (
    IssuePlan,
    LegalClaim,
    LegalDraft,
    LegalIssue,
)
from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter


class StubRetrieval:
    def __init__(self) -> None:
        self.top_k_values: list[int | None] = []
        self.queries: list[str] = []

    def retrieve(
        self,
        english_query: str,
        top_k: int | None = None,
    ) -> list[dict[str, object]]:
        self.top_k_values.append(top_k)
        return [
            {
                "chunk_id": "ni_act_1881_s138",
                "act": "Negotiable Instruments Act, 1881",
                "citation_string": "Section 138, Negotiable Instruments Act, 1881",
                "content": "A cheque dishonour notice must satisfy the statutory conditions.",
                "score": 1.0,
            }
        ]

    def retrieve_many(
        self,
        english_queries: list[str],
        top_k: int | None = None,
    ) -> list[list[dict[str, object]]]:
        self.queries.extend(english_queries)
        return [self.retrieve(query, top_k) for query in english_queries]


def retrieval_stub() -> RetrievalAdapter:
    return cast(RetrievalAdapter, StubRetrieval())


def decode_sse(chunk: bytes) -> tuple[str, dict[str, object]]:
    event_line, data_line = chunk.decode().strip().splitlines()
    return event_line.removeprefix("event: "), cast(
        dict[str, object], orjson.loads(data_line.removeprefix("data: "))
    )


async def collect_graph_items(
    query: str,
    session_id: str,
    database_path: Path,
) -> list[AgentNodeEvent | AgentGraphOutcome]:
    return [
        item
        async for item in stream_agent_graph(
            query,
            session_id,
            Memory(database_path),
            retrieval_stub(),
        )
    ]


@pytest.mark.asyncio
async def test_greeting_stream_reports_actual_direct_path(tmp_path: Path) -> None:
    items = await collect_graph_items("Hi", "greeting", tmp_path / "greeting.sqlite")
    node_events = [item for item in items if isinstance(item, AgentNodeEvent)]
    assert [(item.event, item.node) for item in node_events] == [
        ("agent_start", "intent"),
        ("agent_done", "intent"),
        ("agent_start", "direct"),
        ("agent_done", "direct"),
    ]
    outcome = items[-1]
    assert isinstance(outcome, AgentGraphOutcome)
    assert outcome.terminal_reason == "greeting"
    assert outcome.citations == []


@pytest.mark.asyncio
async def test_immediate_threat_stream_skips_retrieval(tmp_path: Path) -> None:
    items = await collect_graph_items(
        "Someone is outside my house and threatening to kill me.",
        "urgent-safety",
        tmp_path / "urgent.sqlite",
    )
    node_events = [item for item in items if isinstance(item, AgentNodeEvent)]
    assert [(item.event, item.node) for item in node_events] == [
        ("agent_start", "intent"),
        ("agent_done", "intent"),
        ("agent_start", "direct"),
        ("agent_done", "direct"),
    ]
    outcome = items[-1]
    assert isinstance(outcome, AgentGraphOutcome)
    assert outcome.terminal_reason == "urgent_safety"
    assert outcome.citations == []


def test_threat_with_loan_and_payment_demand_routes_to_urgent_legal_reasoning() -> None:
    decision = graph.classify_intent(
        "A lender is threatening to kill me unless I pay Rs 50,000 for my loan.",
        "",
    )
    assert decision.intent == "legal_question"
    assert decision.needs_retrieval is True
    assert decision.urgency == "urgent"


@pytest.mark.asyncio
async def test_legal_stream_plans_retrieves_and_answers_once(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    issue_plan = IssuePlan(
        issues=[
            LegalIssue(
                issue_id="legal_notice",
                question="What deadline applies to the cheque notice?",
                retrieval_query="Section 138 cheque notice deadline",
            )
        ],
        follow_up_questions=["Can you share the notice image?"],
    )

    def plan_legal_issues(english_query: str, recent_history: str) -> IssuePlan:
        return issue_plan

    def draft_legal_answer(
        english_query: str,
        plan: IssuePlan,
        recent_history: str,
        citations: list[dict[str, object]],
    ) -> LegalDraft:
        return LegalDraft(
            draft_answer=(
                "Review the statutory conditions. "
                "Section 138, Negotiable Instruments Act, 1881"
            ),
            claims=[
                LegalClaim(
                    claim="The statutory notice conditions must be checked.",
                    citation_ids=["Section 138, Negotiable Instruments Act, 1881"],
                    evidence_strength="direct",
                )
            ],
            answer_scope="Section 138 notice",
        )

    monkeypatch.setattr(graph, "plan_legal_issues", plan_legal_issues)
    monkeypatch.setattr(graph, "draft_legal_answer", draft_legal_answer)

    items = await collect_graph_items(
        "I received a legal notice under Section 138 for a dishonoured cheque.",
        "legal-plan",
        tmp_path / "legal.sqlite",
    )
    completed_nodes = [
        item.node
        for item in items
        if isinstance(item, AgentNodeEvent) and item.event == "agent_done"
    ]
    assert completed_nodes == ["intent", "planner", "retrieval", "advocate"]
    outcome = items[-1]
    assert isinstance(outcome, AgentGraphOutcome)
    assert "Section 138" in outcome.answer
    assert "Can you share the notice image?" in outcome.answer
    assert len(outcome.citations) == 1


@pytest.mark.asyncio
async def test_legal_stream_abstains_when_claim_citation_is_missing(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    issue_plan = IssuePlan(
        issues=[
            LegalIssue(
                issue_id="police_procedure",
                question="Must the borrower go to a police station?",
                retrieval_query="loan recovery police procedure",
            )
        ]
    )

    monkeypatch.setattr(
        graph,
        "plan_legal_issues",
        lambda english_query, recent_history: issue_plan,
    )
    monkeypatch.setattr(
        graph,
        "draft_legal_answer",
        lambda english_query, plan, recent_history, citations: LegalDraft(
            draft_answer="The borrower must report to the police immediately.",
            claims=[
                LegalClaim(
                    claim="The borrower must report to the police immediately.",
                    citation_ids=["missing-citation"],
                    evidence_strength="direct",
                )
            ],
            answer_scope="unsupported police procedure",
        ),
    )

    items = await collect_graph_items(
        "A lender demands that I go to a police station now.",
        "unsupported-claim",
        tmp_path / "unsupported.sqlite",
    )
    completed_nodes = [
        item.node
        for item in items
        if isinstance(item, AgentNodeEvent) and item.event == "agent_done"
    ]
    assert completed_nodes == [
        "intent",
        "planner",
        "retrieval",
        "advocate",
        "safe",
    ]
    outcome = items[-1]
    assert isinstance(outcome, AgentGraphOutcome)
    assert outcome.terminal_reason == "evidence_insufficient"
    assert outcome.citations == []


def test_retrieval_query_removes_numeric_noise_without_broadening_issue() -> None:
    query = graph._retrieval_query(
        "I borrowed 10,000 rupees at 1% interest and the lender contacted me."
    )
    assert "10,000" not in query
    assert "1%" not in query
    assert "lender contacted me" in query
    assert "recovery agent" not in query


def test_threat_query_preserves_focused_legal_terms() -> None:
    query = graph._retrieval_query(
        "A lender threatens to kill me unless I pay Rs 50,000."
    )
    assert "threatens to kill me" in query
    assert "50,000" not in query


def test_rate_only_question_routes_to_legal_reasoning_without_amount() -> None:
    decision = graph.classify_intent(
        "Someone offered to lend me money at 1% interest per day. Kya sahi rahega?",
        "",
    )
    assert decision.intent == "legal_question"
    assert decision.needs_retrieval is True


def test_retrieval_logs_every_ranked_chunk(monkeypatch: MonkeyPatch) -> None:
    retrieval = StubRetrieval()
    log_events: list[tuple[str, dict[str, object]]] = []

    def capture_log(event: str, **values: object) -> None:
        log_events.append((event, values))

    monkeypatch.setattr(graph.logger, "info", capture_log)
    issue_plan = IssuePlan(
        issues=[
            LegalIssue(
                issue_id="legal_notice",
                question="What rules govern the notice?",
                retrieval_query="legal notice for loan",
            )
        ]
    )
    citations = graph._retrieve_issue_citations(
        cast(RetrievalAdapter, retrieval),
        issue_plan,
    )

    assert len(citations) == 1
    query_event = next(
        values for event, values in log_events if event == "retrieval_query"
    )
    chunk_event = next(
        values for event, values in log_events if event == "retrieved_chunk"
    )
    assert query_event["issue_id"] == "legal_notice"
    assert query_event["top_k"] == 3
    assert chunk_event["rank"] == 1
    assert chunk_event["score"] == 1.0
    assert chunk_event["content"] == (
        "A cheque dishonour notice must satisfy the statutory conditions."
    )


def test_issue_retrieval_sends_independent_queries() -> None:
    retrieval = StubRetrieval()
    issue_plan = IssuePlan(
        issues=[
            LegalIssue(
                issue_id="contact_hours",
                question="Was the call made during prohibited hours?",
                retrieval_query="RBI recovery calls after 7 p.m.",
            ),
            LegalIssue(
                issue_id="death_threat",
                question="What law governs a threat to kill for payment?",
                retrieval_query="BNS fear of death demand money extortion",
            ),
        ]
    )

    graph._retrieve_issue_citations(cast(RetrievalAdapter, retrieval), issue_plan)

    assert len(retrieval.queries) == 2
    assert "after 7 p.m." in retrieval.queries[0]
    assert "fear of death" in retrieval.queries[1]


def test_ambiguous_forced_to_chill_phrase_plans_distress_issues() -> None:
    plan = issue_planner_agent.plan_legal_issues(
        "They said I will be forced to chill and are demanding payment at midnight.",
        "",
    )

    issue_ids = {issue.issue_id for issue in plan.issues}
    assert "recovery_contact_hours" in issue_ids
    assert "recovery_intimidation" in issue_ids
    assert "criminal_threat_or_extortion" in issue_ids
    assert any("exact words" in question for question in plan.follow_up_questions)


def test_105b_conversational_reasoning_excludes_unmentioned_cheque_law(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def chat_complete(
        system_prompt: str,
        user_prompt: str,
        model: str = "sarvam-105b",
        max_tokens: int = 2048,
        reasoning_effort: str | None = "low",
    ) -> str:
        calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
                "reasoning_effort": reasoning_effort,
            }
        )
        return (
            "I understand this is stressful. What this means for you: the rate needs "
            "review and midnight recovery contact may be prohibited. "
            "[Citation: Section 3, Usurious Loans Act, 1918] "
            "[Citation: Paragraph 2, RBI/2022-23/108 (Recovery Agents)]\n\n"
            "What you should do now:\n1. Preserve the notice.\n\n"
            "Please tell me:\nWhat is the lender name?"
        )

    monkeypatch.setattr(legal_advocate_agent.sarvam, "chat_complete", chat_complete)
    plan = IssuePlan(
        issues=[
            LegalIssue(
                issue_id="interest_and_disclosure",
                question="Is the daily interest legally valid?",
                retrieval_query="Usurious Loans Act excessive interest",
            )
        ]
    )
    citations: list[dict[str, object]] = [
        {
            "act": "Usurious Loans Act, 1918",
            "citation_string": "Section 3, Usurious Loans Act, 1918",
            "content": "The Court may reopen a substantially unfair transaction with excessive interest.",
        },
        {
            "act": "RBI Recovery Agents Circular, 2022",
            "citation_string": "Paragraph 2, RBI/2022-23/108 (Recovery Agents)",
            "content": "Calls after 7:00 p.m. for recovery are prohibited.",
        },
        {
            "act": "Negotiable Instruments Act, 1881",
            "citation_string": "Section 138, Negotiable Instruments Act, 1881",
            "content": "Dishonour of cheque conditions.",
        },
    ]

    draft = legal_advocate_agent.draft_legal_answer(
        "I borrowed Rs 10,000 at 1% daily interest and received a legal notice.",
        plan,
        "",
        citations,
    )

    assert calls[0]["model"] == "sarvam-105b"
    assert calls[0]["reasoning_effort"] == "medium"
    assert "Section 138" not in str(calls[0]["user_prompt"])
    assert "Para 8(i)" not in str(calls[0]["user_prompt"])
    assert "What this means for you" in draft.draft_answer
    assert {claim.citation_ids[0] for claim in draft.claims} == {
        "Section 3, Usurious Loans Act, 1918",
        "Paragraph 2, RBI/2022-23/108 (Recovery Agents)",
    }


def test_legalfriend_voice_is_first_person_singular() -> None:
    assert (
        legal_advocate_agent._normalize_legalfriend_voice(
            "We need the notice. We're checking it and we will explain the result."
        )
        == "I need the notice. I'm checking it and I will explain the result."
    )


def test_valid_claim_citations_survive_an_invalid_claim() -> None:
    state = cast(
        graph.AgentState,
        {
            "english_query": "loan threat",
            "session_id": "partial-grounding",
            "agent_steps": 1,
            "citations": StubRetrieval().retrieve("loan threat"),
            "draft": LegalDraft(
                draft_answer="A partially supported answer.",
                claims=[
                    LegalClaim(
                        claim="Supported notice condition",
                        citation_ids=["Section 138, Negotiable Instruments Act, 1881"],
                        evidence_strength="direct",
                    ),
                    LegalClaim(
                        claim="Unsupported extra conclusion",
                        citation_ids=["missing-citation"],
                        evidence_strength="direct",
                    ),
                ],
                answer_scope="partial",
            ),
        },
    )

    assert graph._validated_draft_citation_ids(state) == {
        "Section 138, Negotiable Instruments Act, 1881"
    }


@pytest.mark.asyncio
async def test_text_stream_ends_with_unchanged_result_shape(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(logic.sarvam, "speak", lambda text, language: b"audio")
    logic.cached_simple_reply.cache_clear()
    chunks = [
        chunk
        async for chunk in logic.analyze_text_stream(
            query="Hi",
            session_id="text-result",
            memory=Memory(tmp_path / "result.sqlite"),
            retrieval=retrieval_stub(),
            target_lang_code="en-IN",
            source_lang_code="en-IN",
        )
    ]
    events = [decode_sse(chunk) for chunk in chunks]
    assert [event for event, payload in events] == [
        "agent_start",
        "agent_done",
        "agent_start",
        "agent_done",
        "result",
    ]
    result = events[-1][1]
    assert set(result) == {"summary_card", "citations", "advice"}
    advice = cast(dict[str, object], result["advice"])
    assert advice["audio_payload_b64"] == "YXVkaW8="


@pytest.mark.asyncio
async def test_text_stream_converts_input_failure_to_error_event(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_translation(
        text: str,
        target_lang_code: str,
        source_lang_code: str = "en-IN",
    ) -> str:
        raise PipelineError("translation unavailable", stage="translate_text")

    monkeypatch.setattr(logic.sarvam, "translate_text", fail_translation)
    stream: AsyncIterator[bytes] = logic.analyze_text_stream(
        query="ನಮಸ್ಕಾರ",
        session_id="text-error",
        memory=Memory(tmp_path / "error.sqlite"),
        retrieval=retrieval_stub(),
        target_lang_code="kn-IN",
        source_lang_code="kn-IN",
    )
    events = [decode_sse(chunk) async for chunk in stream]
    assert events == [
        (
            "error",
            {
                "stage": "translate_text",
                "message_user": "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again.",
            },
        )
    ]
