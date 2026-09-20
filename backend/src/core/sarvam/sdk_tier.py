from sarvamai import SarvamAI

from src.core.config import settings

_client: SarvamAI | None = None


def get_client() -> SarvamAI:
    global _client
    if _client is None:
        _client = SarvamAI(
            api_subscription_key=settings.sarvam_api_key,
            timeout=240.0,
        )
    return _client


def identify_language(text: str) -> dict:
    resp = get_client().text.identify_language(input=text)
    return {"language_code": resp.language_code, "script_code": resp.script_code}


def transcribe_verbatim(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    resp = get_client().speech_to_text.transcribe(
        file=(filename, audio_bytes), model="saarika:v2.5", mode="verbatim"
    )
    return {"transcript": resp.transcript, "language_code": resp.language_code}


def transcribe_translate(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    resp = get_client().speech_to_text.translate(
        file=(filename, audio_bytes), model="saaras:v2.5"
    )
    return {
        "translated_english_query": resp.transcript,
        "language_code": resp.language_code,
    }


def translate_text(
    text: str, target_lang_code: str, source_lang_code: str = "en-IN"
) -> str:
    resp = get_client().text.translate(
        input=text,
        source_language_code=source_lang_code,
        target_language_code=target_lang_code,
    )
    return resp.translated_text


def speak(text: str, target_lang_code: str, speaker: str = "anushka") -> bytes:
    resp = get_client().text_to_speech.convert(
        text=text, target_language_code=target_lang_code, speaker=speaker
    )
    audio_b64 = resp.audios[0]
    import base64

    return base64.b64decode(audio_b64)


def chat_complete(
    system_prompt: str,
    user_prompt: str,
    model: str = "sarvam-105b",
    max_tokens: int = 2048,
    reasoning_effort: str | None = "low",
) -> str:
    resp = get_client().chat.completions(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )
    choice = resp.choices[0]
    content: str | None = choice.message.content
    if not content:
        raise ValueError(f"Sarvam returned no content: {choice.finish_reason}")
    return content
