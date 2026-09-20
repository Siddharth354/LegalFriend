import asyncio
import base64
import io
import wave
from collections.abc import AsyncIterator
from functools import lru_cache
from time import perf_counter
from typing import cast

from src.core.api_errors import PipelineError
from src.core.logger import get_logger
from src.core.memory import Memory
from src.core.sarvam import client as sarvam
from src.modules.legal_notice.features.analyze.citation_sources import (
    source_url_for_act,
)
from src.modules.legal_notice.features.analyze.graph import (
    AgentGraphOutcome,
    AgentNodeEvent,
    run_agent_graph,
    stream_agent_graph,
)
from src.modules.legal_notice.features.analyze.schemas import (
    AdviceResponse,
    AnalyzeResponse,
    Citation,
)
from src.modules.legal_notice.features.analyze.streaming import (
    encode_sse,
    stream_error_payload,
)
from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter

logger = get_logger(__name__)
MAYURA_CHAR_LIMIT: int = 950
TTS_CHAR_LIMIT: int = 2000
SIMPLE_RESPONSE_INTENTS: frozenset[str] = frozenset({"greeting", "capability"})
NO_SPEECH_RESPONSE_HI: str = (
    "नमस्ते। मैं लीगल फ्रेंड हूँ। मैं आपकी कैसे मदद कर सकती हूँ? मैं ऋण नोटिस, "
    "वसूली एजेंट की धमकियों, आपके अगले कदमों और प्रासंगिक कानूनी अंशों को आसान "
    "भाषा में समझने में मदद करती हूँ। कृपया अपना सवाल बोलें।"
)


def chunk_by_sentence(text: str, limit: int) -> list[str]:
    sentences: list[str] = text.replace("\n", " ").split(". ")
    chunks: list[str] = []
    buffer: str = ""
    for sentence in sentences:
        piece: str = sentence if sentence.endswith((".", "!", "?")) else sentence + "."
        if buffer and len(buffer) + len(piece) > limit:
            chunks.append(buffer.strip())
            buffer = ""
        buffer += " " + piece
    if buffer.strip():
        chunks.append(buffer.strip())
    return chunks


def translate_for_speech(text: str, target_lang_code: str) -> str:
    chunks: list[str] = chunk_by_sentence(text, MAYURA_CHAR_LIMIT)
    translated_chunks: list[str] = [
        sarvam.translate_text(chunk, target_lang_code) for chunk in chunks
    ]
    return " ".join(translated_chunks)


def synthesize_speech(text: str, target_lang_code: str) -> bytes:
    chunks: list[str] = chunk_by_sentence(text, TTS_CHAR_LIMIT) or [text]
    audio_chunks: list[bytes] = [
        sarvam.speak(chunk, target_lang_code) for chunk in chunks
    ]
    if len(audio_chunks) == 1:
        return audio_chunks[0]
    with wave.open(io.BytesIO(audio_chunks[0]), "rb") as first_wav:
        params = first_wav.getparams()
        frames: list[bytes] = [first_wav.readframes(first_wav.getnframes())]
    for audio_chunk in audio_chunks[1:]:
        with wave.open(io.BytesIO(audio_chunk), "rb") as chunk_wav:
            frames.append(chunk_wav.readframes(chunk_wav.getnframes()))
    output = io.BytesIO()
    with wave.open(output, "wb") as merged_wav:
        merged_wav.setparams(params)
        for frame in frames:
            merged_wav.writeframes(frame)
    return output.getvalue()


@lru_cache(maxsize=32)
def cached_simple_reply(answer: str, target_lang_code: str) -> tuple[str, str]:
    translated_reply: str = (
        answer
        if target_lang_code == "en-IN"
        else translate_for_speech(answer, target_lang_code)
    )
    audio_payload_b64: str = base64.b64encode(
        synthesize_speech(translated_reply, target_lang_code)
    ).decode()
    return translated_reply, audio_payload_b64


@lru_cache(maxsize=1)
def cached_no_speech_reply() -> str:
    return base64.b64encode(synthesize_speech(NO_SPEECH_RESPONSE_HI, "hi-IN")).decode()


