"""
Centralized configuration management for RaveDigest services.
Uses Pydantic Settings for validation and type safety.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    postgres_url: str = Field(..., env="POSTGRES_URL")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="digest_db", env="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    
    @validator("postgres_url", pre=True)
    def validate_postgres_url(cls, v, values):
        """Ensure POSTGRES_URL is properly formatted."""
        if not v:
            # Construct URL from components if not provided
            user = values.get("postgres_user", "postgres")
            password = values.get("postgres_password", "")
            host = values.get("postgres_host", "postgres")
            port = values.get("postgres_port", 5432)
            db = values.get("postgres_db", "digest_db")
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    @validator("redis_url", pre=True)
    def validate_redis_url(cls, v, values):
        """Ensure Redis URL is properly formatted."""
        if not v:
            # Construct URL from components if not provided
            host = values.get("redis_host", "redis")
            port = values.get("redis_port", 6379)
            db = values.get("redis_db", 0)
            password = values.get("redis_password")
            if password:
                return f"redis://:{password}@{host}:{port}/{db}"
            return f"redis://{host}:{port}/{db}"
        return v


class OpenAISettings(BaseSettings):
    """OpenAI API configuration settings."""
    
    api_key: str = Field(..., env="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")


class NotionSettings(BaseSettings):
    """Notion API configuration settings."""
    
    api_key: str = Field(..., env="NOTION_API_KEY")
    database_id: str = Field(..., env="NOTION_DB_ID")


class ServiceSettings(BaseSettings):
    """Service-specific configuration settings."""
    
    # Collector settings
    rss_feeds: List[str] = Field(
        default=[
            "https://techcrunch.com/category/artificial-intelligence/feed",
            "https://www.wired.com/feed/tag/ai/latest/rss",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://blog.kore.ai/rss.xml",
            "https://thenewstack.io/blog/feed/",
        ],
        env="RSS_FEEDS"
    )
    
    # Analyzer settings
    developer_keywords: List[str] = Field(
        default=[
            "ai", "machine learning", "deep learning", "neural network",
            "ai engineering", "developer", "programming", "mcp", "langchain",
            "openai", "anthropic", "python", "javascript", "typescript",
            "api", "microservices", "kubernetes", "docker", "aws", "gcp"
        ],
        env="DEVELOPER_KEYWORDS"
    )
    cosine_similarity_threshold: float = Field(default=0.6, env="COSINE_SIMILARITY_THRESHOLD")
    max_articles_per_digest: int = Field(default=20, env="MAX_ARTICLES_PER_DIGEST")
    
    # Redis Stream settings
    stream_max_length: int = Field(default=1000, env="STREAM_MAX_LENGTH")
    consumer_group_prefix: str = Field(default="ravedigest", env="CONSUMER_GROUP_PREFIX")
    
    # Retry settings
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="RETRY_DELAY")
    retry_backoff_factor: float = Field(default=2.0, env="RETRY_BACKOFF_FACTOR")
    
    # Timeout settings
    http_timeout: float = Field(default=30.0, env="HTTP_TIMEOUT")
    redis_timeout: float = Field(default=5.0, env="REDIS_TIMEOUT")
    
    @validator("rss_feeds", "developer_keywords", pre=True)
    def parse_list_from_string(cls, v):
        """Parse comma-separated string into list if needed."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        env="LOG_FORMAT"
    )
    include_correlation_id: bool = Field(default=True, env="LOG_INCLUDE_CORRELATION_ID")
    json_logs: bool = Field(default=False, env="JSON_LOGS")


class Settings(BaseSettings):
    """Main settings class that combines all configuration sections."""
    
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)
    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Service identification
    service_name: str = Field(default="ravedigest", env="SERVICE_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    version: str = Field(default="1.0.0", env="SERVICE_VERSION")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


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
