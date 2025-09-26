from sqlalchemy.orm import Session

from shared.app_logging.logger import get_logger
from shared.database.models.article import Article
from shared.database.models.digest import Digest
from shared.utils.retry import retry

logger = get_logger("composer.crud")

@retry(retryable_exceptions=(Exception,))
def get_top_articles(db: Session, limit: int = 20):
    """Get top developer-focused articles ordered by relevance score."""
    logger.info("Querying top %d developer-focused articles", limit)
    try:
        articles = (
            db.query(Article)
            .filter(Article.developer_focus.is_(True))
            .order_by(Article.relevance_score.desc())
            .limit(limit)
            .all()
        )
        logger.info(f"Found {len(articles)} developer-focused articles")
        return articles
    except Exception as e:
        logger.error(f"Error querying top articles: {e}")
        raise

@retry(retryable_exceptions=(Exception,))
def create_digest(
        db: Session, 
        title: str, 
        summary: str,
        url: str,
        source: str,
    ) -> Digest:
    """Create a new digest in the database."""
    try:
        digest = Digest(
            title=title, 
            summary=summary,
            url=url,
            source=source,
        )
        db.add(digest)
        db.commit()
        db.refresh(digest)
        logger.info(f"Created digest: {digest.id}")
        return digest
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating digest: {e}")
        raise