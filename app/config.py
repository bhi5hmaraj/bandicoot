"""
Configuration management for Bandicoot RMAB API.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    API_TITLE: str = "Bandicoot RMAB API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Restless Multi-Armed Bandit recommendation service for caregiver prioritization"

    # Authentication
    API_KEY: Optional[str] = None  # Set via env var for production
    REQUIRE_AUTH: bool = False  # Set to True in production

    # Model Settings
    N_CLUSTERS: int = 20
    GAMMA: float = 0.99
    ALPHA: float = 1.0
    MIN_OBSERVATIONS: int = 10
    RANDOM_STATE: int = 42

    # Data Paths (for file-based storage, will migrate to DB later)
    DATA_DIR: str = "/app/data"
    MODEL_PATH: Optional[str] = None  # Path to saved model pickle

    # Database Settings (for future PostgreSQL integration)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Performance Settings
    MAX_CAREGIVERS: int = 200000  # Maximum caregivers to process
    RECOMMENDATION_TIMEOUT: int = 30  # seconds

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
