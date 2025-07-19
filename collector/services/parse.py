import feedparser 

def parse_feed(url: str, source_name: str):

    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        articles.append({
            "title": entry.get("title"),
            "url": entry.get("link"),
            "summary": entry.get("summary") or entry.get("description") or "",
            "author": entry.get("author", None),
            "categories": [cat.term if hasattr(cat, 'term') else str(cat) for cat in entry.get("tags", [])],
            "published_at": entry.get("published") or entry.get("updated"),
            "source": source_name
        })

    return articles 

