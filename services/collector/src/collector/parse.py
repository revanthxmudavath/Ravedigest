import feedparser
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from collector.article import Article

from email.utils import parsedate_to_datetime

def parse_timestamp(source: str, ts_raw: str) -> datetime:
    """
    Try ISO8601 first, then fall back to RFC-style dates.
    Returns a naive UTC datetime, or None if parsing fails.
    """
    if not isinstance(ts_raw, str) or not ts_raw.strip():
        return None

    # ISO: e.g. “2025-07-16T20:54:01+00:00” or “2025-07-16T20:54:01Z”
    try:
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        pass

    # RFC: e.g. “Wed, 16 Jul 2025 20:54:01 +0000”
    try:
        dt = parsedate_to_datetime(ts_raw)
        return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        return None

def parse_feed(url: str, source: str) -> List[Article]:
    feed = feedparser.parse(url)
    entries = []
    for item in feed.entries:
        try:
            
            title = item.get("title", "").strip()
            link = item.get("link", "").strip()

            desc = item.get("description") or item.get("summary", "")
            if not desc and item.get("content"):
                desc = item.content[0].value
            
            published = None
            if item.get("published_parsed"):
                published = datetime(*item.published_parsed[:6])
            else:
                # fall back to raw strings
                raw_ts = item.get("published") or item.get("updated") or ""
                published = parse_timestamp(source, raw_ts)
            
            categories = [cat.term if hasattr(cat, "term") else cat for cat in item.get("tags", [])]
            
            article = Article(
                id=uuid4(),
                title=title,
                url=link,
                summary=desc,
                categories=categories,
                published_at=published,
                source=source
            )
            entries.append(article)
            
        except Exception as e:
            print(f"Error parsing feed {url}: {e}")
            continue
    
    return entries