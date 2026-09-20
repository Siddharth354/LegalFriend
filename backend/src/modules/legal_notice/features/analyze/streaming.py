from typing import Literal

import orjson

from src.core.api_errors import PipelineError, user_message_for_error

SseEventName = Literal["agent_start", "agent_done", "result", "error"]
GENERIC_USER_MESSAGE: str = (
    "कुछ गड़बड़ हो गई, दोबारा कोशिश करें। / Something went wrong, please try again."
)


def encode_sse(event: SseEventName, payload: dict[str, object]) -> bytes:
    return b"event: " + event.encode() + b"\ndata: " + orjson.dumps(payload) + b"\n\n"


def stream_error_payload(stage: str, exc: Exception) -> dict[str, object]:
    message_user: str = (
        user_message_for_error(exc)
        if isinstance(exc, PipelineError)
        else GENERIC_USER_MESSAGE
    )
    return {"stage": stage, "message_user": message_user}
