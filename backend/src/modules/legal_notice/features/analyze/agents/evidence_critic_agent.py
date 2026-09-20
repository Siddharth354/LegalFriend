import orjson

from src.core.api_errors import PipelineError
from src.modules.legal_notice.features.analyze.agents.parsing import (
    StructuredOutputError,
    complete_structured,
)
from src.modules.legal_notice.features.analyze.state import CritiqueDecision, LegalDraft

CRITIC_PROMPT: str = """Audit a legal draft against the supplied statutory excerpts.
Require every legal conclusion to be supported by an exact citation_string from the excerpts.
Treat the user's reported facts as allegations that do not need citations.
Allow clearly labelled practical safety, verification, evidence-preservation, and clarification steps without citations when they are not presented as legal requirements.
Mark the draft sufficient when it gives at least one materially useful supported legal point, removes unsupported legal conclusions, states important qualifications, and identifies what remains unanswered.
When relevant excerpts exist, reject a draft that only says more information is needed or lists practical steps without explaining at least one retrieved legal rule and placing its exact citation_string next to that explanation in draft_answer.
Do not reject a qualified partial answer merely because the excerpts cannot resolve the entire question.
Reject unsupported conclusions about criminal liability, extortion, enforceability, police authority, interest legality, or court procedure.
Reject treating a repayment demand, an unspecified threat, or a legal notice by itself as fear of injury or extortion.
Reject any claim that a recovery agent was assigned, required particulars were omitted, the lender is regulated, or the loan is digital unless the user's facts establish it. Permit the RBI rule only as a clearly conditional explanation when those facts are unknown.
Return strict JSON only.
Schema: {"sufficient":bool,"defects":[string],"repair_instructions":[string]}"""


def critique_draft(
    draft: LegalDraft,
    citations: list[dict[str, object]],
) -> CritiqueDecision:
    user_prompt: str = (
        f"Draft: {draft.model_dump_json()}\n\n"
        f"Statutory excerpts: {orjson.dumps(citations).decode()}"
    )
    try:
        return complete_structured(
            CRITIC_PROMPT,
            user_prompt,
            CritiqueDecision,
            max_tokens=2560,
        )
    except (StructuredOutputError, PipelineError):
        return CritiqueDecision(
            sufficient=False,
            defects=["Structured evidence critique unavailable"],
            repair_instructions=["Do not release unverified legal claims"],
        )
