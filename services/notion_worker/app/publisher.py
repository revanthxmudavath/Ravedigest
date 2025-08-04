import logging
from services.notion_worker.app.notion_client import notion, DATABASE_ID
from services.notion_worker.app.utils import retry_with_backoff
from shared.database.session import SessionLocal
from services.composer.app.models import Digest
from services.notion_worker.app.markdown_parser import markdown_to_blocks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def publish_latest_digest():
    db = SessionLocal()
    try:
        latest_digest = db.query(Digest).order_by(Digest.inserted_at.desc()).first()
        if not latest_digest:
            raise ValueError("No digest found in database")

        blocks = markdown_to_blocks(latest_digest.summary)

        def post_to_notion():
            return notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties={
                    "title": {
                        "rich_text": [{"text": {"content": latest_digest.title}}]
                    },
                    "url": {
                        "rich_text": [{"text": {"content": latest_digest.url}}]
                    },
                    "source": {
                        "rich_text": [{"text": {"content": latest_digest.source}}]
                    },
                    "summary": {
                        "rich_text": [{"text": {"content": latest_digest.summary[:2000]}}]
                    },
                    "inserted_at": {
                        "date": {"start": latest_digest.inserted_at.isoformat()}
                    }
                },
                children=blocks
            )
        
        logger.info("📤 Sending digest to Notion...")
        response = retry_with_backoff(post_to_notion, retries=3)
        logger.info("✅ Notion page created: %s", response.get("url", ""))

        return response.get("url", "")

    finally:
        db.close()
