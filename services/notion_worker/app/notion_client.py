# services.notion_worker.app.notion_client.py
import os

from notion_client import Client

from services.notion_worker.app.markdown_parser import markdown_to_blocks
from shared.schemas.messages import DigestReady

notion = Client(auth=os.getenv("NOTION_API_KEY"))
DATABASE_ID = os.getenv("NOTION_DB_ID")


def publish_to_notion(event: DigestReady) -> str:
    """
    Converts markdown summary to Notion blocks and creates a page.
    Returns the Notion page URL.
    """
    blocks = markdown_to_blocks(event.summary)

    # Create page properties
    properties = {
        "title": {"rich_text": [{"text": {"content": event.title}}]},
        "url": {"rich_text": [{"text": {"content": event.url}}]},
        "source": {"rich_text": [{"text": {"content": event.source}}]},
        "inserted_at": {"date": {"start": event.inserted_at.isoformat()}},
    }

    # Create page using the correct API
    page = notion.pages.create(
        parent={"database_id": DATABASE_ID}, properties=properties, children=blocks
    )

    return page["url"]
