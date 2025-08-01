from fastapi import FastAPI, Depends, HTTPException
from shared.database.session import SessionLocal
from services.composer.app.crud import get_top_articles, create_digest
from services.composer.app.redis_client import publish_digest_ready
from services.composer.app.template_engine import get_template, render
import uuid 
from services.composer.app.schema import DigestOut
import logging 


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/compose/health")
def health():
    return {"status": "ok"}

@app.post("/compose", response_model=DigestOut)
def compose(db=Depends(get_db)):
    try:
        logger.info("Fetching Top Articles")
        articles = get_top_articles(db)

        logger.info("Rendering digest template")
        
        summary = render("digest.md.j2", title="Today", articles=articles)
    
        digest_id = uuid.uuid4()
        url = f"/digests/{digest_id}"
        source = "AI-Tech"

        logger.info("Persisting digest %s", digest_id)
        digest = create_digest(
            db,
            title="Today’s Digest",
            summary=summary,
            url=url,
            source=source,
        )

        logger.info("Publishing digest_ready for %s", digest.id)
        publish_digest_ready(str(digest.id))

        return DigestOut(
            digest_id=digest.id,
            title=digest.title,
            summary=digest.summary,
            url=digest.url,
            source=digest.source,
        )

    except Exception as e:
        logger.exception("Unexpected error in /compose")
        raise HTTPException(status_code=500, detail="Internal Server Error")
   