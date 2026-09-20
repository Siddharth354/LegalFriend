from collections.abc import Callable

from tenacity import retry, stop_after_attempt, wait_fixed

from src.core.api_errors import PipelineError
from src.core.logger import get_logger
from src.core.sarvam import sdk_tier

logger = get_logger(__name__)


def _with_retry[T](fn: Callable[[], T]) -> T:
    return retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)(fn)()


def _run[T](capability: str, fn: Callable[[], T]) -> T:
    try:
        result = _with_retry(fn)
        logger.info("sarvam_tier", capability=capability, tier="sdk", status="ok")
        return result
    except Exception as exc:
        logger.warning(
            "sarvam_tier",
            capability=capability,
            tier="sdk",
            status="failed",
            error=str(exc),
        )
        raise PipelineError(str(exc), stage=capability) from exc


def identify_language(text: str) -> dict:
    return _run("identify_language", lambda: sdk_tier.identify_language(text))


def transcribe_verbatim(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    return _run(
        "transcribe_verbatim",
        lambda: sdk_tier.transcribe_verbatim(audio_bytes, filename),
    )


def transcribe_translate(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    return _run(
        "transcribe_translate",
        lambda: sdk_tier.transcribe_translate(audio_bytes, filename),
    )


def translate_text(
    text: str, target_lang_code: str, source_lang_code: str = "en-IN"
) -> str:
    return _run(
        "translate_text",
        lambda: sdk_tier.translate_text(text, target_lang_code, source_lang_code),
    )


def speak(text: str, target_lang_code: str) -> bytes:
    return _run("speak", lambda: sdk_tier.speak(text, target_lang_code))


def chat_complete(
    system_prompt: str,
    user_prompt: str,
    model: str = "sarvam-105b",
    max_tokens: int = 2048,
    reasoning_effort: str | None = "low",
) -> str:
    return _run(
        "chat_complete",
        lambda: sdk_tier.chat_complete(
            system_prompt,
            user_prompt,
            model=model,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        ),
    )
