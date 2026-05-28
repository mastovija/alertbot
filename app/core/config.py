"""
app/core/config.py
------------------
Central configuration module for the entire application.

Reads all environment variables from the .env file at startup and exposes
them as a single 'settings' object that any module can import.

Why this approach:
- Secrets (API keys, passwords) never live in the code itself
- One place to find all configuration — no hunting across files
- Pydantic validates types at startup, catching missing vars immediately
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic automatically maps .env variables to these fields,
    converting UPPER_SNAKE_CASE (in .env) to lower_snake_case (in Python).
    For example: DATABASE_URL in .env → database_url here.

    If any required variable is missing from .env, the app will
    raise a clear error at startup rather than failing silently later.
    """

    database_url: str       # PostgreSQL connection string
    redis_url: str          # Redis connection string (used by Celery)
    telegram_bot_token: str # Bot token from @BotFather
    anthropic_api_key: str  # Claude API key for natural language parsing
    tmdb_api_key: str       # TMDB API key for movie/series release checks

    model_config = SettingsConfigDict(
        env_file=".env",            # Load variables from this file
        env_file_encoding="utf-8",
    )


# Single shared instance — imported by all other modules like:
# from app.core.config import settings
# This means .env is only read once, at startup.
settings = Settings()