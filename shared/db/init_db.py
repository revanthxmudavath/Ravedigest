
from shared.db.pg import Base, engine
from shared.db import models
import logging 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init():
    logger.info("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Done.")

if __name__ == "__main__":
    init()
