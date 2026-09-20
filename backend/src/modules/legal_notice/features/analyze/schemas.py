from pydantic import BaseModel


class AnalyzeTextRequest(BaseModel):
    query: str
    source_lang_code: str = "en-IN"
    target_lang_code: str = "hi-IN"


class Citation(BaseModel):
    chunk_id: str
    citation_string: str
    source_title: str
    source_url: str
    content: str
    score: float


class AdviceResponse(BaseModel):
    language: str
    transcript: str
    verbatim_transcript: str
    audio_payload_b64: str


class AnalyzeResponse(BaseModel):
    summary_card: str
    citations: list[Citation]
    advice: AdviceResponse
