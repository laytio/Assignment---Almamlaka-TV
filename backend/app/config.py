from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "Almamlaka TV RAG Chatbot"
    app_env: str = "development"
    data_dir: Path = BACKEND_DIR / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
