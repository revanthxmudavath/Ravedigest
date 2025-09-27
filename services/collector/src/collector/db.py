from sqlalchemy.exc import IntegrityError

from shared.app_logging.logger import get_logger
from shared.database.models.article import Article
from shared.database.session import SessionLocal
from shared.utils.retry import retry

logger = get_logger("collector.db")


@retry(retryable_exceptions=(Exception,))
def save_articles_to_db(article_data):
    """Save article to database with retry logic."""
    session = SessionLocal()
    try:
        article = Article(
            id=article_data.id,
            title=article_data.title,
            url=str(article_data.url),
            summary=article_data.summary,
            categories=article_data.categories,
            published_at=article_data.published_at,
            source=article_data.source,
        )

        session.add(article)
        session.commit()
        logger.info(f"✅ Article saved: {article.title[:50]}...")

    except IntegrityError as e:
        session.rollback()
        logger.warning(f"Article with ID {article_data.id} already exists: {e}")
        # Don't re-raise IntegrityError as it's expected for duplicates
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Error saving article {article_data.title}: {e}")
        raise
    finally:
        session.close()
