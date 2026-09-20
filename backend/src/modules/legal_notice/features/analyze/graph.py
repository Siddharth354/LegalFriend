import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Literal, cast

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from src.core.logger import get_logger
from src.core.memory import Memory
from src.modules.legal_notice.features.analyze.agents import (
    classify_intent,
    draft_legal_answer,
    plan_legal_issues,
)
from src.modules.legal_notice.features.analyze.state import (
    AgentState,
    IntentDecision,
    IssuePlan,
    LegalDraft,
)
from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter

logger = get_logger(__name__)

PER_ISSUE_RETRIEVAL_TOP_K: int = 3
MAX_EVIDENCE_CHUNKS: int = 15
AgentNodeId = Literal[
    "intent",
    "direct",
    "planner",
    "retrieval",
    "advocate",
    "safe",
]
AGENT_NODE_IDS: frozenset[str] = frozenset(
    {
        "intent",
        "direct",
        "planner",
        "retrieval",
        "advocate",
        "safe",
    }
)
RETRIEVAL_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"(?:₹|\b(?:rs\.?|inr)\s*)\d[\d,]*(?:\.\d+)?(?:\s*rupees?)?\b"
    r"|\b\d[\d,]*(?:\.\d+)?\s*rupees?\b"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent\b|per cent\b)"
    r"|\b\d{1,3}(?:,\d{3})+\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AgentGraphOutcome:
    answer: str
    citations: list[dict[str, object]]
    terminal_reason: str


@dataclass(frozen=True)
class AgentNodeEvent:
    event: Literal["agent_start", "agent_done"]
    node: AgentNodeId
    detail: str | None = None


AgentGraphStreamItem = AgentNodeEvent | AgentGraphOutcome


def _history(memory: Memory, session_id: str) -> str:
    turns = memory.recent_turns(session_id, limit=6)
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in turns)


def _direct_response(intent: str) -> str:
    responses: dict[str, str] = {
        "greeting": "Hello. I can help with loan notices, lender threats, next steps, and the legal excerpts behind an answer. What would you like to understand?",
        "capability": "I can explain loan notices and lender threats, identify next steps, and show relevant legal excerpts. I provide legal information, not a replacement for a lawyer or emergency services.",
        "urgent_safety": "If you are in immediate danger, move to a safe place and contact local emergency services or a trusted person now. I can help you document the legal issue after you are safe.",
        "clarification": "Please share the lender's threat, the amount claimed, and whether you received a written notice so I can assess the issue safely.",
        "unsupported": "I can help with Indian loan-notice and lender-threat questions. Please ask about the notice or threat you received.",
    }
    return responses[intent]


def _safe_abstention(reason: str) -> str:
    return (
        "I do not have enough supported legal evidence to answer that reliably. "
        "Please share the written notice, the lender's exact threat, and any relevant payment or cheque details."
    )


def _retrieval_query(english_query: str) -> str:
    return " ".join(RETRIEVAL_NUMBER_PATTERN.sub(" ", english_query).split())


def _retrieve_issue_citations(
    retrieval: RetrievalAdapter,
    issue_plan: IssuePlan,
) -> list[dict[str, object]]:
    retrieval_queries: list[str] = [
        _retrieval_query(issue.retrieval_query) for issue in issue_plan.issues
    ]
    for issue, retrieval_query in zip(
        issue_plan.issues,
        retrieval_queries,
        strict=True,
    ):
        logger.info(
            "retrieval_query",
            issue_id=issue.issue_id,
            issue_question=issue.question,
            retrieval_query=retrieval_query,
            top_k=PER_ISSUE_RETRIEVAL_TOP_K,
        )
    started_at: float = perf_counter()
    results_by_issue: list[list[dict[str, object]]] = retrieval.retrieve_many(
        retrieval_queries,
        top_k=PER_ISSUE_RETRIEVAL_TOP_K,
    )
    merged_citations: dict[str, dict[str, object]] = {}
    issue_results = list(zip(issue_plan.issues, results_by_issue, strict=True))
    for result_index in range(PER_ISSUE_RETRIEVAL_TOP_K):
        for issue, citations in issue_results:
            if result_index >= len(citations):
                continue
            citation = citations[result_index]
            rank = result_index + 1
            score_value: object = citation.get("score")
            score: float | None = (
                float(score_value) if isinstance(score_value, int | float) else None
            )
            logger.info(
                "retrieved_chunk",
                issue_id=issue.issue_id,
                rank=rank,
                score=score,
                chunk_id=str(citation.get("chunk_id", "")),
                citation_string=str(citation.get("citation_string", "")),
                act=str(citation.get("act", "")),
                content=str(citation.get("content", "")),
            )
            chunk_id: str = str(citation.get("chunk_id", ""))
            existing: dict[str, object] | None = merged_citations.get(chunk_id)
            if existing is None:
                enriched: dict[str, object] = {
                    **citation,
                    "matched_issue_ids": [issue.issue_id],
                    "matched_issue_questions": [issue.question],
                }
                merged_citations[chunk_id] = enriched
                continue
            matched_ids = cast(list[str], existing["matched_issue_ids"])
            matched_questions = cast(
                list[str],
                existing["matched_issue_questions"],
            )
            if issue.issue_id not in matched_ids:
                matched_ids.append(issue.issue_id)
                matched_questions.append(issue.question)
    citations: list[dict[str, object]] = list(merged_citations.values())[
        :MAX_EVIDENCE_CHUNKS
    ]
    logger.info(
        "parallel_retrieval_complete",
        issue_count=len(issue_plan.issues),
        citation_count=len(citations),
        duration_ms=round((perf_counter() - started_at) * 1000, 1),
    )
    return citations


