from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

from dotenv import load_dotenv

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
