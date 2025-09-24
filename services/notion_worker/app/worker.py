#services.notion_worker.app.worker.py
import asyncio
import redis
from shared.schemas.messages import DigestReady
from shared.database.session import SessionLocal
from services.composer.app.models import Digest
from services.notion_worker.app.notion_client import notion, DATABASE_ID
from services.notion_worker.app.markdown_parser import markdown_to_blocks
from services.notion_worker.app.utils import retry_with_backoff
from services.notion_worker.app.notion_client import publish_to_notion
from shared.config.settings import get_settings
from shared.app_logging.logger import get_logger
from shared.utils.redis_client import get_redis_client

logger = get_logger("notion.worker")
settings = get_settings()

STREAM_KEY = "digest_stream"
GROUP_NAME = f"{settings.service.consumer_group_prefix}-notion"
CONSUMER_NAME = "notion_consumer_1"

def ensure_group_exists(client: redis.Redis):
    """Ensure consumer group exists for the stream."""
    try:
        groups = client.xinfo_groups(STREAM_KEY)
        if not any(g["name"] == GROUP_NAME for g in groups):
            client.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
            logger.info(f"✅ Created consumer group: {GROUP_NAME}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group {GROUP_NAME} already exists")
        else:
            logger.error(f"Error creating consumer group: {e}")
            raise

def consume_enriched():
    """Consume digest messages and publish to Notion."""
    client = get_redis_client("notion_worker")
    ensure_group_exists(client)

    logger.info("🚀 Starting Redis group consumer...")

    while True:
        try:
            response = client.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=1,
                block=5000
            )

            if response:
                for stream_key, messages in response:
                    for message_id, fields in messages:
                        try:
                            logger.info(f"📩 Received message {message_id}")
                            payload = {k.decode(): v.decode() for k, v in fields.items()}
                            event = DigestReady(**payload)

                            notion_url = publish_to_notion(event)
                            logger.info(f"✅ Published to Notion: {notion_url}")

                            # Acknowledge after success
                            client.xack(STREAM_KEY, GROUP_NAME, message_id)
                            logger.info(f"🧾 Acknowledged message {message_id}")

                        except Exception as e:
                            logger.exception(f"❌ Failed to process message {message_id}: {e}")

        except Exception as e:
            logger.error(f"🔁 Redis consumer error: {e}")
            import time
            time.sleep(5)



async def consume_digest_stream():
    """Async consumer for digest stream messages."""
    stream, group, consumer = "digest_stream", GROUP_NAME, CONSUMER_NAME
    redis_client = get_redis_client("notion_worker")

    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info(f"Created consumer group {group} for stream {stream}")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating consumer group: {e}")
            raise

    logger.info("Starting async digest stream consumer...")
    seen = set()
    
    while True:
        try:
            entries = redis_client.xreadgroup(group, consumer, {stream: ">"}, block=5000, count=10)
            if not entries:
                await asyncio.sleep(1)
                continue

            for _, messages in entries:
                for msg_id, payload in messages:
                    try:
                        event = DigestReady(**payload)
                        
                        # Check if already processed
                        if redis_client.get(f"digest_published:{event.digest_id}"):
                            logger.info("⚠️ Digest %s already published. Skipping.", event.digest_id)
                            redis_client.xack(stream, group, msg_id)
                            continue

                        # Load digest from database
                        db = SessionLocal()
                        try:
                            digest = db.get(Digest, event.digest_id)
                            if digest:
                                blocks = markdown_to_blocks(digest.summary)
                                
                                def post_page():
                                    props = {
                                        "title": {"rich_text": [{"text": {"content": digest.title}}]},
                                        "url": {"rich_text": [{"text": {"content": digest.url}}]},
                                        "source": {"rich_text": [{"text": {"content": digest.source}}]},
                                        "summary": {"rich_text": [{"text": {"content": digest.summary[:2000]}}]},
                                        "inserted_at": {"date": {"start": digest.inserted_at.isoformat()}}
                                    }
                                    return notion.pages.create(
                                        parent={"database_id": DATABASE_ID},
                                        properties=props,
                                        children=blocks
                                    )
                                
                                resp = retry_with_backoff(post_page)
                                redis_client.set(f"digest_published:{event.digest_id}", 1, ex=86400)
                                logger.info("Notion page created: %s", resp.get("url"))
                            else:
                                logger.error("Digest %s not found in DB", event.digest_id)

                            redis_client.xack(stream, group, msg_id)
                            
                        finally:
                            db.close()
                            
                    except Exception as e:
                        logger.exception("Error handling message %s: %s", msg_id, e)

        except Exception as e:
            logger.error(f"Error in async consumer loop: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(0.2)
