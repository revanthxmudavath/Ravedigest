from shared.database.session import SessionLocal
from shared.database.models.article import Article
from sqlalchemy.exc import IntegrityError

def save_articles_to_db(article_data):
    session = SessionLocal()
    article = Article(
        id=article_data.id,
        title=article_data.title,
        url=str(article_data.url),
        summary=article_data.summary,
        categories=article_data.categories,
        published_at=article_data.published_at,
        source=article_data.source
    )

    try:
        session.add(article)
        session.commit()
        print(f"✅ Article saved: {article.title[:20]}…")
    except IntegrityError:
        session.rollback()
        print(f"Article with ID {article.id} already exists.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error saving article: {e}")
    finally:
        session.close()

   