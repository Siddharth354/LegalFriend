import orjson

from src.core.api_errors import PipelineError
from src.core.logger import get_logger
from src.modules.legal_notice.features.analyze.agents.parsing import (
    StructuredOutputError,
    complete_structured,
)
from src.modules.legal_notice.features.analyze.state import (
    CritiqueDecision,
    JudgeDecision,
    LegalDraft,
)

logger = get_logger(__name__)

JUDGE_PROMPT: str = """Make the final release decision for a citation-grounded Indian legal answer.
Use exact citation_string values from the excerpts in citation_ids. Never use chunk_id values.
When the critique is sufficient, accept only when every released legal claim is supported.
When the critique identifies defects but at least one materially useful supported claim remains, rewrite the final answer to remove every defective claim and accept the grounded subset.
An accepted final_answer must itself explain at least one materially useful retrieved legal rule and place the rule's exact citation_string next to that explanation. Returning citation_ids without explaining the cited law in final_answer is not sufficient.
Never accept a generic answer that only says information is missing when the excerpts support a conditional legal explanation. Give the conditional rule first, then identify the exact missing fact needed to apply it.
Preserve the draft's "To complete the assessment" questions in final_answer. A partial legal answer must end with the focused questions needed to determine applicability and assess the notice.
Do not introduce a legal claim that is absent from the grounded draft claims. Never state that an interest rate is illegal or may be illegal unless a supplied excerpt expressly establishes the applicable rate limit.
Do not treat a demand to repay a missed instalment, an unspecified threat, or a legal notice by itself as fear of injury or extortion. State the cited extortion test conditionally and ask for the exact words or conduct used as the threat.
Do not infer that a recovery agent was assigned, required agent particulars were omitted, the lender is regulated, or the loan is digital. State an RBI recovery-agent rule only with those applicability conditions when the user's facts do not establish them.
The rewritten answer may include clearly labelled practical safety, verification, evidence-preservation, and clarification steps without citations, but must not present them as legal requirements.
State qualifications such as whether the RBI excerpt applies only to digital lending or an assigned recovery agent.
Abstain only when no materially useful supported legal claim remains. Choose revise only when the answer cannot be safely rewritten during this review.
Return strict JSON only.
Schema: {"verdict":"accept|revise|abstain","final_answer":string|null,"revision_instructions":[string],"abstention_reason":string|null,"citation_ids":[string]}"""

FINALIZE_NOW_INSTRUCTION: str = """No additional Advocate drafting pass is available.
Perform the safe rewrite during this review. Return accept with a final_answer containing only materially useful supported claims and exact citation_string values, or return abstain if no supported claim remains.
Do not return revise."""


def judge_draft(
    draft: LegalDraft,
    critique: CritiqueDecision,
    citations: list[dict[str, object]],
) -> JudgeDecision:
    user_prompt: str = (
        f"Draft: {draft.model_dump_json()}\n\nCritique: {critique.model_dump_json()}\n\n"
        f"Statutory excerpts: {orjson.dumps(citations).decode()}"
    )
    try:
        decision: JudgeDecision = complete_structured(
            JUDGE_PROMPT,
            user_prompt,
            JudgeDecision,
            max_tokens=3072,
        )
        if decision.verdict != "revise":
            return decision
        logger.info(
            "judge_self_revision",
            revision_instructions=decision.revision_instructions,
        )
        final_decision: JudgeDecision = complete_structured(
            f"{JUDGE_PROMPT}\n{FINALIZE_NOW_INSTRUCTION}",
            (f"{user_prompt}\n\nPrevious judge decision: {decision.model_dump_json()}"),
            JudgeDecision,
            max_tokens=3072,
        )
        if final_decision.verdict == "revise":
            return JudgeDecision(
                verdict="abstain",
                abstention_reason="Final review did not produce a releasable answer",
            )
        return final_decision
    except (StructuredOutputError, PipelineError):
        return JudgeDecision(
            verdict="abstain",
            abstention_reason="Structured final review unavailable",
        )
