"""
app/core/config.py

Application configuration — environment variables and settings.
All configuration lives here; no other module reads environment variables directly.
"""
from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite for development; override with PostgreSQL URL for hosted deployment.
    DATABASE_URL: str = "sqlite:///./smartqueue.db"

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "SmartQueue"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # "development" | "production" | "test"
    DOCS_ENABLED: bool = True

    # ── Security & Auth ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "smartqueue-default-secret-key-32-bytes-long-change-in-production!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours default for shift work
    DEVICE_KEY_HEADER: str = "X-Device-Key"
    DEVICE_ID_HEADER: str = "X-Device-ID"

    # ── Patient frontend ──────────────────────────────────────────────────────
    PATIENT_FRONTEND_URL: str = "http://localhost:8000/patient/"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if "smartqueue-default" in self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    "Production security violation: JWT_SECRET_KEY must be a cryptographically "
                    "secure random string of at least 32 characters in production."
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "Production security violation: CORS_ORIGINS cannot contain wildcard '*' in production. "
                    "Specify exact allowed domains or configure same-origin reverse proxy."
                )
        return self


# Singleton settings instance — imported by every module that needs configuration.
settings = Settings()
