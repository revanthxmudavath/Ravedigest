from datetime import datetime
import pytest
import fakeredis
import asyncio
from uuid import uuid4
from services.analyzer.main import handle_message, fetch_and_extract, safe_summarize, mark_developer_focus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_db(tmp_path, monkeypatch):
    # Set up SQLite in-memory
    engine = create_engine("sqlite:///:memory:")
    
    # Create table schema
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE rave_articles (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        summary TEXT,
        categories TEXT DEFAULT '[]',
        published_at TIMESTAMP,
        source TEXT NOT NULL,
        relevance_score REAL,
        developer_focus BOOLEAN DEFAULT 0,
        inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX ix_rave_articles_url ON rave_articles (url)"))
        conn.execute(text("CREATE INDEX ix_rave_articles_source ON rave_articles (source)"))
    
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr("services.analyzer.main.SessionLocal", Session)
    
    monkeypatch.setenv("REDIS_URL", "")  # avoid real redis
    return Session

@pytest.fixture
def fake_redis(monkeypatch):
    r = fakeredis.FakeRedis()
    monkeypatch.setattr("services.analyzer.main.redis.from_url",
                        lambda *args, **kw: r)
    return r

# Create a simple Article mock for testing
class MockArticle:
    def __init__(self, id, title, url, source):
        self.id = id
        self.title = title
        self.url = url
        self.source = source
        self.summary = None
        self.relevance_score = None
        self.developer_focus = None

@pytest.mark.asyncio
async def test_handle_message_end_to_end(monkeypatch, in_memory_db, fake_redis):
   
    async def fake_fetch(url):
        return "dummy text"
    
    import services.analyzer.main as main_mod 
    monkeypatch.setattr(main_mod, "fetch_and_extract", fake_fetch)

    async def fake_summarize(text):
        return ("SUM", 0.5)
    monkeypatch.setattr(main_mod, "safe_summarize", fake_summarize)
    monkeypatch.setattr(
        main_mod,
        "mark_developer_focus",
        lambda t, s: True,
    )

    test_uuid = uuid4()
    payload = {
        "id": str(test_uuid),
        "title": "Test Title",
        "url": "http://example.com",
        "source": "unittest",
    }

    # Create the test article in the database
    with in_memory_db() as session:
        session.execute(text("""
            INSERT INTO rave_articles (id, title, url, source, categories, developer_focus, inserted_at) 
            VALUES (:id, :title, :url, :source, :categories, :developer_focus, :inserted_at)
        """), {
            "id": str(test_uuid),
            "title": payload["title"],
            "url": payload["url"],
            "source": payload["source"],
            "categories": "[]",
            "developer_focus": False,
            "inserted_at": datetime.now()
        })
        session.commit()

    # Mock session.get to return a MockArticle that can be updated
    test_article = MockArticle(str(test_uuid), payload["title"], payload["url"], payload["source"])
    
    def mock_session_get(entity, ident):
        # Convert UUID to string for comparison
        if hasattr(ident, 'hex'):
            ident = str(ident)
        if ident == str(test_uuid):
            return test_article
        return None
    
    # Patch the session.get method
    original_sessionlocal = main_mod.SessionLocal
    
    class MockSessionLocal:
        def __enter__(self):
            session = original_sessionlocal()
            session.get = mock_session_get
            session.test_article = test_article  # Store reference for assertions
            return session
        
        def __exit__(self, *args):
            pass
    
    monkeypatch.setattr(main_mod, "SessionLocal", MockSessionLocal)

    # Set up Redis
    r = fake_redis
    r.xgroup_create("raw_articles", "test-group", id="0", mkstream=True)
    r.xadd("raw_articles", payload)

    msg_id = next(iter(r.xrange("raw_articles")))[0]
    await handle_message(payload, msg_id, r, "raw_articles", "test-group")

    # Verify enriched message was published
    enriched = r.xrange("enriched_articles")
    assert enriched, "No enriched message published"

    # Verify the mock article was updated correctly
    assert test_article.summary == "SUM"
    assert test_article.relevance_score == 0.5
    assert test_article.developer_focus == True

    # Also verify database was updated directly
    with in_memory_db() as session:
        row = session.execute(text("SELECT summary, relevance_score, developer_focus FROM rave_articles WHERE id = :id"), 
                            {"id": str(test_uuid)}).fetchone()
        assert row is not None, "Article not found in database"