def _citation_id_mapping(state: AgentState) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for citation in state.get("citations", []):
        citation_string: str = str(citation.get("citation_string", "")).strip()
        if not citation_string:
            continue
        mapping[citation_string] = citation_string
        chunk_id: str = str(citation.get("chunk_id", "")).strip()
        if chunk_id:
            mapping[chunk_id] = citation_string
    return mapping


def _validated_draft_citation_ids(state: AgentState) -> set[str]:
    draft: LegalDraft | None = state.get("draft")
    if draft is None:
        return set()
    mapping: dict[str, str] = _citation_id_mapping(state)
    resolved_ids: set[str] = set()
    invalid_claims: list[dict[str, object]] = []
    for claim in draft.claims:
        if claim.evidence_strength == "insufficient":
            continue
        if not claim.citation_ids or any(
            citation_id not in mapping for citation_id in claim.citation_ids
        ):
            invalid_claims.append(
                {
                    "claim": claim.claim,
                    "citation_ids": claim.citation_ids,
                    "reason": "citation_not_retrieved",
                }
            )
            continue
        resolved_ids.update(mapping[citation_id] for citation_id in claim.citation_ids)
    logger.info(
        "draft_citation_validation",
        valid_citation_ids=sorted(resolved_ids),
        invalid_claims=invalid_claims,
    )
    return resolved_ids


def _append_follow_up_questions(answer: str, issue_plan: IssuePlan) -> str:
    missing_questions: list[str] = [
        question
        for question in issue_plan.follow_up_questions
        if question.lower() not in answer.lower()
    ]
    if not missing_questions:
        return answer
    question_lines: str = "\n".join(
        f"{index}. {question}"
        for index, question in enumerate(missing_questions, start=1)
    )
    return f"{answer.rstrip()}\n\nPlease tell me:\n{question_lines}"


