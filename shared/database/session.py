from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from .models.article import Article
from .models.digest import Digest
from shared.config.settings import get_settings
from shared.app_logging.logger import get_logger
import logging

logger = get_logger("database")

# Get database configuration
settings = get_settings()
POSTGRES_URL = settings.database.postgres_url

# Configure SQLAlchemy logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

logger.info(f"▶︎ Connecting to database: {POSTGRES_URL.split('@')[1] if '@' in POSTGRES_URL else 'localhost'}")

# Create engine with connection pooling
engine = create_engine(
    POSTGRES_URL, 
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

def get_db_session():
    """Get a database session with proper error handling."""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()