from fastapi import Request
from fastapi.responses import JSONResponse

from src.core.logger import get_logger

logger = get_logger(__name__)


class PipelineError(Exception):
    def __init__(self, message: str, stage: str) -> None:
        self.message = message
        self.stage = stage
        super().__init__(message)


class AllTiersFailedError(PipelineError):
    pass


def user_message_for_error(exc: PipelineError) -> str:
    if exc.stage == "transcribe_verbatim" and "maximum limit of 30 seconds" in exc.message:
        return "रिकॉर्डिंग 30 सेकंड या उससे कम रखें। कृपया छोटा सवाल फिर से बोलें। / Keep the recording to 30 seconds or less, then try again."
    return "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again."


async def pipeline_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PipelineError)
    logger.error(
        "pipeline_error", stage=exc.stage, message=exc.message, path=request.url.path
    )
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "stage": exc.stage,
                "message_en": exc.message,
                "message_user": user_message_for_error(exc),
            }
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "stage": "unknown",
                "message_en": "Internal error",
                "message_user": "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again.",
            }
        },
    )
