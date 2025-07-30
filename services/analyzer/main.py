from fastapi import FastAPI, Response
from shared.database.session import SessionLocal, init_db
from shared.database.models.article import Article
import asyncio 
import os
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import redis
from services.analyzer.summarize import summarize_articles
from services.analyzer.filter import mark_developer_focus
import logging 
from dotenv import load_dotenv
import httpx
from readability import Document
from bs4 import BeautifulSoup
from sqlalchemy import text as sql_text, update
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
    url = payload["url"]
    source = payload["source"]
    text = await fetch_and_extract(url)
    if not text:
        logger.warning(f"Failed to extract text from source: {source}")
        r.xack(stream, group, msg_id)
        return  # Stop processing if text extraction failed
    
    summary, score = await safe_summarize(text)

    title = payload["title"]
    dev_focus = bool(mark_developer_focus(title, summary))
    article_id = payload["id"]

    summary = str(summary)
    score = float(score)
    

    with SessionLocal() as session:
        # stmt = (
        #     update(Article)
        #     .where(Article.id == article_id)
        #     .values(
        #         summary=summary,
        #         relevance_score=score,
        #         developer_focus=dev_focus
        #     )
        # )
        
        # session.execute(stmt)
        ar = session.get(Article, article_id)
        if ar:
            ar.summary = summary
            ar.relevance_score = score
            ar.developer_focus = dev_focus
            session.commit()
            logger.info(f"Updated article {article_id} with summary and relevance score.")

    ARTICLE_PROCESSED.inc()

    enriched = {
        **payload,
        "summary": summary,
        "relevance_score": score,
        "developer_focus": str(dev_focus).lower(), # Store as string for Redis compatibility
    }

    r.xadd("enriched_articles", enriched)
    r.xack(stream, group, msg_id)
    logger.info("Processed and ACKed message %s", msg_id)


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



