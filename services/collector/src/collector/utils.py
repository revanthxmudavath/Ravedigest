import redis
import logging

from shared.database.models.article import Article

logger = logging.getLogger(__name__)

# Initialize Redis client with retry logic
redis_client = redis.Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    socket_timeout=5,
    retry_on_timeout=True,
    max_connections=10
)

def is_duplicate(url: str) -> bool:
    try:
        return redis_client.sismember("seen_urls", url)
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Redis error: {e}")
        return False

def mark_seen(url: str) -> None:
    try:
        redis_client.sadd("seen_urls", url)
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
    except Exception as e:
        logger.error(f"Redis error: {e}")

def publish_raw(article: Article) -> None:
    try:
        redis_client.xadd(
            "raw_articles",
            {
            "id": str(article.id),
            "title": article.title,
            "url": str(article.url),
            "feed_summary": article.summary or "",
            "categories": ",".join(article.categories),
            "published_at": article.published_at.isoformat() if article.published_at else "",
            "source": article.source,  
            },
            maxlen=1000,
            approximate=True   
        )
    except Exception as e:
        logger.error(f"Error publishing raw article: {e}")
