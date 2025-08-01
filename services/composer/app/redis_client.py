import os
import logging 
import redis
from redis.exceptions import RedisError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_DB = int(os.getenv("REDIS_DB"))

_client: redis.Redis | None = None 

def get_redis_client() -> redis.Redis:
    global _client 
    if _client is not None:
        return _client 
    
    try:
        if REDIS_URL:
            client = redis.Redis.from_url(REDIS_URL)
            logger.info("Connecting to Redis via from_url")
        else:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
            logger.info("Connecting to Redis via Redis function")

        client.ping()
        logger.info("✅ Connected to Redis at %s:%d db=%d", REDIS_HOST, REDIS_PORT, REDIS_DB)
        _client = client
        return client
    except RedisError as e:
        logger.exception("❌ Failed to connect to Redis: %s", e)
        raise

def publish_digest_ready(digest_id: str) -> None:
    
    client = get_redis_client()
    try:
        payload = {"digest_id": digest_id}
        client.xadd("digest_stream", payload)
        logger.info("Published digest_ready event: %r", payload)
    except RedisError as e:
        logger.exception("Failed to publish digest_ready for %s: %s", digest_id, e)
        raise