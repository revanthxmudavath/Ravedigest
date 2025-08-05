#services/collector/src/collector/main.py
from collector.article import Article
from collector.db import save_articles_to_db
from collector.utils import is_duplicate, mark_seen, publish_raw
from shared.database.session import init_db
import logging
from uuid import UUID
from dotenv import load_dotenv
from fastapi import FastAPI
from collector import parse 

load_dotenv()

logger = logging.getLogger("collector")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app =FastAPI(title="RaveDigest Collector Service")

app.add_event_handler("startup", init_db)

RSS_FEEDS = [
    ("https://techcrunch.com/category/artificial-intelligence/feed", "TechCrunch AI"),
    ("https://www.wired.com/feed/tag/ai/latest/rss", "Wired AI"),
    ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge AI"),
    ("https://blog.kore.ai/rss.xml", "Kore.ai"),
    ("https://thenewstack.io/blog/feed/", "TheNewStack AI"),
]

@app.get("/health")
def health_check():
    return {"status": "Collector service is running ✅"}

@app.get("/collect/rss")
def collect_articles():
    total_collected = 0
    total_skipped = 0 

    for url, source in RSS_FEEDS:
        logger.info(f"📥 Parsing feed: {source}")
        articles = parse.parse_feed(url, source)

        for article in articles:
            if is_duplicate(article.url):
                logger.info(f"🔁 Duplicate skipped: {article.url}")
                total_skipped += 1
                continue

            try:
                save_articles_to_db(article)
                mark_seen(article.url)
                publish_raw(article)
                total_collected += 1
            except Exception as e:
                logger.error(f"❌ Error saving article {article.title}: {e}")
                continue 
    
    logger.info(f"✅ Collection complete: {total_collected} articles saved, {total_skipped} duplicates skipped.")

    return {
        "status" : "success",
        "total_collected": total_collected,
        "total_skipped": total_skipped
    }