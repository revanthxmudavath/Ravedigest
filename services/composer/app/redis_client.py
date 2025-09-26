#services/composer/app/redis_client.py
from datetime import datetime, timezone

from shared.app_logging.logger import get_logger
from shared.schemas.messages import DigestReady
from shared.utils.redis_client import \
    get_redis_client as get_shared_redis_client
from shared.utils.retry import retry

logger = get_logger("composer.redis_client")


@retry(retryable_exceptions=(Exception,))
def publish_digest_ready(digest) -> None:
    """Publish digest ready event to Redis stream."""
    try:
        client = get_shared_redis_client("composer")
        inserted_at = digest.inserted_at or datetime.now(timezone.utc)

        event = DigestReady(
            version="1.0",
            digest_id=str(digest.id),
            title=digest.title,
            summary=digest.summary,
            url=digest.url,
            source=digest.source,
            inserted_at=inserted_at
        )

        # Convert to string format for Redis
        payload = {
            "version": str(event.version),
            "digest_id": str(event.digest_id),
            "title": str(event.title),
            "summary": str(event.summary),
            "url": str(event.url),
            "source": str(event.source),
            "inserted_at": event.inserted_at.isoformat(),
        }

        # Publish to stream
        message_id = client.xadd("digest_stream", payload)
        logger.info(f"✅ Published digest_ready: {message_id}")

    except Exception as e:
        logger.error(f"❌ Failed to publish digest_ready: {e}")
        raise
