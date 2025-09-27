"""
Centralized configuration management for RaveDigest services.
Uses Pydantic Settings for validation and type safety.
"""

import re
from functools import lru_cache
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppBaseSettings(BaseSettings):
    """Base settings with shared configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class DatabaseSettings(AppBaseSettings):
    """Database configuration settings."""

    postgres_url: Optional[str] = Field(
        default=None,
        validation_alias="POSTGRES_URL",
    )
    postgres_user: str = Field(
        default="postgres",
        validation_alias="POSTGRES_USER",
    )
    postgres_password: str = Field(
        ...,
        validation_alias="POSTGRES_PASSWORD",
    )
    postgres_db: str = Field(
        default="digest_db",
        validation_alias="POSTGRES_DB",
    )
    postgres_host: str = Field(
        default="postgres",
        validation_alias="POSTGRES_HOST",
    )
    postgres_port: int = Field(
        default=5432,
        validation_alias="POSTGRES_PORT",
    )

    @validator("postgres_url", pre=True)
    def validate_postgres_url(cls, v, values):
        """Ensure POSTGRES_URL is properly formatted."""
        if not v:
            user = values.get("postgres_user", "postgres")
            password = values.get("postgres_password", "")
            host = values.get("postgres_host", "postgres")
            port = values.get("postgres_port", 5432)
            db = values.get("postgres_db", "digest_db")
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return v


class RedisSettings(AppBaseSettings):
    """Redis configuration settings."""

    redis_url: Optional[str] = Field(
        default=None,
        validation_alias="REDIS_URL",
    )
    redis_host: str = Field(
        default="redis",
        validation_alias="REDIS_HOST",
    )
    redis_port: int = Field(
        default=6379,
        validation_alias="REDIS_PORT",
    )
    redis_db: int = Field(
        default=0,
        validation_alias="REDIS_DB",
    )
    redis_password: Optional[str] = Field(
        default=None,
        validation_alias="REDIS_PASSWORD",
    )

    @validator("redis_url", pre=True)
    def validate_redis_url(cls, v, values):
        """Ensure Redis URL is properly formatted."""
        if not v:
            host = values.get("redis_host", "redis")
            port = values.get("redis_port", 6379)
            db = values.get("redis_db", 0)
            password = values.get("redis_password")
            if password:
                return f"redis://:{password}@{host}:{port}/{db}"
            return f"redis://{host}:{port}/{db}"
        return v


class OpenAISettings(AppBaseSettings):
    """OpenAI API configuration settings."""

    api_key: str = Field(
        ...,
        validation_alias="OPENAI_API_KEY",
    )
    model: str = Field(
        default="gpt-4o-mini",
        validation_alias="OPENAI_MODEL",
    )
    max_tokens: int = Field(
        default=1000,
        validation_alias="OPENAI_MAX_TOKENS",
    )
    temperature: float = Field(
        default=0.7,
        validation_alias="OPENAI_TEMPERATURE",
    )


class NotionSettings(AppBaseSettings):
    """Notion API configuration settings."""

    api_key: str = Field(
        ...,
        validation_alias="NOTION_API_KEY",
    )
    database_id: str = Field(
        ...,
        validation_alias=AliasChoices("NOTION_DB_ID", "NOTION_DATABASE_ID"),
    )

    @validator("database_id")
    def validate_database_id(cls, v):
        """Validate Notion database ID format (should be UUID format without hyphens)."""
        if not v:
            raise ValueError("Notion database ID is required")

        # Remove hyphens and check if it's 32 hexadecimal characters
        cleaned_id = v.replace("-", "")
        if not re.match(r"^[0-9a-fA-F]{32}$", cleaned_id):
            raise ValueError(
                "Notion database ID must be a valid UUID format (32 hexadecimal characters)"
            )

        return v


class ServiceSettings(AppBaseSettings):
    """Service-specific configuration settings."""

    rss_feeds: List[str] = Field(
        default=[
            "https://techcrunch.com/category/artificial-intelligence/feed",
            "https://www.wired.com/feed/tag/ai/latest/rss",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://blog.kore.ai/rss.xml",
            "https://thenewstack.io/blog/feed/",
        ],
        validation_alias="RSS_FEEDS",
    )
    developer_keywords: List[str] = Field(
        default=[
            "ai",
            "machine learning",
            "deep learning",
            "neural network",
            "ai engineering",
            "developer",
            "programming",
            "mcp",
            "langchain",
            "openai",
            "anthropic",
            "python",
            "javascript",
            "typescript",
            "api",
            "microservices",
            "kubernetes",
            "docker",
            "aws",
            "gcp",
        ],
        validation_alias="DEVELOPER_KEYWORDS",
    )
    cosine_similarity_threshold: float = Field(
        default=0.6,
        validation_alias="COSINE_SIMILARITY_THRESHOLD",
    )
    max_articles_per_digest: int = Field(
        default=20,
        validation_alias="MAX_ARTICLES_PER_DIGEST",
    )
    stream_max_length: int = Field(
        default=1000,
        validation_alias="STREAM_MAX_LENGTH",
    )
    consumer_group_prefix: str = Field(
        default="ravedigest",
        validation_alias="CONSUMER_GROUP_PREFIX",
    )
    max_retries: int = Field(
        default=3,
        validation_alias="MAX_RETRIES",
    )
    retry_delay: float = Field(
        default=1.0,
        validation_alias="RETRY_DELAY",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        validation_alias="RETRY_BACKOFF_FACTOR",
    )
    http_timeout: float = Field(
        default=30.0,
        validation_alias="HTTP_TIMEOUT",
    )
    redis_timeout: float = Field(
        default=5.0,
        validation_alias="REDIS_TIMEOUT",
    )

    @validator("rss_feeds", "developer_keywords", pre=True)
    def parse_list_from_string(cls, v):
        """Parse comma-separated string into list if needed."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @validator("rss_feeds")
    def validate_rss_feeds(cls, v):
        """Validate that RSS feeds are valid URLs."""
        if not isinstance(v, list):
            raise ValueError("RSS feeds must be a list")

        for feed_url in v:
            if not feed_url:
                continue  # Skip empty strings

            try:
                parsed = urlparse(feed_url)
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError(f"Invalid RSS feed URL: {feed_url}")

                if parsed.scheme not in ["http", "https"]:
                    raise ValueError(f"RSS feed URL must use HTTP or HTTPS: {feed_url}")

            except Exception as e:
                raise ValueError(f"Invalid RSS feed URL format: {feed_url} - {str(e)}")

        return v


class LoggingSettings(AppBaseSettings):
    """Logging configuration settings."""

    level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        validation_alias="LOG_FORMAT",
    )
    include_correlation_id: bool = Field(
        default=True,
        validation_alias="LOG_INCLUDE_CORRELATION_ID",
    )
    json_logs: bool = Field(
        default=False,
        validation_alias="JSON_LOGS",
    )


class Settings(AppBaseSettings):
    """Main settings class that combines all configuration sections."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    service_name: str = Field(
        default="ravedigest",
        validation_alias="SERVICE_NAME",
    )
    environment: str = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )
    version: str = Field(
        default="1.0.0",
        validation_alias="SERVICE_VERSION",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience functions for common settings
def get_database_url() -> str:
    """Get the database URL."""
    return get_settings().database.postgres_url


def get_redis_url() -> str:
    """Get the Redis URL."""
    return get_settings().redis.redis_url


def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    return get_settings().openai.api_key


def get_notion_api_key() -> str:
    """Get the Notion API key."""
    return get_settings().notion.api_key


def get_notion_database_id() -> str:
    """Get the Notion database ID."""
    return get_settings().notion.database_id
