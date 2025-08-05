# services/analyzer/app/crud.py

import logging
from shared.database.session import SessionLocal
from shared.database.models.article import Article
from shared.schemas.messages import EnrichedArticle

logger = logging.getLogger("analyzer.crud")
logger.setLevel(logging.INFO)

def save_enriched_to_db(enriched: EnrichedArticle) -> None:
    """
    Insert or update an Article row based on the EnrichedArticle payload.
    """
    with SessionLocal() as session:
        existing = session.get(Article, enriched.id)
        if existing:
            existing.summary = enriched.summary
            existing.relevance_score = enriched.relevance_score
            existing.developer_focus = enriched.developer_focus
            session.commit()
            logger.info(f"[DB] Updated Article {enriched.id}")
        else:
            new = Article(
                id=enriched.id,
                title=enriched.title,
                url=enriched.url,
                categories=enriched.categories,
                published_at=enriched.published_at,
                source=enriched.source,
                summary=enriched.summary,
                relevance_score=enriched.relevance_score,
                developer_focus=enriched.developer_focus,
            )
            session.add(new)
            session.commit()
            logger.info(f"[DB] Inserted Article {enriched.id}")
