"""
Application configuration.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"
    debug: bool = False

    # GCP Settings
    gcp_project_id: str = ""
    gcs_bucket: str = ""
    pubsub_topic: str = "olmocr-jobs"
    pubsub_subscription: str = "olmocr-jobs-sub"

    # Firebase
    firebase_credentials_path: Optional[str] = None

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Storage
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    signed_url_expiration: int = 3600  # 1 hour

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
