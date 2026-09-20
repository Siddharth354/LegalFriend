import os

from src.core.config import settings


def mcp_env() -> dict[str, str]:
    # sarvam-mcp does not auto-inherit SARVAM_API_KEY from .env — must be set explicitly
    # in the subprocess environment.
    env = os.environ.copy()
    env["SARVAM_API_KEY"] = settings.sarvam_api_key
    return env
