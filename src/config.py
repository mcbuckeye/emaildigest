"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "your-secret-key-change-in-production"  # noqa: S105


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_name: str = "EmailDigest"
    app_env: str = Field(default="development")
    app_base_url: str = Field(default="http://localhost:8000")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173")

    # Database
    database_url: str = "postgresql+asyncpg://emaildigest:emaildigest@localhost:5432/emaildigest"

    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # JWT
    secret_key: str = INSECURE_DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_token_expire_minutes: int = 30

    # Rate limiting
    rate_limit_signup: str = "5/minute"
    rate_limit_login: str = "10/minute"
    rate_limit_ai_chat: str = "20/minute"

    # Email (smtp2go)
    smtp2go_api_key: str = ""
    smtp2go_from_email: str = "noreply@emaildigest.machomelab.com"
    smtp2go_from_name: str = "EmailDigest"
    smtp2go_host: str = "mail.smtp2go.com"
    smtp2go_port: int = 2525

    # AI/LLM (OpenAI)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # Observability
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def config() -> Settings:
    """Alias for get_settings."""
    return get_settings()


def reset_settings_cache() -> None:
    """Clear cached settings (tests use this to re-read env)."""
    get_settings.cache_clear()
