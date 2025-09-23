# digest_utils.py
import uuid
from services.composer.app.crud import get_top_articles, create_digest
from services.composer.app.redis_client import publish_digest_ready
from services.composer.app.template_engine import render, validate_markdown
from shared.database.session import SessionLocal
from shared.config.settings import get_settings
from shared.logging.logger import get_logger

logger = get_logger("composer.digest_utils")
settings = get_settings()

def get_db():
    """Get database session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def generate_and_publish_digest(db):
    """Generate and publish a digest from top articles."""
    try:
        logger.info("Generating digest from top articles")
        
        # Get top articles
        articles = get_top_articles(db, limit=settings.service.max_articles_per_digest)
        logger.info(f"Found {len(articles)} articles for digest")
        
        if not articles:
            logger.warning("No articles found for digest generation")
            return None
        
        # Render markdown
        md = render("digest.md.j2", title="Today", articles=articles)
        validate_markdown(md)
        
        # Create digest
        digest = create_digest(
            db, 
            title="Today's Digest", 
            summary=md, 
            url=f"/digests/{uuid.uuid4()}", 
            source="AI-Tech"
        )
        
        # Publish to stream
        publish_digest_ready(digest)
        logger.info(f"Successfully generated and published digest: {digest.id}")
        
        return digest
        
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        raise
