from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    supervisor_max_tokens: int = 256
    chat_max_tokens: int = 1024

    supabase_url: str = ""
    supabase_key: str = ""

    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    redis_url: str = "redis://localhost:6379"

    brave_search_api_key: str = ""
    e2b_api_key: str = ""

    langsmith_api_key: str = ""
    langsmith_project: str = "guidee"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    cors_origins: str = "http://localhost:1420,tauri://localhost"

    # Rate limits (requests per minute)
    rate_limit_chat: int = 30
    rate_limit_agent: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
