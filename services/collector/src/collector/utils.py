#services/collector/src/collector/utils.py
import redis
import logging

from shared.database.models.article import Article
from shared.schemas.messages import RawArticle
from collector.redis_client import get_redis_client
from redis import Redis

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

def publish_raw(article):
    r: Redis = get_redis_client()

    try:
        raw_msg = RawArticle(
        id=article.id,
        title=article.title,
        url=str(article.url),
        summary=article.summary or "",
        categories=",".join(article.categories),
        published_at=article.published_at,
        source=article.source,
    )
    
        r.xadd(
        "raw_articles",
        raw_msg.model_dump(),
        maxlen=1000,
        approximate=True
    )
        logger.info("Composer server : Message hit Redis ")
    except Exception as e:
        logger.error(f"Error publishing raw article: {e}")