def no_speech_response(verbatim_text: str) -> AnalyzeResponse:
    return AnalyzeResponse(
        summary_card=NO_SPEECH_RESPONSE_HI,
        citations=[],
        advice=AdviceResponse(
            language="hi-IN",
            transcript=NO_SPEECH_RESPONSE_HI,
            verbatim_transcript=verbatim_text,
            audio_payload_b64=cached_no_speech_reply(),
        ),
    )


def resolve_voice_language(language_code: object, fallback_language_code: str) -> str:
    detected_language_code: str = str(language_code or "").strip()
    if detected_language_code in {"en", "en-IN"}:
        return "en-IN"
    return detected_language_code or fallback_language_code


def detect_text_language_code(text: str) -> str | None:
    # Audio-based STT language ID is unreliable for code-switched Indian
    # speech (legal/financial terms said in English inside a Hindi/Kannada
    # sentence). Text-based ID on the actual transcribed script is more
    # robust and overrides a false "en-IN" audio detection.
    try:
        detected = sarvam.identify_language(text)
    except PipelineError:
        return None
    language_code: str = str(detected.get("language_code") or "").strip()
    return language_code or None


async def finalize_response(
    verbatim_text: str,
    english_query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str,
) -> AnalyzeResponse:
    outcome = await asyncio.to_thread(
        run_agent_graph, english_query, session_id, memory, retrieval
    )
    return response_from_outcome(
        outcome=outcome,
        verbatim_text=verbatim_text,
        target_lang_code=target_lang_code,
    )


def response_from_outcome(
    outcome: AgentGraphOutcome,
    verbatim_text: str,
    target_lang_code: str,
) -> AnalyzeResponse:
    if outcome.terminal_reason in SIMPLE_RESPONSE_INTENTS:
        translated_reply, audio_payload_b64 = cached_simple_reply(
            outcome.answer,
            target_lang_code,
        )
    else:
        translated_reply = (
            outcome.answer
            if target_lang_code == "en-IN"
            else translate_for_speech(outcome.answer, target_lang_code)
        )
        audio_payload_b64 = base64.b64encode(
            synthesize_speech(translated_reply, target_lang_code)
        ).decode()
    return AnalyzeResponse(
        summary_card=translated_reply,
        citations=[
            Citation(
                chunk_id=str(citation["chunk_id"]),
                citation_string=str(citation["citation_string"]),
                source_title=str(citation["act"]),
                source_url=source_url_for_act(str(citation["act"])),
                content=str(citation["content"]),
                score=float(cast(str | int | float, citation["score"])),
            )
            for citation in outcome.citations
        ],
        advice=AdviceResponse(
            language=target_lang_code,
            transcript=translated_reply,
            verbatim_transcript=verbatim_text,
            audio_payload_b64=audio_payload_b64,
        ),
    )


async def stream_response_from_graph(
    verbatim_text: str,
    english_query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str,
) -> AsyncIterator[bytes]:
    active_node: str | None = None
    graph_complete: bool = False
    try:
        async for item in stream_agent_graph(
            english_query,
            session_id,
            memory,
            retrieval,
        ):
            if isinstance(item, AgentNodeEvent):
                if item.event == "agent_start":
                    active_node = item.node
                payload: dict[str, object] = {"node": item.node}
                if item.detail:
                    payload["detail"] = item.detail
                yield encode_sse(item.event, payload)
                continue
            graph_complete = True
            response = response_from_outcome(
                outcome=item,
                verbatim_text=verbatim_text,
                target_lang_code=target_lang_code,
            )
            yield encode_sse("result", response.model_dump(mode="json"))
    except Exception as exc:
        stage: str = (
            exc.stage
            if graph_complete and isinstance(exc, PipelineError)
            else active_node
            or (exc.stage if isinstance(exc, PipelineError) else "unknown")
        )
        logger.error("stream_pipeline_error", stage=stage, error=str(exc))
        yield encode_sse("error", stream_error_payload(stage, exc))


