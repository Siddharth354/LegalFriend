from src.core.api_errors import PipelineError
from src.modules.legal_notice.features.analyze.agents.parsing import (
    StructuredOutputError,
    complete_structured,
)
from src.modules.legal_notice.features.analyze.state import IntentDecision

INTENT_PROMPT: str = """Classify the user message for an Indian legal first-responder.
Return strict JSON only.
Valid intents: greeting, capability, legal_question, urgent_safety, clarification, unsupported.
Use greeting for hello or small talk. Use capability for asking what the product can do.
Use urgent_safety for immediate threats of violence, self-harm, or danger.
Use clarification when a legal question lacks the minimum facts needed to identify the issue.
Only legal_question may set needs_retrieval to true.
Schema: {"intent":"...","needs_retrieval":bool,"needs_clarification":bool,"urgency":"normal|urgent","reason":"..."}"""

GREETING_MESSAGES: frozenset[str] = frozenset(
    {"hi", "hello", "hey", "namaste", "namaskar", "good morning", "good evening"}
)
CAPABILITY_PHRASES: tuple[str, ...] = (
    "what can you help",
    "what can you do",
    "how can you help",
    "what do you do",
    "how does this work",
    "tell me about this",
    "tell me about legalfriend",
    "what is legalfriend",
    "about this app",
)
URGENT_SAFETY_PHRASES: tuple[str, ...] = (
    "kill me",
    "kill myself",
    "threatening to kill",
    "threatened to kill",
    "immediate danger",
    "in danger now",
    "outside my house",
    "physical violence",
    "attack me",
    "attacking me",
)
LEGAL_QUERY_PHRASES: tuple[str, ...] = (
    "legal notice",
    "court notice",
    "section ",
    "cheque",
    "dishonour",
    "dishonored",
    "loan",
    "lend",
    "borrow",
    "lender",
    "interest",
    "recovery agent",
    "criminal case",
    "rbi",
    "repayment",
    "debt",
    "emi",
)


def classify_intent(english_query: str, recent_history: str) -> IntentDecision:
    normalized_query: str = " ".join(english_query.lower().strip().split())
    has_urgent_safety_signal: bool = any(
        phrase in normalized_query for phrase in URGENT_SAFETY_PHRASES
    )
    has_legal_signal: bool = any(
        phrase in normalized_query for phrase in LEGAL_QUERY_PHRASES
    )
    if normalized_query in GREETING_MESSAGES:
        return IntentDecision(
            intent="greeting",
            needs_retrieval=False,
            needs_clarification=False,
            urgency="normal",
            reason="deterministic_greeting",
        )
    if any(phrase in normalized_query for phrase in CAPABILITY_PHRASES):
        return IntentDecision(
            intent="capability",
            needs_retrieval=False,
            needs_clarification=False,
            urgency="normal",
            reason="deterministic_capability",
        )
    if has_urgent_safety_signal and has_legal_signal:
        return IntentDecision(
            intent="legal_question",
            needs_retrieval=True,
            needs_clarification=False,
            urgency="urgent",
            reason="deterministic_urgent_legal_query",
        )
    if has_urgent_safety_signal:
        return IntentDecision(
            intent="urgent_safety",
            needs_retrieval=False,
            needs_clarification=False,
            urgency="urgent",
            reason="deterministic_urgent_safety",
        )
    if has_legal_signal:
        return IntentDecision(
            intent="legal_question",
            needs_retrieval=True,
            needs_clarification=False,
            urgency="normal",
            reason="deterministic_legal_query",
        )
    user_prompt: str = f"Recent conversation:\n{recent_history or 'none'}\n\nUser message:\n{english_query}"
    try:
        return complete_structured(
            INTENT_PROMPT,
            user_prompt,
            IntentDecision,
            max_tokens=1536,
        )
    except (StructuredOutputError, PipelineError):
        return IntentDecision(
            intent="clarification",
            needs_retrieval=False,
            needs_clarification=True,
            urgency="normal",
            reason="intent_output_unavailable",
        )