def build_agent_graph(memory: Memory, retrieval: RetrievalAdapter):
    def intent_node(state: AgentState) -> dict[str, object]:
        started_at: float = perf_counter()
        next_steps: int = state["agent_steps"] + 1
        decision = classify_intent(
            state["english_query"],
            _history(memory, state["session_id"]),
        )
        logger.info(
            "agent_node",
            node="intent",
            intent=decision.intent,
            agent_steps=next_steps,
            duration_ms=round((perf_counter() - started_at) * 1000, 1),
        )
        return {"agent_steps": next_steps, "intent": decision}

    def direct_response_node(state: AgentState) -> dict[str, object]:
        intent = state["intent"]
        return {
            "final_answer": _direct_response(intent.intent),
            "final_citation_ids": [],
            "terminal_reason": intent.intent,
        }

    def planner_node(state: AgentState) -> dict[str, object]:
        started_at: float = perf_counter()
        next_steps: int = state["agent_steps"] + 1
        issue_plan: IssuePlan = plan_legal_issues(
            state["english_query"],
            _history(memory, state["session_id"]),
        )
        logger.info(
            "agent_node",
            node="planner",
            agent_steps=next_steps,
            issue_count=len(issue_plan.issues),
            issues=[issue.model_dump() for issue in issue_plan.issues],
            follow_up_questions=issue_plan.follow_up_questions,
            duration_ms=round((perf_counter() - started_at) * 1000, 1),
        )
        return {"agent_steps": next_steps, "issue_plan": issue_plan}

    def retrieval_node(state: AgentState) -> dict[str, object]:
        citations: list[dict[str, object]] = _retrieve_issue_citations(
            retrieval,
            state["issue_plan"],
        )
        logger.info("agent_node", node="retrieval", citation_count=len(citations))
        return {"citations": citations}

    def advocate_node(state: AgentState) -> dict[str, object]:
        started_at: float = perf_counter()
        next_steps: int = state["agent_steps"] + 1
        draft: LegalDraft = draft_legal_answer(
            state["english_query"],
            state["issue_plan"],
            _history(memory, state["session_id"]),
            state["citations"],
        )
        candidate_state: AgentState = {**state, "draft": draft}
        citation_ids: set[str] = _validated_draft_citation_ids(candidate_state)
        final_answer: str = _append_follow_up_questions(
            draft.draft_answer,
            state["issue_plan"],
        )
        logger.info(
            "agent_node",
            node="advocate",
            agent_steps=next_steps,
            claim_count=len(draft.claims),
            answer_scope=draft.answer_scope,
            grounded=bool(citation_ids),
            duration_ms=round((perf_counter() - started_at) * 1000, 1),
        )
        return {
            "agent_steps": next_steps,
            "draft": draft,
            "final_answer": final_answer if citation_ids else "",
            "final_citation_ids": list(citation_ids),
            "terminal_reason": "accepted" if citation_ids else "evidence_insufficient",
        }

    def safe_abstention_node(state: AgentState) -> dict[str, object]:
        reason: str = state.get("terminal_reason", "evidence_insufficient")
        return {
            "final_answer": _safe_abstention(reason),
            "final_citation_ids": [],
            "terminal_reason": reason,
        }

    def route_after_intent(state: AgentState) -> Literal["direct", "planner"]:
        if state["intent"].intent == "legal_question":
            return "planner"
        return "direct"

    def route_after_advocate(state: AgentState) -> Literal["end", "safe"]:
        if state.get("final_answer") and state.get("final_citation_ids"):
            return "end"
        return "safe"

    graph = StateGraph(cast(type[BaseModel], AgentState))
    graph.add_node("intent", intent_node)
    graph.add_node("direct", direct_response_node)
    graph.add_node("planner", planner_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("advocate", advocate_node)
    graph.add_node("safe", safe_abstention_node)
    graph.add_edge(START, "intent")
    graph.add_conditional_edges(
        "intent",
        route_after_intent,
        {"direct": "direct", "planner": "planner"},
    )
    graph.add_edge("direct", END)
    graph.add_edge("planner", "retrieval")
    graph.add_edge("retrieval", "advocate")
    graph.add_conditional_edges(
        "advocate",
        route_after_advocate,
        {"end": END, "safe": "safe"},
    )
    graph.add_edge("safe", END)
    return graph.compile()


def _initial_state(english_query: str, session_id: str) -> AgentState:
    return {
        "english_query": english_query,
        "session_id": session_id,
        "agent_steps": 0,
    }


def _node_detail(node: AgentNodeId, delta: dict[str, object]) -> str | None:
    if node == "intent":
        decision = delta.get("intent")
        if isinstance(decision, IntentDecision):
            return f"Classified as {decision.intent}"
    if node == "direct":
        return "Prepared direct response"
    if node == "planner":
        plan = delta.get("issue_plan")
        if isinstance(plan, IssuePlan):
            return f"Planned {len(plan.issues)} legal issues"
    if node == "retrieval":
        citations = delta.get("citations")
        if isinstance(citations, list):
            return f"Retrieved {len(citations)} citations"
    if node == "advocate":
        return "Prepared and validated the issue-by-issue answer"
    if node == "safe":
        return "Prepared safe response"
    return None


def _outcome_from_state(
    output: AgentState,
    session_id: str,
    memory: Memory,
) -> AgentGraphOutcome:
    answer: str = output.get("final_answer", "")
    citation_ids: set[str] = set(output.get("final_citation_ids", []))
    terminal_reason: str = output.get("terminal_reason", "accepted")
    citations: list[dict[str, object]] = [
        citation
        for citation in output.get("citations", [])
        if str(citation.get("citation_string")) in citation_ids
    ]
    memory.add_turn(session_id, "assistant", answer)
    return AgentGraphOutcome(
        answer=answer,
        citations=citations,
        terminal_reason=terminal_reason,
    )


def run_agent_graph(
    english_query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
) -> AgentGraphOutcome:
    memory.ensure_session(session_id)
    memory.add_turn(session_id, "user", english_query)
    graph = build_agent_graph(memory, retrieval)
    initial_state = _initial_state(english_query, session_id)
    output = cast(AgentState, graph.invoke(initial_state))
    return _outcome_from_state(output, session_id, memory)


async def stream_agent_graph(
    english_query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
) -> AsyncIterator[AgentGraphStreamItem]:
    memory.ensure_session(session_id)
    memory.add_turn(session_id, "user", english_query)
    graph = build_agent_graph(memory, retrieval)
    output = _initial_state(english_query, session_id)
    async for stream_event in graph.astream(
        output,
        stream_mode="tasks",
        version="v2",
    ):
        event_data = cast(dict[str, object], stream_event)
        task_data = cast(dict[str, object], event_data.get("data", {}))
        node_name = str(task_data.get("name", ""))
        if node_name not in AGENT_NODE_IDS:
            continue
        node = cast(AgentNodeId, node_name)
        if "input" in task_data:
            yield AgentNodeEvent(event="agent_start", node=node)
            continue
        if task_data.get("error") is not None:
            raise RuntimeError(str(task_data["error"]))
        result = task_data.get("result")
        if isinstance(result, dict):
            delta = cast(dict[str, object], result)
            output.update(cast(AgentState, delta))
            yield AgentNodeEvent(
                event="agent_done",
                node=node,
                detail=_node_detail(node, delta),
            )
    yield _outcome_from_state(output, session_id, memory)
