from src.core.api_errors import PipelineError
from src.modules.legal_notice.features.analyze.agents.parsing import (
    StructuredOutputError,
    complete_structured,
)
from src.modules.legal_notice.features.analyze.state import IssuePlan, LegalIssue

ISSUE_PLANNER_PROMPT: str = """Decompose an Indian loan-recovery question into independent legal issues for retrieval.
Create one issue per distinct concern, such as recovery contact hours, harassment or intimidation, threat of death or injury, interest and disclosure, legal-notice validity, cheque dishonour, and lender applicability.
Do not answer the legal question. Produce concise retrieval queries containing the conduct, governing institution or statute, and legal concept. Do not put all concerns into one broad query.
Ask only follow-up questions whose answers would change applicability or the conclusion. Always ask for the lender or app identity when RBI applicability is unknown. Ask for the exact threatening words when a threat is vague. Ask for the notice image or cited section when notice validity is raised without its contents.
Return at most five issues and four follow-up questions.
Return strict JSON only.
Schema: {"issues":[{"issue_id":string,"question":string,"retrieval_query":string}],"follow_up_questions":[string]}"""

FAST_PATH_TERMS: tuple[str, ...] = (
    "loan",
    "lender",
    "borrow",
    "interest",
    "recovery",
    "threat",
    "harass",
    "notice",
    "cheque",
    "midnight",
    "at night",
    "force",
    "jail",
    "chill",
)

DISTRESS_TERMS: tuple[str, ...] = (
    "threat",
    "kill",
    "hurt",
    "harass",
    "force",
    "jail",
    "chill",
)


def _fallback_plan(english_query: str) -> IssuePlan:
    lowered_query: str = english_query.lower()
    issues: list[LegalIssue] = []
    if any(term in lowered_query for term in ("midnight", "at night", "call")):
        issues.append(
            LegalIssue(
                issue_id="recovery_contact_hours",
                question="Was the recovery contact made during prohibited hours?",
                retrieval_query=(
                    "RBI/2022-23/108 paragraph 2 calls after 7 p.m. paragraph 5 "
                    "applicability commercial banks NBFC regulated entity"
                ),
            )
        )
    if any(term in lowered_query for term in DISTRESS_TERMS):
        issues.append(
            LegalIssue(
                issue_id="recovery_intimidation",
                question="What RBI rules govern threatening or intimidating recovery conduct?",
                retrieval_query=(
                    "RBI recovery agents intimidation harassment threatening calls"
                ),
            )
        )
        issues.append(
            LegalIssue(
                issue_id="criminal_threat_or_extortion",
                question=(
                    "Does the reported payment threat meet a BNS threat or extortion test?"
                ),
                retrieval_query=(
                    "BNS extortion intentionally putting person in fear of injury death "
                    "demand money deliver property"
                ),
            )
        )
    if any(term in lowered_query for term in ("interest", "%", "rate")):
        issues.append(
            LegalIssue(
                issue_id="interest_and_disclosure",
                question="What rules govern the stated interest and its disclosure?",
                retrieval_query=(
                    "Usurious Loans Act Section 3 excessive interest substantially "
                    "unfair court reopen transaction RBI APR Key Fact Statement"
                ),
            )
        )
    if "notice" in lowered_query:
        issues.append(
            LegalIssue(
                issue_id="legal_notice",
                question="Can the legal notice be assessed from the available facts?",
                retrieval_query=(
                    "Indian loan legal notice cheque dishonour Section 138 notice "
                    "payment deadline statutory conditions"
                ),
            )
        )
    if not issues:
        issues.append(
            LegalIssue(
                issue_id="loan_recovery",
                question="What law governs the reported loan-recovery conduct?",
                retrieval_query=english_query,
            )
        )
    follow_up_questions: list[str] = [
        "What is the exact name of the lender or loan app, and what type of lender is it?",
    ]
    if any(term in lowered_query for term in DISTRESS_TERMS):
        follow_up_questions.append(
            "What exact words, messages, or actions were used to threaten you?"
        )
    if "notice" in lowered_query:
        follow_up_questions.append(
            "Can you share the notice image or its cited section, issuer, amount, and deadline?"
        )
    return IssuePlan(
        issues=issues[:5],
        follow_up_questions=follow_up_questions[:4],
    )


def plan_legal_issues(english_query: str, recent_history: str) -> IssuePlan:
    normalized_query: str = english_query.lower()
    if any(term in normalized_query for term in FAST_PATH_TERMS):
        return _fallback_plan(english_query)
    user_prompt: str = (
        f"Recent conversation:\n{recent_history or 'none'}\n\n"
        f"Current question:\n{english_query}"
    )
    try:
        plan: IssuePlan = complete_structured(
            ISSUE_PLANNER_PROMPT,
            user_prompt,
            IssuePlan,
            max_tokens=1536,
            model="sarvam-105b",
        )
        if not plan.issues:
            return _fallback_plan(english_query)
        return plan
    except (StructuredOutputError, PipelineError):
        return _fallback_plan(english_query)
