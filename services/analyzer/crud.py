# services/analyzer/app/crud.py

from shared.database.session import SessionLocal
from shared.database.models.article import Article
from shared.schemas.messages import EnrichedArticle
from shared.app_logging.logger import get_logger
from shared.utils.retry import retry

logger = get_logger("analyzer.crud")

@retry(retryable_exceptions=(Exception,))
def save_enriched_to_db(enriched: EnrichedArticle) -> None:
    """
    Insert or update an Article row based on the EnrichedArticle payload.
    """
    session = SessionLocal()
    try:
        existing = session.get(Article, enriched.id)
        if existing:
            existing.summary = enriched.summary
            existing.relevance_score = enriched.relevance_score
            existing.developer_focus = enriched.developer_focus
            session.commit()
            logger.info(f"Updated Article {enriched.id} with developer_focus={enriched.developer_focus}")
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
            logger.info(f"Inserted Article {enriched.id} with developer_focus={enriched.developer_focus}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving enriched article {enriched.id}: {e}")
        raise
    finally:
        session.close()
