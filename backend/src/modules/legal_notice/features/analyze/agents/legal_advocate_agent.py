import re

import orjson

from src.core.api_errors import PipelineError
from src.core.sarvam import client as sarvam
from src.modules.legal_notice.features.analyze.state import (
    IssuePlan,
    LegalClaim,
    LegalDraft,
)

ADVOCATE_PROMPT: str = """You are LegalFriend, a calm and conversational Indian legal first-responder helping a person who may be distressed.
Use only the supplied statutory excerpts for legal claims.
Write directly to the user in natural language. Do not return JSON. Do not expose retrieval terminology such as chunks, excerpts not found, evidence strength, or assessment scope.

Required response structure:
1. Start with one empathetic sentence that acknowledges the stress without sounding theatrical.
2. Give a short provisional outcome beginning with "What this means for you:". Answer what can be answered now, then clearly state the one or two facts preventing a final conclusion.
3. Address each actual concern in short, plain-language paragraphs. Do not repeat the issue questions as robotic headings.
4. Add "What you should do now:" with three to five concrete, safe steps such as preserving messages and call logs, requesting a written account statement, verifying the notice, and avoiding unverified payment channels. Label these as practical steps, not statutory commands.
5. End with "Please tell me:" followed by only the supplied follow-up questions.
Copy each supplied follow-up question exactly so the application can detect that it was answered conversationally without appending a duplicate question block.

Legal reasoning rules:
1. Put the exact citation_string beside every legal rule in this form: [Citation: exact citation_string]. Never translate or alter the citation string.
2. A 1% daily rate is about 365% yearly by simple arithmetic. Do not declare it automatically legal or illegal. If Section 3 of the Usurious Loans Act is supplied, explain that a court may examine whether interest is excessive and the transaction substantially unfair, subject to territorial and state-law applicability.
In the same paragraph, explicitly say that whether the central Act or an applicable state amendment operates in the user's location must be checked.
3. Do not infer that the lender is RBI-regulated, that the loan is digital, or that a recovery agent was assigned. Apply RBI rules conditionally until the lender identity establishes coverage.
Never say conduct is "likely against RBI rules" before coverage is established. Say it would breach the cited RBI rule if the lender is a covered regulated entity or its agent.
4. If midnight contact and RBI Paragraph 2 are supplied, give a clear outcome: for a covered regulated entity or its agent, a recovery call after 7:00 p.m. is prohibited.
5. A demand for overdue payment alone is not extortion. Explain BNS Section 308 conditionally unless the reported words establish fear of injury and dishonest inducement to deliver property. Use the statutory phrase "injury". Never narrow it to only physical injury.
6. Sending a legal notice is not itself proof that the demand is correct. Do not discuss cheque dishonour or Section 138 unless the user expressly mentions a cheque, dishonour, or Section 138.
7. Treat unclear speech such as "forced to chill" as ambiguous. Ask what was actually said. Do not silently rewrite it as jail, violence, or a death threat.
8. If the user reports immediate physical danger, give concise safety guidance first. Otherwise, do not turn a vague payment demand into an emergency.
9. Never say "no targeted statutory excerpt was retrieved". Explain the practical limitation in human language.
10. Be concise, warm, and decisive. The user should finish knowing what is provisionally lawful or prohibited, what remains uncertain, and what to do next.
11. Use first-person singular "I" when speaking as LegalFriend. Never refer to LegalFriend as "we".
12. Do not advise the user simply to stop answering calls. Recommend asking the lender to communicate in writing and preserving call records and messages."""

DISTRESS_QUERY_TERMS: tuple[str, ...] = (
    "threat",
    "kill",
    "hurt",
    "harass",
    "force",
    "jail",
    "chill",
)


def _normalize_legalfriend_voice(answer: str) -> str:
    normalized: str = re.sub(r"\b[Ww]e're\b", "I'm", answer)
    normalized = re.sub(r"\b[Ww]e've\b", "I've", normalized)
    normalized = re.sub(r"\b[Ww]e'll\b", "I'll", normalized)
    return re.sub(r"\b[Ww]e\b", "I", normalized)


