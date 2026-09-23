"""
app/core/config.py

Application configuration — environment variables and settings.
All configuration lives here; no other module reads environment variables directly.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite for development; override with PostgreSQL URL for hosted deployment.
    DATABASE_URL: str = "sqlite:///./smartqueue.db"

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "SmartQueue"
    APP_VERSION: str = "0.1.0"

    # ── Patient frontend ──────────────────────────────────────────────────────
    # The URL that patients will use to access the registration page.
    # This is embedded in the registration QR code.
    # Change to your production domain before final deployment.
    PATIENT_FRONTEND_URL: str = "http://localhost:8000/patient/"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Origins allowed to make cross-origin requests to the API.
    # Permissive during development; tighten for production.
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance — imported by every module that needs configuration.
settings = Settings()
