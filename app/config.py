"""
Configuration management using Pydantic Settings.
Loads environment variables with type validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # X/Twitter API credentials (only needed for posting replies now)
    twitter_consumer_key: str
    twitter_consumer_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    twitter_bearer_token: str

    # Bot identity
    bot_user_id: str
    bot_username: str = "FallacySheriff"

    # RSSHub configuration (for reading tweets - bypasses API limits)
    rsshub_url: str = "http://localhost:1200"
    rsshub_access_key: str | None = None

    # Grok API
    grok_api_key: str

    # Polling configuration
    poll_interval_minutes: int = 5

    # Confidence threshold (0-100) - only post if confidence >= this value
    confidence_threshold: int = 90

    # App configuration
    database_path: str = "data/tweets.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance - lazily loaded
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance, creating it if needed."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def override_settings(settings: Settings) -> None:
    """Override settings for testing purposes."""
    global _settings
    _settings = settings
