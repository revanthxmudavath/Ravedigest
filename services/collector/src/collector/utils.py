#services/collector/src/collector/utils.py
import logging
from shared.database.models.article import Article
from shared.schemas.messages import RawArticle
from shared.utils.redis_client import get_redis_client
from shared.app_logging.logger import get_logger
from shared.utils.retry import retry

logger = get_logger("collector.utils")

@retry(retryable_exceptions=(Exception,))
def is_duplicate(url: str) -> bool:
    """Check if URL has already been processed."""
    try:
        redis_client = get_redis_client("collector")
        return redis_client.sismember("seen_urls", url)
    except Exception as e:
        logger.error(f"Redis error checking duplicate: {e}")
        return False

@retry(retryable_exceptions=(Exception,))
def mark_seen(url: str) -> None:
    """Mark URL as seen in Redis."""
    try:
        redis_client = get_redis_client("collector")
        redis_client.sadd("seen_urls", url)
        logger.debug(f"Marked URL as seen: {url}")
    except Exception as e:
        logger.error(f"Redis error marking URL as seen: {e}")

@retry(retryable_exceptions=(Exception,))
def publish_raw(article):
    """Publish raw article to Redis stream."""
    try:
        redis_client = get_redis_client("collector")
        
        raw_msg = RawArticle(
            id=article.id,
            title=article.title,
            url=str(article.url),
            summary=article.summary or "",
            categories=",".join(article.categories),
            published_at=article.published_at,
            source=article.source,
        )
        
        message_id = redis_client.xadd(
            "raw_articles",
            raw_msg.model_dump(),
            maxlen=1000,
            approximate=True
        )
        logger.info(f"Published raw article to stream: {message_id}")
        
    except Exception as e:
        logger.error(f"Error publishing raw article: {e}")
        raise
