from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    redis_url: str = "redis://localhost:6379"
    brave_search_api_key: str = ""
    e2b_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = "guidee"


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
