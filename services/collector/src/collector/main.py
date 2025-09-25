#services/collector/src/collector/main.py
from collector.article import Article
from collector.db import save_articles_to_db
from collector.utils import is_duplicate, mark_seen, publish_raw
from shared.database.session import init_db
from shared.config.settings import get_settings
from shared.app_logging.logger import setup_logging, get_logger
from shared.utils.health import create_collector_health_checker
from uuid import UUID
from fastapi import FastAPI, HTTPException
from collector import parse 

# Setup logging
logger = setup_logging("collector")

app = FastAPI(title="RaveDigest Collector Service")

app.add_event_handler("startup", init_db)

# Get configuration
settings = get_settings()
RSS_FEEDS = [(url, f"RSS Feed {i+1}") for i, url in enumerate(settings.service.rss_feeds)]

# Create health checker
health_checker = create_collector_health_checker()

@app.get("/collector/health")
def health_check():
    """Comprehensive health check endpoint."""
    return health_checker.run_all_checks()

@app.get("/collector/health/live")
def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive", "service": "collector"}

@app.get("/collector/health/ready")
def readiness_check():
    """Readiness check endpoint."""
    health_data = health_checker.run_all_checks()
    critical_checks = [check for check in health_data["checks"] 
                      if check["name"] in ["database", "redis"]]
    all_critical_healthy = all(check["status"] == "healthy" for check in critical_checks)
    
    return {
        "status": "ready" if all_critical_healthy else "not_ready",
        "service": "collector",
        "critical_dependencies": {
            check["name"]: check["status"] for check in critical_checks
        }
    }

# @app.get("/collect/rss")
# def collect_articles():
#     """Collect articles from RSS feeds."""
#     total_collected = 0
#     total_skipped = 0 
#     total_errors = 0

#     logger.info(f"🚀 Starting RSS collection from {len(RSS_FEEDS)} feeds")

#     for url, source in RSS_FEEDS:
#         try:
#             logger.info(f"📥 Parsing feed: {source}")
#             articles = parse.parse_feed(url, source)
#             logger.info(f"📄 Found {len(articles)} articles in {source}")

#             for article in articles:
#                 try:
#                     if is_duplicate(article.url):
#                         logger.debug(f"🔁 Duplicate skipped: {article.url}")
#                         total_skipped += 1
#                         continue

#                     save_articles_to_db(article)
#                     mark_seen(article.url)
#                     publish_raw(article)
#                     total_collected += 1
#                     logger.debug(f"✅ Saved article: {article.title[:50]}...")
                    
#                 except Exception as e:
#                     logger.error(f"❌ Error processing article {article.title}: {e}")
#                     total_errors += 1
#                     continue
                    
#         except Exception as e:
#             logger.error(f"❌ Error parsing feed {source}: {e}")
#             total_errors += 1
#             continue
    
#     logger.info(f"✅ Collection complete: {total_collected} articles saved, {total_skipped} duplicates skipped, {total_errors} errors")

#     return {
#         "status": "success",
#         "total_collected": total_collected,
#         "total_skipped": total_skipped,
#         "total_errors": total_errors,
#         "feeds_processed": len(RSS_FEEDS)
#     }