def _reasoning_evidence(
    english_query: str,
    citations: list[dict[str, object]],
) -> list[dict[str, object]]:
    lowered_query: str = english_query.lower()
    mentions_cheque: bool = any(
        term in lowered_query
        for term in ("cheque", "check bounce", "dishonour", "section 138")
    )
    mentions_distress: bool = any(
        term in lowered_query for term in DISTRESS_QUERY_TERMS
    )
    mentions_digital_loan: bool = any(
        term in lowered_query for term in ("app", "digital", "online", "platform")
    )
    selected: list[dict[str, object]] = []
    for citation in citations:
        citation_string: str = str(citation.get("citation_string", ""))
        include: bool = citation_string.startswith(
            (
                "Paragraph 2, RBI/2022-23/108",
                "Paragraphs 5-6, RBI/2022-23/108",
                "Section 3, Usurious Loans Act",
                "Sections 1-2, Usurious Loans Act",
            )
        )
        if mentions_digital_loan and citation_string.startswith(
            "Para 8(i), RBI (Digital Lending)"
        ):
            include = True
        if mentions_distress and citation_string.startswith("Section 308(1), BNS"):
            include = True
        if mentions_cheque and citation_string.startswith("Section 138,"):
            include = True
        if include:
            selected.append(
                {
                    "act": citation.get("act"),
                    "citation_string": citation_string,
                    "content": citation.get("content"),
                    "matched_issue_ids": citation.get("matched_issue_ids", []),
                }
            )
    return selected


def _citation_for_issue(
    citations: list[dict[str, object]],
    issue_id: str,
    required_text: tuple[str, ...],
    required_citation_prefix: str | None = None,
) -> dict[str, object] | None:
    for citation in citations:
        matched_issue_ids = citation.get("matched_issue_ids", [])
        content: str = str(citation.get("content", "")).lower()
        citation_string: str = str(citation.get("citation_string", ""))
        if (
            isinstance(matched_issue_ids, list)
            and issue_id in matched_issue_ids
            and any(text in content for text in required_text)
            and (
                required_citation_prefix is None
                or citation_string.startswith(required_citation_prefix)
            )
        ):
            return citation
    return None


def _fallback_grounded_draft(
    english_query: str,
    issue_plan: IssuePlan,
    citations: list[dict[str, object]],
) -> LegalDraft:
    mentions_cheque: bool = any(
        term in english_query.lower()
        for term in ("cheque", "check bounce", "dishonour", "section 138")
    )
    evidence_by_issue: dict[str, tuple[dict[str, object] | None, str]] = {
        "recovery_contact_hours": (
            _citation_for_issue(citations, "recovery_intimidation", ("after 7:00",)),
            "If the lender is an RBI-regulated entity covered by this circular, calling a borrower at midnight for recovery is prohibited under this rule because midnight is after 7:00 p.m. The rule also prohibits calls before 8:00 a.m.",
        ),
        "recovery_intimidation": (
            _citation_for_issue(
                citations,
                "recovery_intimidation",
                ("intimidation", "harassment"),
            ),
            "If the lender is covered by the RBI circular, it and its recovery agents must not use intimidation, harassment, or threatening calls. A demand for overdue payment alone does not establish intimidation, so the exact words and conduct matter.",
        ),
        "criminal_threat_or_extortion": (
            _citation_for_issue(
                citations,
                "criminal_threat_or_extortion",
                ("commits extortion",),
            ),
            "BNS extortion requires intentionally creating fear of injury and thereby dishonestly inducing delivery of property. A bare statement that payment is due is not enough by itself. The exact threat is required. If there is an immediate threat of physical harm, move to safety and contact 112 or local police as practical safety guidance.",
        ),
        "interest_and_disclosure": (
            _citation_for_issue(
                citations,
                "interest_and_disclosure",
                ("interest is excessive", "substantially unfair"),
                required_citation_prefix="Section 3, Usurious Loans Act",
            ),
            "One percent per day is approximately 365% per year by simple arithmetic, without compounding. That does not make the rate automatically legal or illegal. A court may examine whether the interest is excessive and the transaction substantially unfair, subject to the Act's local applicability. Your State, lender identity, agreement, and complete charge breakdown are needed for a firmer answer.",
        ),
        "legal_notice": (
            _citation_for_issue(
                citations,
                "legal_notice",
                ("dishonour of cheque",),
                required_citation_prefix="Section 138,",
            )
            if mentions_cheque
            else None,
            (
                "Sending a legal notice is not by itself unlawful and does not prove that its demand is valid. Because you did not mention a dishonoured cheque, I would not apply Section 138 merely from the words 'legal notice'. The notice must be reviewed before advising you about its deadline or legal effect."
            ),
        ),
    }
    sections: list[str] = [
        "I understand why this feels stressful, especially when payment is being demanded late at night.",
        (
            "What this means for you: do not ignore the notice, but do not assume that every demand in it is legally correct. A missed payment can permit lawful recovery steps. It does not permit prohibited recovery conduct, and a 1% daily rate needs legal review rather than a yes-or-no guess."
        ),
    ]
    claims: list[LegalClaim] = []
    missing_information: list[str] = []
    for index, issue in enumerate(issue_plan.issues, start=1):
        citation, explanation = evidence_by_issue.get(issue.issue_id, (None, ""))
        if citation is None:
            if explanation:
                sections.append(f"{index}. {explanation}")
            else:
                missing_information.append(issue.question)
            continue
        citation_string: str = str(citation.get("citation_string", ""))
        sections.append(f"{index}. {issue.question}\n{explanation} ({citation_string})")
        claims.append(
            LegalClaim(
                claim=explanation,
                citation_ids=[citation_string],
                evidence_strength="direct",
            )
        )
    sections.append(
        "What you should do now:\n"
        "1. Save the notice, messages, call logs, recordings, and payment receipts.\n"
        "2. Ask for a written loan statement showing principal, interest, penalties, and the amount now claimed.\n"
        "3. Verify the sender and pay only through a verified lender channel, not an unknown personal account.\n"
        "4. Do not sign a new document or issue a cheque only because someone is pressuring you on a call."
    )
    return LegalDraft(
        draft_answer="\n\n".join(sections),
        claims=claims,
        missing_information=missing_information,
        answer_scope="deterministic grounded fallback",
    )


