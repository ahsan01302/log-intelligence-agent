"""Runtime settings, read from LOGINTEL_* environment variables and an optional .env file."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOGINTEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama is the default so the project runs locally and for free.
    provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:4b"
    embed_model: str = "nomic-embed-text"
    api_key: SecretStr | None = None

    # Relative paths: resolved against the working directory, never hardcoded.
    index_dir: Path = Path("data/index")
    upload_dir: Path = Path("data/uploads")
    max_upload_mb: int = Field(default=20, gt=0)

    top_k: int = Field(default=5, gt=0)
    window_seconds: int = Field(default=30, gt=0)
