from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_anthropic_base_url: str = "https://openrouter.ai/api"
    claude_model: str = "anthropic/claude-sonnet-4"
    redis_url: str = "redis://localhost:6379"
    brave_search_api_key: str = ""
    e2b_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = "guidee"


@lru_cache
def get_settings() -> AgentSettings:
    return AgentSettings()
