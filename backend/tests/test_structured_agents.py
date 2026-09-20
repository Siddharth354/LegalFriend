from pytest import MonkeyPatch

from src.modules.legal_notice.features.analyze.agents import final_judge_agent, parsing
from src.modules.legal_notice.features.analyze.agents.evidence_critic_agent import (
    critique_draft,
)
from src.modules.legal_notice.features.analyze.state import (
    CaseFacts,
    CritiqueDecision,
    JudgeDecision,
    LegalDraft,
)


def test_structured_completion_repairs_one_invalid_response(
    monkeypatch: MonkeyPatch,
) -> None:
    responses: list[str] = [
        "invalid",
        '{"lender_name":null,"loan_amount":"Rs 50,000","threat_type":null,"missing_information":[]}',
    ]

    def chat_complete(
        system_prompt: str,
        user_prompt: str,
        model: str = "sarvam-105b",
        max_tokens: int = 2048,
    ) -> str:
        return responses.pop(0)

    monkeypatch.setattr(parsing.sarvam, "chat_complete", chat_complete)
    result = parsing.complete_structured(
        "Extract facts",
        "Cheque notice for Rs 50,000",
        CaseFacts,
        max_tokens=768,
    )
    assert result.loan_amount == "Rs 50,000"
    assert responses == []


def test_critic_falls_back_after_bounded_invalid_responses(
    monkeypatch: MonkeyPatch,
) -> None:
    call_count: int = 0

    def chat_complete(
        system_prompt: str,
        user_prompt: str,
        model: str = "sarvam-105b",
        max_tokens: int = 2048,
    ) -> str:
        nonlocal call_count
        call_count += 1
        return "invalid"

    monkeypatch.setattr(parsing.sarvam, "chat_complete", chat_complete)
    decision = critique_draft(
        LegalDraft(
            draft_answer="Draft",
            claims=[],
            answer_scope="test",
        ),
        [],
    )
    assert call_count == parsing.STRUCTURED_OUTPUT_ATTEMPTS
    assert decision.sufficient is False
    assert decision.repair_instructions == ["Do not release unverified legal claims"]


def test_parser_extracts_json_from_surrounding_text() -> None:
    result = parsing.parse_json_response(
        'Result:\n```json\n{"lender_name":null,"loan_amount":null,"threat_type":null,"missing_information":[]}\n```',
        CaseFacts,
    )
    assert result == CaseFacts()


def test_case_facts_allow_rate_without_principal_amount() -> None:
    facts = CaseFacts(interest_rate="1% per day")
    assert facts.loan_amount is None
    assert facts.interest_rate == "1% per day"


def test_judge_rewrites_immediately_instead_of_requesting_another_draft(
    monkeypatch: MonkeyPatch,
) -> None:
    decisions: list[JudgeDecision] = [
        JudgeDecision(
            verdict="revise",
            revision_instructions=["Remove the unsupported rate conclusion."],
        ),
        JudgeDecision(
            verdict="accept",
            final_answer="The recovery rule applies to an assigned agent.",
            citation_ids=["RBI Digital Lending Directions, 2025, Paragraph 8.2(v)"],
        ),
    ]
    system_prompts: list[str] = []

    def complete_structured(
        system_prompt: str,
        user_prompt: str,
        schema: type[JudgeDecision],
        max_tokens: int,
    ) -> JudgeDecision:
        system_prompts.append(system_prompt)
        return decisions.pop(0)

    monkeypatch.setattr(final_judge_agent, "complete_structured", complete_structured)
    result = final_judge_agent.judge_draft(
        LegalDraft(
            draft_answer="The rate is illegal and the agent must be identified.",
            claims=[],
            answer_scope="loan recovery",
        ),
        CritiqueDecision(sufficient=True),
        [],
    )

    assert result.verdict == "accept"
    assert len(system_prompts) == 2
    assert "Do not return revise" in system_prompts[1]
