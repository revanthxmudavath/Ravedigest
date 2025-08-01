from sqlalchemy.orm import Session
from shared.database.models.article import Article
from services.composer.app.models import Digest
import logging

logger = logging.getLogger(__name__)

def get_top_articles(db: Session, limit: int = 20):
    logger.info("Querying top %d developer-focused articles", limit)
    return (
        db.query(Article)
        .filter(Article.developer_focus.is_(True))
        .order_by(Article.relevance_score.desc())
        .limit(limit)
        .all()
    )

def create_digest(
        db: Session, 
        title: str, 
        summary: str,
        url: str,
        source: str,
        
    ) -> Digest:
    
    
    d = Digest(
        title=title, 
        summary=summary,
        url=url,
        source=source,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d