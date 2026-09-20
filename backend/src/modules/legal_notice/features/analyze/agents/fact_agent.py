from src.core.api_errors import PipelineError
from src.modules.legal_notice.features.analyze.agents.parsing import (
    StructuredOutputError,
    complete_structured,
)
from src.modules.legal_notice.features.analyze.state import CaseFacts

FACT_PROMPT: str = """Extract only case facts from this Indian legal question.
Return strict JSON only. Do not infer facts not stated.
An interest-rate question does not require a principal amount. Preserve daily, monthly, and annual rate periods exactly as stated.
Schema: {"lender_name":string|null,"loan_amount":string|null,"interest_rate":string|null,"threat_type":string|null,"contact_timing":string|null,"missing_information":[string]}"""


def extract_case_facts(english_query: str) -> CaseFacts:
    try:
        return complete_structured(
            FACT_PROMPT,
            english_query,
            CaseFacts,
            max_tokens=2048,
        )
    except (StructuredOutputError, PipelineError):
        return CaseFacts(missing_information=["Structured fact extraction unavailable"])
