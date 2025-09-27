"""
Standardized Redis client utilities for RaveDigest services.
Provides connection pooling, retry logic, and consistent error handling.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import redis

from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings

logger = get_logger(__name__)


class RedisClient:
    """Enhanced Redis client with retry logic and connection pooling."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._logger = get_logger(f"{service_name}.redis")

    def _serialize_value(self, value: Any) -> Any:
        """Convert values to Redis-compatible types."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (bytes, str, int, float)):
            return value
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except AttributeError as e:
                self._logger.warning(f"Value has no isoformat(): {e}")
            return str(value)

    def _get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            try:
                # Use URL if available, otherwise construct from components
                if self.settings.redis.redis_url:
                    self._client = redis.from_url(
                        self.settings.redis.redis_url,
                        decode_responses=True,
                        socket_timeout=self.settings.service.redis_timeout,
                        retry_on_timeout=True,
                        max_connections=20,
                        health_check_interval=30,
                    )
                else:
                    self._client = redis.Redis(
                        host=self.settings.redis.redis_host,
                        port=self.settings.redis.redis_port,
                        db=self.settings.redis.redis_db,
                        password=self.settings.redis.redis_password,
                        decode_responses=True,
                        socket_timeout=self.settings.service.redis_timeout,
                        retry_on_timeout=True,
                        max_connections=20,
                        health_check_interval=30,
                    )

                # Test connection
                self._client.ping()
                self._logger.info("✅ Connected to Redis successfully")

            except Exception as e:
                self._logger.error(f"❌ Failed to connect to Redis: {e}")
                raise

        return self._client

    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            client = self._get_client()
            return client.ping()
        except Exception as e:
            self._logger.error(f"Redis ping failed: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """Get value by key with error handling."""
        try:
            client = self._get_client()
            return client.get(key)
        except Exception as e:
            self._logger.error(f"Failed to get key {key}: {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration."""
        try:
            client = self._get_client()
            return client.set(key, value, ex=ex)
        except Exception as e:
            self._logger.error(f"Failed to set key {key}: {e}")
            return False

    def sadd(self, key: str, *values: str) -> int:
        """Add values to a set."""
        try:
            client = self._get_client()
            return client.sadd(key, *values)
        except Exception as e:
            self._logger.error(f"Failed to add to set {key}: {e}")
            return 0

    def sismember(self, key: str, value: str) -> bool:
        """Check if value is in set."""
        try:
            client = self._get_client()
            return client.sismember(key, value)
        except Exception as e:
            self._logger.error(f"Failed to check set membership {key}: {e}")
            return False

    def xadd(
        self,
        stream: str,
        fields: Dict[str, Any],
        maxlen: Optional[int] = None,
        approximate: bool = True,
        *,
        id: str = "*",
        nomkstream: bool = False,
        minid: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Add message to a Redis stream with optional trimming."""
        try:
            client = self._get_client()
            encoded_fields = {k: self._serialize_value(v) for k, v in fields.items()}
            return client.xadd(
                stream,
                encoded_fields,
                id=id,
                maxlen=maxlen,
                approximate=approximate,
                nomkstream=nomkstream,
                minid=minid,
                limit=limit,
            )
        except Exception as e:
            self._logger.error(f"Failed to add to stream {stream}: {e}")
            raise

    def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: Dict[str, str],
        count: int = 1,
        block: int = 1000,
    ) -> List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]:
        """Read from Redis stream with consumer group."""
        try:
            client = self._get_client()
            return client.xreadgroup(group, consumer, streams, count=count, block=block)
        except Exception as e:
            self._logger.error(f"Failed to read from stream group {group}: {e}")
            return []

    def xgroup_create(
        self, stream: str, group: str, id: str = "0", mkstream: bool = True
    ) -> bool:
        """Create consumer group for stream."""
        try:
            client = self._get_client()
            client.xgroup_create(stream, group, id=id, mkstream=mkstream)
            self._logger.info(f"Created consumer group {group} for stream {stream}")
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                self._logger.debug(f"Consumer group {group} already exists")
                return True
            else:
                self._logger.error(f"Failed to create consumer group {group}: {e}")
                return False
        except Exception as e:
            self._logger.error(f"Failed to create consumer group {group}: {e}")
            return False

    def xack(self, stream: str, group: str, message_id: str) -> int:
        """Acknowledge message in consumer group."""
        try:
            client = self._get_client()
            return client.xack(stream, group, message_id)
        except Exception as e:
            self._logger.error(f"Failed to ack message {message_id}: {e}")
            return 0

    def xpending_range(
        self,
        stream: str,
        group: str,
        min_id: str = "-",
        max_id: str = "+",
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get pending messages in consumer group."""
        try:
            client = self._get_client()
            return client.xpending_range(stream, group, min_id, max_id, count)
        except Exception as e:
            self._logger.error(f"Failed to get pending messages: {e}")
            return []

    def xrange(
        self, stream: str, min_id: str = "-", max_id: str = "+", count: int = 10
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get messages from stream by ID range."""
        try:
            client = self._get_client()
            return client.xrange(stream, min=min_id, max=max_id, count=count)
        except Exception as e:
            self._logger.error(f"Failed to get messages from stream: {e}")
            return []

    def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._logger.info("Redis connection closed")


# Global Redis client instances for each service
_redis_clients: Dict[str, RedisClient] = {}


def get_redis_client(service_name: str) -> RedisClient:
    """Get or create Redis client for a service."""
    if service_name not in _redis_clients:
        _redis_clients[service_name] = RedisClient(service_name)
    return _redis_clients[service_name]


def close_all_redis_clients():
    """Close all Redis client connections."""
    for client in _redis_clients.values():
        client.close()
    _redis_clients.clear()


# Convenience functions for backward compatibility
def get_redis_client_legacy() -> redis.Redis:
    """Legacy function for backward compatibility."""
    settings = get_settings()
    if settings.redis.redis_url:
        return redis.from_url(settings.redis.redis_url, decode_responses=True)
    else:
        return redis.Redis(
            host=settings.redis.redis_host,
            port=settings.redis.redis_port,
            db=settings.redis.redis_db,
            password=settings.redis.redis_password,
            decode_responses=True,
        )
