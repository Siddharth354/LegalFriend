from fastapi import APIRouter, Header, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.modules.legal_notice.features.analyze.logic import (
    analyze_text,
    analyze_text_stream,
    analyze_voice,
    analyze_voice_stream,
)
from src.modules.legal_notice.features.analyze.schemas import (
    AnalyzeResponse,
    AnalyzeTextRequest,
)

router = APIRouter()
STREAM_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


@router.post("/api/v1/analyze/voice", response_model=AnalyzeResponse)
async def analyze_voice_endpoint(
    request: Request,
    audio: UploadFile,
    x_session_id: str = Header(...),
) -> AnalyzeResponse:
    audio_bytes = await audio.read()
    return await analyze_voice(
        audio_bytes=audio_bytes,
        session_id=x_session_id,
        memory=request.app.state.memory,
        retrieval=request.app.state.retrieval,
    )


@router.post("/api/v1/analyze/text", response_model=AnalyzeResponse)
async def analyze_text_endpoint(
    request: Request,
    body: AnalyzeTextRequest,
    x_session_id: str = Header(...),
) -> AnalyzeResponse:
    return await analyze_text(
        query=body.query,
        session_id=x_session_id,
        memory=request.app.state.memory,
        retrieval=request.app.state.retrieval,
        target_lang_code=body.target_lang_code,
        source_lang_code=body.source_lang_code,
    )


@router.post("/api/v1/analyze/voice/stream")
async def analyze_voice_stream_endpoint(
    request: Request,
    audio: UploadFile,
    x_session_id: str = Header(...),
) -> StreamingResponse:
    audio_bytes = await audio.read()
    return StreamingResponse(
        analyze_voice_stream(
            audio_bytes=audio_bytes,
            session_id=x_session_id,
            memory=request.app.state.memory,
            retrieval=request.app.state.retrieval,
        ),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )


@router.post("/api/v1/analyze/text/stream")
async def analyze_text_stream_endpoint(
    request: Request,
    body: AnalyzeTextRequest,
    x_session_id: str = Header(...),
) -> StreamingResponse:
    return StreamingResponse(
        analyze_text_stream(
            query=body.query,
            session_id=x_session_id,
            memory=request.app.state.memory,
            retrieval=request.app.state.retrieval,
            target_lang_code=body.target_lang_code,
            source_lang_code=body.source_lang_code,
        ),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
