from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel, Field


class IntentDecision(BaseModel):
    intent: Literal[
        "greeting",
        "capability",
        "legal_question",
        "urgent_safety",
        "clarification",
        "unsupported",
    ]
    needs_retrieval: bool
    needs_clarification: bool
    urgency: Literal["normal", "urgent"]
    reason: str


class CaseFacts(BaseModel):
    lender_name: str | None = None
    loan_amount: str | None = None
    interest_rate: str | None = None
    threat_type: str | None = None
    contact_timing: str | None = None
    missing_information: list[str] = Field(default_factory=list)


class LegalIssue(BaseModel):
    issue_id: str
    question: str
    retrieval_query: str


class IssuePlan(BaseModel):
    issues: list[LegalIssue] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class LegalClaim(BaseModel):
    claim: str
    citation_ids: list[str]
    evidence_strength: Literal["direct", "contextual", "insufficient"]


class LegalDraft(BaseModel):
    draft_answer: str
    claims: list[LegalClaim]
    missing_information: list[str] = Field(default_factory=list)
    answer_scope: str


class CritiqueDecision(BaseModel):
    sufficient: bool
    defects: list[str] = Field(default_factory=list)
    repair_instructions: list[str] = Field(default_factory=list)


class JudgeDecision(BaseModel):
    verdict: Literal["accept", "revise", "abstain"]
    final_answer: str | None = None
    revision_instructions: list[str] = Field(default_factory=list)
    abstention_reason: str | None = None
    citation_ids: list[str] = Field(default_factory=list)


class AgentState(TypedDict):
    english_query: str
    session_id: str
    agent_steps: int
    intent: NotRequired[IntentDecision]
    issue_plan: NotRequired[IssuePlan]
    facts: NotRequired[CaseFacts]
    citations: NotRequired[list[dict[str, object]]]
    draft: NotRequired[LegalDraft]
    critique: NotRequired[CritiqueDecision]
    judge: NotRequired[JudgeDecision]
    repair_instructions: NotRequired[list[str]]
    final_answer: NotRequired[str]
    final_citation_ids: NotRequired[list[str]]
    terminal_reason: NotRequired[str]
