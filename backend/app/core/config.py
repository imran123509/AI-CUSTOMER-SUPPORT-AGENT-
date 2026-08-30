"""Centralized settings powered by pydantic-settings.

All environment variables in `.env.example` map onto fields here.  Reading
config goes through `get_settings()` which is cached so values are loaded
exactly once per process.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    app_name: str = "AI Agent"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Security
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14
    password_pepper: str = "change-me-too"

    cors_allowed_origins: str = "http://localhost:3000"

    rate_limit_per_minute: int = 120
    rate_limit_burst: int = 30

    # Database
    database_url: str = "postgresql+asyncpg://unfyd:change-me@localhost:5432/unfyd_pivot"
    sync_database_url: str = "postgresql+psycopg://unfyd:change-me@localhost:5432/unfyd_pivot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_events: str = "unfyd:events"
    redis_stream_docs: str = "unfyd:docs"
    redis_stream_tickets: str = "unfyd:tickets"
    redis_memory_ttl_seconds: int = 3600

    # Chroma
    chroma_http_url: str = "http://localhost:8001"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_temperature: float = 0.4
    gemini_max_output_tokens: int = 2048
    gemini_timeout_seconds: int = 30

    # RAG / uploads
    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 50
    allowed_upload_extensions: str = "pdf,docx,txt,csv,md"
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180
    rag_top_k: int = 5

    # Tickets / SLA
    sla_default_first_response_minutes: int = 15
    sla_default_resolution_hours: int = 24

    # Observability
    prometheus_enabled: bool = True
    sentry_dsn: str = ""

    # Feature flags
    feature_translation: bool = True
    feature_sentiment: bool = True
    feature_faq_generation: bool = True
    feature_smart_replies: bool = True

    @field_validator("cors_allowed_origins")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {e.strip().lower().lstrip(".") for e in self.allowed_upload_extensions.split(",")}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