async def analyze_voice(
    audio_bytes: bytes,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str = "hi-IN",
) -> AnalyzeResponse:
    started_at: float = perf_counter()
    verbatim = sarvam.transcribe_verbatim(audio_bytes)
    verbatim_text: str = str(verbatim.get("transcript") or "").strip()
    if not verbatim_text:
        return no_speech_response(verbatim_text)
    detected_language_code: str = resolve_voice_language(
        detect_text_language_code(verbatim_text) or verbatim.get("language_code"),
        target_lang_code,
    )
    english_query: str = (
        verbatim_text
        if detected_language_code == "en-IN"
        else str(sarvam.transcribe_translate(audio_bytes)["translated_english_query"])
    )
    logger.info(
        "voice_input_ready",
        detected_language_code=detected_language_code,
        verbatim_text=verbatim_text,
        english_query=english_query,
    )
    response: AnalyzeResponse = await finalize_response(
        verbatim_text=verbatim_text,
        english_query=english_query,
        session_id=session_id,
        memory=memory,
        retrieval=retrieval,
        target_lang_code=detected_language_code,
    )
    logger.info(
        "pipeline_complete",
        input_type="voice",
        duration_ms=round((perf_counter() - started_at) * 1000, 1),
    )
    return response


async def analyze_text(
    query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str = "hi-IN",
    source_lang_code: str = "en-IN",
) -> AnalyzeResponse:
    started_at: float = perf_counter()
    english_query: str = (
        query
        if source_lang_code == "en-IN"
        else sarvam.translate_text(query, "en-IN", source_lang_code=source_lang_code)
    )
    logger.info(
        "text_input_ready",
        source_language_code=source_lang_code,
        target_language_code=target_lang_code,
        verbatim_text=query,
        english_query=english_query,
    )
    response: AnalyzeResponse = await finalize_response(
        verbatim_text=query,
        english_query=english_query,
        session_id=session_id,
        memory=memory,
        retrieval=retrieval,
        target_lang_code=target_lang_code,
    )
    logger.info(
        "pipeline_complete",
        input_type="text",
        duration_ms=round((perf_counter() - started_at) * 1000, 1),
    )
    return response


async def analyze_voice_stream(
    audio_bytes: bytes,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str = "hi-IN",
) -> AsyncIterator[bytes]:
    try:
        verbatim = sarvam.transcribe_verbatim(audio_bytes)
        verbatim_text: str = str(verbatim.get("transcript") or "").strip()
        if not verbatim_text:
            response = no_speech_response(verbatim_text)
            yield encode_sse("result", response.model_dump(mode="json"))
            return
        detected_language_code: str = resolve_voice_language(
            verbatim.get("language_code"),
            target_lang_code,
        )
        english_query: str = (
            verbatim_text
            if detected_language_code == "en-IN"
            else str(
                sarvam.transcribe_translate(audio_bytes)["translated_english_query"]
            )
        )
        logger.info(
            "voice_input_ready",
            detected_language_code=detected_language_code,
            verbatim_text=verbatim_text,
            english_query=english_query,
        )
    except Exception as exc:
        stage: str = exc.stage if isinstance(exc, PipelineError) else "voice_input"
        logger.error("stream_pipeline_error", stage=stage, error=str(exc))
        yield encode_sse("error", stream_error_payload(stage, exc))
        return
    async for event in stream_response_from_graph(
        verbatim_text=verbatim_text,
        english_query=english_query,
        session_id=session_id,
        memory=memory,
        retrieval=retrieval,
        target_lang_code=detected_language_code,
    ):
        yield event


async def analyze_text_stream(
    query: str,
    session_id: str,
    memory: Memory,
    retrieval: RetrievalAdapter,
    target_lang_code: str = "hi-IN",
    source_lang_code: str = "en-IN",
) -> AsyncIterator[bytes]:
    try:
        english_query: str = (
            query
            if source_lang_code == "en-IN"
            else sarvam.translate_text(
                query,
                "en-IN",
                source_lang_code=source_lang_code,
            )
        )
        logger.info(
            "text_input_ready",
            source_language_code=source_lang_code,
            target_language_code=target_lang_code,
            verbatim_text=query,
            english_query=english_query,
        )
    except Exception as exc:
        stage: str = exc.stage if isinstance(exc, PipelineError) else "text_input"
        logger.error("stream_pipeline_error", stage=stage, error=str(exc))
        yield encode_sse("error", stream_error_payload(stage, exc))
        return
    async for event in stream_response_from_graph(
        verbatim_text=query,
        english_query=english_query,
        session_id=session_id,
        memory=memory,
        retrieval=retrieval,
        target_lang_code=target_lang_code,
    ):
        yield event
