from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]
REPO_ROOT: Path = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    sarvam_api_key: str = Field(default="")

    qdrant_path: Path = REPO_ROOT / "legal-corpus" / "qdrant_data"
    chunks_dir: Path = REPO_ROOT / "legal-corpus" / "chunks"
    sqlite_path: Path = BACKEND_ROOT / "legalfriend.db"

    dense_model_name: str = "zeroentropy/zembed-1"
    dense_model_dtype: str = "bfloat16"
    sparse_model_name: str = "Qdrant/bm25"
    collection_name: str = "legal_acts"
    retrieval_top_k: int = 5

    demo_mode: bool = False
    cors_extra_origins: list[str] = Field(default_factory=list)


settings = Settings()
