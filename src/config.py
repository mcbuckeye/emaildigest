"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_name: str = "EmailDigest"

    # Database
    database_url: str = "postgresql+asyncpg://emaildigest:emaildigest@localhost:5432/emaildigest"

    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email (smtp2go)
    smtp2go_api_key: str = ""
    smtp2go_from_email: str = "noreply@emaildigest.machomelab.com"
    smtp2go_from_name: str = "EmailDigest"

    # AI/LLM
    llm_api_key: str = ""
    llm_model: str = "openrouter/deepseek/deepseek-r1-distill-llama-70b"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def config() -> Settings:
    """Alias for get_settings."""
    return get_settings()