def draft_legal_answer(
    english_query: str,
    issue_plan: IssuePlan,
    history: str,
    citations: list[dict[str, object]],
) -> LegalDraft:
    reasoning_evidence: list[dict[str, object]] = _reasoning_evidence(
        english_query,
        citations,
    )
    if not reasoning_evidence:
        return _fallback_grounded_draft(english_query, issue_plan, citations)
    evidence: str = orjson.dumps(reasoning_evidence).decode()
    user_prompt: str = (
        f"Question: {english_query}\n\nIssue Plan: {issue_plan.model_dump_json()}\n\n"
        f"Recent conversation: {history or 'none'}\n\n"
        f"Authoritative evidence: {evidence}"
    )
    try:
        answer: str = sarvam.chat_complete(
            ADVOCATE_PROMPT,
            user_prompt,
            model="sarvam-105b",
            max_tokens=4096,
            reasoning_effort="medium",
        )
    except PipelineError:
        return _fallback_grounded_draft(english_query, issue_plan, citations)
    answer = _normalize_legalfriend_voice(answer)
    citation_ids: list[str] = [
        str(citation["citation_string"])
        for citation in reasoning_evidence
        if str(citation["citation_string"]) in answer
    ]
    required_sections: tuple[str, ...] = (
        "What this means for you:",
        "What you should do now:",
        "Please tell me:",
    )
    names_covered_lender_class: bool = any(
        term in answer.lower()
        for term in ("nbfc", "commercial bank", "regulated entities like banks")
    )
    applicability_citation: str = "Paragraphs 5-6, RBI/2022-23/108 (Applicability)"
    missing_applicability_citation: bool = (
        names_covered_lender_class
        and any(
            citation.get("citation_string") == applicability_citation
            for citation in reasoning_evidence
        )
        and applicability_citation not in answer
    )
    if (
        not citation_ids
        or not all(section in answer for section in required_sections)
        or missing_applicability_citation
    ):
        return _fallback_grounded_draft(english_query, issue_plan, citations)
    return LegalDraft(
        draft_answer=answer,
        claims=[
            LegalClaim(
                claim="Legal rule stated in the conversational answer.",
                citation_ids=[citation_id],
                evidence_strength="direct",
            )
            for citation_id in citation_ids
        ],
        answer_scope="sarvam-105b conversational reasoning",
    )
