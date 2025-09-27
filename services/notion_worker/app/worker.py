# services.notion_worker.app.worker.py
import asyncio

import redis

from services.notion_worker.app.markdown_parser import markdown_to_blocks
from services.notion_worker.app.notion_client import (
    DATABASE_ID,
    notion,
    publish_to_notion,
)
from services.notion_worker.app.utils import retry_with_backoff
from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings
from shared.database.models.digest import Digest
from shared.database.session import SessionLocal
from shared.schemas.messages import DigestReady
from shared.utils.redis_client import get_redis_client

logger = get_logger("notion.worker")
settings = get_settings()

STREAM_KEY = "digest_stream"
GROUP_NAME = f"{settings.service.consumer_group_prefix}-notion"
CONSUMER_NAME = "notion_consumer_1"


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
            entries = redis_client.xreadgroup(
                group, consumer, {stream: ">"}, block=5000, count=10
            )
            if not entries:
                await asyncio.sleep(1)
                continue

            for _, messages in entries:
                for msg_id, payload in messages:
                    try:
                        event = DigestReady(**payload)

                        # Check if already processed
                        if redis_client.get(f"digest_published:{event.digest_id}"):
                            logger.info(
                                "⚠️ Digest %s already published. Skipping.",
                                event.digest_id,
                            )
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
                                        "title": {
                                            "rich_text": [
                                                {"text": {"content": digest.title}}
                                            ]
                                        },
                                        "url": {
                                            "rich_text": [
                                                {"text": {"content": digest.url}}
                                            ]
                                        },
                                        "source": {
                                            "rich_text": [
                                                {"text": {"content": digest.source}}
                                            ]
                                        },
                                        "summary": {
                                            "rich_text": [
                                                {
                                                    "text": {
                                                        "content": digest.summary[:2000]
                                                    }
                                                }
                                            ]
                                        },
                                        "inserted_at": {
                                            "date": {
                                                "start": digest.inserted_at.isoformat()
                                            }
                                        },
                                    }
                                    return notion.pages.create(
                                        parent={"database_id": DATABASE_ID},
                                        properties=props,
                                        children=blocks,
                                    )

                                resp = retry_with_backoff(post_page)
                                redis_client.set(
                                    f"digest_published:{event.digest_id}", 1, ex=86400
                                )
                                logger.info("Notion page created: %s", resp.get("url"))
                            else:
                                logger.error(
                                    "Digest %s not found in DB", event.digest_id
                                )

                            redis_client.xack(stream, group, msg_id)

                        finally:
                            db.close()

                    except Exception as e:
                        logger.exception("Error handling message %s: %s", msg_id, e)

        except Exception as e:
            logger.error(f"Error in async consumer loop: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(0.2)
