import orjson
from pydantic import BaseModel, ValidationError

from src.core.sarvam import client as sarvam

STRUCTURED_OUTPUT_ATTEMPTS: int = 2
INVALID_OUTPUT_CONTEXT_LIMIT: int = 2000


class StructuredOutputError(ValueError):
    pass


def parse_json_response[T: BaseModel](raw: str, schema: type[T]) -> T:
    cleaned: str = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    candidates: list[str] = [cleaned]
    object_start: int = cleaned.find("{")
    object_end: int = cleaned.rfind("}")
    if object_start >= 0 and object_end > object_start:
        candidates.append(cleaned[object_start : object_end + 1])
    last_error: orjson.JSONDecodeError | ValidationError | None = None
    for candidate in candidates:
        try:
            payload: object = orjson.loads(candidate)
            return schema.model_validate(payload)
        except (orjson.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise StructuredOutputError(str(last_error))


def complete_structured[T: BaseModel](
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    max_tokens: int,
    model: str = "sarvam-105b",
    attempts: int = STRUCTURED_OUTPUT_ATTEMPTS,
) -> T:
    current_prompt: str = user_prompt
    last_error: StructuredOutputError | None = None
    for attempt in range(attempts):
        raw: str = sarvam.chat_complete(
            system_prompt,
            current_prompt,
            model=model,
            max_tokens=max_tokens,
        )
        try:
            return parse_json_response(raw, schema)
        except StructuredOutputError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                invalid_output: str = raw[:INVALID_OUTPUT_CONTEXT_LIMIT]
                current_prompt = (
                    f"{user_prompt}\n\nThe previous response was invalid for "
                    f"{schema.__name__}:\n{invalid_output}\n\nReturn corrected strict JSON only."
                )
    raise StructuredOutputError(str(last_error))
