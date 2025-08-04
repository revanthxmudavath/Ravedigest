import re 
import logging 

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def markdown_to_blocks(md: str) -> list[dict]:
    logger.info("📄 Starting markdown-to-Notion block parsing")

    blocks = []
    articles = re.split(r"\n## \d+\.\s", md)[1:]
    logger.info("🧾 Detected %d article sections", len(articles) - 1)

    for idx, raw in enumerate(articles):
        raw = raw.strip()
        if not raw:
            continue 

        logger.debug("🔍 Parsing article #%d", idx)

        title_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", raw)
        title = title_match.group(1) if title_match else "Untitled"
        url = title_match.group(2) if title_match else ""

        source_match = re.search(r"\*\*Source:\*\*\s*(.+)", raw)
        source = source_match.group(1) if source_match else "Unknown"

        summary_match = re.search(r"\*\*Summary:\*\*\s*(.+)", raw, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        logger.debug("Title: %s | Source: %s | URL: %s", title, source, url)

        blocks.extend([
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content" : f"🔹 {title}", "link": {"url": url} if url else None}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"🌐 Source: {source}"}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"📝 Summary: {summary}"}
                    }]
                }   
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"🔗 Read More", "link": {"url": url} if url else None}
                    }]
                }
            },
            {"object": "block", "type": "divider", "divider": {}}
        ])

    logger.info("✅ Finished building %d Notion blocks", len(blocks))
    return blocks

