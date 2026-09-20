import httpx

from src.core.config import settings

BASE_URL = "https://api.sarvam.ai"


def _headers() -> dict[str, str]:
    return {"api-subscription-key": settings.sarvam_api_key}


async def identify_language(text: str) -> dict:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.post(
            "/text-analytics/v1/identify-language",
            json={"input": text},
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()
