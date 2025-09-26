#   services/composer/app/worker.py

import asyncio

from services.composer.app.digest_utils import (generate_and_publish_digest,
                                                get_db)
from shared.app_logging.logger import get_logger
from shared.config.settings import get_settings
from shared.schemas.messages import EnrichedArticle
from shared.utils.redis_client import get_redis_client

logger = get_logger("composer.worker")
settings = get_settings()

async def consume_enriched():
    """Consume enriched articles and generate digests."""
    redis_client = get_redis_client("composer")
    stream = "enriched_articles"
    group = f"{settings.service.consumer_group_prefix}-composer"
    consumer = "composer-1"

    # Create consumer group
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Created group %s on %s", group, stream)
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info("Group %s already exists", group)
        else:
            logger.error(f"Error creating consumer group: {e}")
            raise

    logger.info("Starting enriched articles consumer...")
    
    # Poll for new messages
    while True:
        try:
            entries = redis_client.xreadgroup(group, consumer, {stream: ">"}, block=5000)
            if entries:
                for _, msgs in entries:
                    for msg_id, payload in msgs:
                        try:
                            # Validate message schema
                            EnrichedArticle(**payload)
                            
                            # Generate digest
                            with next(get_db()) as db:
                                logger.info("📩 Received enriched article %s; composing digest", msg_id)
                                generate_and_publish_digest(db)

                            # Acknowledge message
                            redis_client.xack(stream, group, msg_id)
                            logger.info("✅ Acknowledged %s", msg_id)

                        except Exception as e:
                            logger.exception("❌ Failed processing %s: %s", msg_id, e)
                            
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying
            
        await asyncio.sleep(0.2)