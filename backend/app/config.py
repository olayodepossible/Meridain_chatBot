from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

from dotenv import load_dotenv

load_dotenv(override=True)


def _default_conversation_memory_dir() -> Path:
    """Backend repo root `.memory` (ignored by git) for local conversation JSON files."""
    return Path(__file__).resolve().parent.parent / ".memory"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tool-augmented-ai-backend"
    environment: str = "development"
    log_level: str = "INFO"

    openai_api_key:  str | None = os.getenv("OPENROUTER_API_KEY")
    openai_model: str = "gpt-4.1-mini"
    max_tool_steps: int = 6

    mcp_server_url: HttpUrl = "https://order-mcp-74afyau24q-uc.a.run.app/mcp"
    mcp_server_auth_token: str | None = Field(default=None, repr=False)
    mcp_tool_cache_seconds: int = 60

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # Conversation memory: S3 when USE_S3 + S3_BUCKET (Lambda), else local directory.
    s3_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_BUCKET", "s3_bucket"),
    )
    use_s3: bool = Field(
        default=False,
        validation_alias=AliasChoices("USE_S3", "use_s3"),
    )
    conversation_memory_dir: Path = Field(
        default_factory=_default_conversation_memory_dir,
        validation_alias=AliasChoices("CONVERSATION_MEMORY_DIR", "conversation_memory_dir"),
    )

    @field_validator("use_s3", mode="before")
    @classmethod
    def _coerce_use_s3(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        return bool(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
