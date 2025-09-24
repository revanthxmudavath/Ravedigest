#services/analyzer/main.py
from fastapi import FastAPI, Response
from shared.database.session import init_db
from shared.schemas.messages import EnrichedArticle, RawArticle
from shared.config.settings import get_settings
from shared.logging.logger import setup_logging, get_logger
from shared.utils.health import create_analyzer_health_checker
from shared.utils.redis_client import get_redis_client
from shared.utils.retry import async_retry
import asyncio 
import os
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from services.analyzer.crud import save_enriched_to_db
from services.analyzer.summarize import summarize_articles
from services.analyzer.filter import mark_developer_focus
import httpx
from readability import Document
from bs4 import BeautifulSoup

# Setup logging
logger = setup_logging("analyzer")

ARTICLE_PROCESSED = Counter("analyzer_article_processed_total", "Total number of articles processed")

app = FastAPI(title="Rave Digest Analyzer", description="Analyzes articles for developer focus and summarizes them.")

# Get configuration
settings = get_settings()


# Create health checker
health_checker = create_analyzer_health_checker()

async def on_startup():
    logger.info("Starting Analyzer service...")
    init_db()  # Initialize the database connection
    logger.info("Database initialized successfully.")

    try:
        # Test Redis connection
        redis_client = get_redis_client("analyzer")
        redis_client.ping()
        logger.info("Redis connection established successfully")

        asyncio.create_task(process_raw_stream())
        logger.info("Launched background task to process raw articles.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

app.add_event_handler("startup", on_startup)

@app.get("/analyzer/health")
def health():
    """Comprehensive health check endpoint."""
    return health_checker.run_all_checks()

@app.get("/analyzer/health/live")
def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "service": "analyzer"}

@app.get("/analyzer/health/ready")
def readiness_check():
    """Readiness check endpoint."""
    health_data = health_checker.run_all_checks()
    critical_checks = [check for check in health_data["checks"] 
                      if check["name"] in ["database", "redis", "openai"]]
    all_critical_healthy = all(check["status"] == "healthy" for check in critical_checks)
    
    return {
        "status": "ready" if all_critical_healthy else "not_ready",
        "service": "analyzer",
        "critical_dependencies": {
            check["name"]: check["status"] for check in critical_checks
        }
    }

@app.get("/analyzer/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    data = generate_latest()
    logger.debug("Metrics endpoint called.")
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@async_retry(max_retries=3, base_delay=1.0, backoff_factor=2.0)
async def safe_summarize(text):
    """Safely summarize text with retry logic."""
    try:
        return summarize_articles(text)
    except Exception as e:
        logger.warning(f"LLM error: {e}")
        raise

@async_retry(max_retries=3, base_delay=1.0, backoff_factor=2.0)
async def fetch_and_extract(url: str) -> str:
    """Fetch and extract text content from URL with retry logic."""
    try:
        async with httpx.AsyncClient(
            timeout=settings.service.http_timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            
            doc = Document(response.text)
            html = doc.summary()

            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return text or ""
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        raise

async def handle_message(payload, msg_id, r, stream, group):
    """Handle a single message from the raw articles stream."""
    try:
        raw = RawArticle(**payload)
        logger.info(f"Processing article: {raw.title[:50]}...")
        
        # Extract and summarize content
        content = await fetch_and_extract(raw.url)
        summary, score = await safe_summarize(content)
        
        # Check developer focus
        dev_focus = mark_developer_focus(raw.title, summary)
        
        # Create enriched article
        raw_dict = raw.model_dump(exclude={"summary"})
        enriched = EnrichedArticle(
            **raw_dict,
            summary=summary,
            relevance_score=score,
            developer_focus=dev_focus
        )

        # Save to database
        save_enriched_to_db(enriched)
        ARTICLE_PROCESSED.inc()

        # Publish to enriched articles stream
        redis_client = get_redis_client("analyzer")
        redis_client.xadd(
            "enriched_articles",
            enriched.model_dump(),
            maxlen=settings.service.stream_max_length,
            approximate=True
        )

        # Acknowledge message
        redis_client.xack(stream, group, msg_id)
        logger.info(f"✅ Processed & acknowledged message {msg_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing message {msg_id}: {e}")
        # Don't acknowledge failed messages - they'll be retried
        raise


async def process_raw_stream():
    """Process messages from the raw articles stream."""
    group = f"{settings.service.consumer_group_prefix}-analyzer"
    consumer = "analyzer-1"
    stream = "raw_articles"

    redis_client = get_redis_client("analyzer")
    
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Consumer group %s created on stream %s", group, stream)

        # Process any pending messages
        pending = redis_client.xpending_range(stream, group, '-', '+', 10)
        for entry in pending:
            msg_id = entry['message_id']
            logger.warning(f"Found unacked message {msg_id}, reclaiming...")
            messages = redis_client.xrange(stream, min=msg_id, max=msg_id)
            for _, payload in messages:
                await handle_message(payload, msg_id, redis_client, stream, group)

    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group %s already exists", group)
        else:
            logger.error(f"Error creating consumer group: {e}")
            raise
    
    logger.info("Starting message processing loop...")
    while True:
        try:
            logger.debug("Waiting for new messages on stream %s", stream)
            entries = redis_client.xreadgroup(group, consumer, {stream: ">"}, count=10, block=5000)

            if not entries:
                continue 

            for _, messages in entries:
                for msg_id, payload in messages:
                    logger.info("Processing message %s", msg_id)
                    try:
                        await handle_message(payload, msg_id, redis_client, stream, group)
                    except Exception as e:
                        logger.error(f"Error processing message {msg_id}: {e}")
                        # Message will be retried on next iteration
            
            await asyncio.sleep(0.7)  # Avoid busy-waiting
            
        except Exception as e:
            logger.error(f"Error in message processing loop: {e}")
            await asyncio.sleep(5)  # Wait before retrying



