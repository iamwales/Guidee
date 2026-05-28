from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_anthropic_base_url: str = "https://openrouter.ai/api"
    claude_model: str = "anthropic/claude-sonnet-4"
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
    stripe_price_pro: str = ""
    stripe_price_team: str = ""
    stripe_portal_url: str = ""
    stripe_customer_portal_return_url: str = "http://localhost:1420/settings"

    app_env: str = "development"
    allow_dev_tokens: bool = True

    cors_origins: str = "http://localhost:1420,tauri://localhost"

    # Rate limits (requests per minute)
    rate_limit_chat: int = 30
    rate_limit_agent: int = 5
    rate_limit_chat_pro: int = 120
    rate_limit_agent_pro: int = 20
    rate_limit_chat_team: int = 300
    rate_limit_agent_team: int = 60
    daily_agent_tasks_free: int = 25
    daily_agent_tasks_pro: int = 250
    daily_agent_tasks_team: int = 1000

    @property
    def has_llm_api_key(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def dev_tokens_enabled(self) -> bool:
        return self.allow_dev_tokens and self.app_env.lower() in {
            "dev",
            "development",
            "local",
            "test",
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
