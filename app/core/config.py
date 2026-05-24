from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic automatically reads these from .env
    # converting DATABASE_URL → database_url
    database_url: str
    redis_url: str
    telegram_bot_token: str
    anthropic_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

# Single instance shared across the entire app
# Usage in other files: from app.core.config import settings
settings = Settings()