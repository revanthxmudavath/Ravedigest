#services/analyzer/main.py
from fastapi import FastAPI, Response
from shared.database.session import init_db
from shared.schemas.messages import EnrichedArticle, RawArticle
import asyncio 
import os
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import redis
from services.analyzer.crud import save_enriched_to_db
from services.analyzer.summarize import summarize_articles
from services.analyzer.filter import mark_developer_focus
import logging 
from dotenv import load_dotenv
import httpx
from readability import Document
from bs4 import BeautifulSoup
load_dotenv()


logger = logging.getLogger("analyzer")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

ARTICLE_PROCESSED = Counter("analyzer_article_processed_total", "Total number of articles processed")

app = FastAPI(title="Rave Digest Analyzer", description="Analyzes articles for developer focus and summarizes them.")


async def on_startup():
    logger.info("Starting Analyzer service...")
    init_db()  # Initialize the database connection
    logger.info("Db initialized successfully.")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    logger.info(f"Using Redis URL: {redis_url}")
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        app.state.redis = r

        asyncio.create_task(process_raw_stream())
        logger.info("Launched background task to process raw articles.")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

app.add_event_handler("startup", on_startup)

@app.get("/analyzer/health")
def health():
    logger.debug("Health check endpoint called.")
    return {"status": "ok"}

@app.get("/analyzer/metrics")
def metrics():
    data = generate_latest()
    logger.debug("Metrics endpoint called.")
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def safe_summarize(text):
    for attempt in range(3):
        try:
            return summarize_articles(text)
        except Exception as e:
            logger.warning(f"LLM error (attempt {attempt+1}): {e}")
            await asyncio.sleep(2 ** attempt)  # exponential backoff
    raise RuntimeError("LLM failed after 3 retries")

async def fetch_and_extract(url: str) -> str:
    try:
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5.0)
        r.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""
    
    doc = Document(r.text)
    html = doc.summary()

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text or ""

async def handle_message(payload, msg_id, r, stream, group):
    
    raw = RawArticle(**payload)
    summary, score = await safe_summarize(await fetch_and_extract(raw.url))
    dev_focus = mark_developer_focus(raw.title, summary)
    raw_dict = raw.model_dump(exclude={"summary"})
    enriched = EnrichedArticle(
        **raw_dict,
        summary=summary,
        relevance_score=score,
        developer_focus=dev_focus
    )

    save_enriched_to_db(enriched)
    ARTICLE_PROCESSED.inc()

    r.xadd(
        "enriched_articles",
        enriched.model_dump(),
        maxlen=1000,
        approximate=True
    )

    r.xack(stream, group, msg_id)
    logger.info("Processed & Acked message %s", msg_id)


async def process_raw_stream():
    group, consumer = "analyzer-group", "analyzer-1"
    stream = "raw_articles"

    r = app.state.redis
    try:
        r.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Consumer group %s created on stream %s", group, stream)

        pending = r.xpending_range(stream, group, min='-', max='+', count=10)
        for entry in pending:
            msg_id = entry['message_id']
            logger.warning(f"Found unacked message {msg_id}, reclaiming...")
            messages = r.xrange(stream, min=msg_id, max=msg_id)
            for _, payload in messages:
                await handle_message(payload, msg_id, r , stream, group)


    except redis.exceptions.ResponseError as e:
        logger.info("Consumer group %s already exists", group)
    
    while True:
        logger.debug("Waiting for new messages on stream %s", stream)
        entries = r.xreadgroup(group, consumer, {stream: ">"}, count=10, block=5000)

        if not entries:
            continue 

        for _, messages in entries:
            for msg_id, payload in messages:
                logger.info("Processing message %s", msg_id)
                try:
                    await handle_message(payload, msg_id, r, stream, group)

                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {e}")
        
        await asyncio.sleep(0.7)  # Avoid busy-waiting



