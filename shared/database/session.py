from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from .models.article import Article
import os 
from dotenv import load_dotenv
import logging
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")

# POSTGRES_URL = (
#     f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
#     f"@postgres:5432/{os.getenv('POSTGRES_DB')}"  
# )

logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

print("▶︎ Connecting to POSTGRES_URL =", POSTGRES_URL)
engine = create_engine(POSTGRES_URL, echo=True)  

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    logging.info("✅ DB initialized")

# init_db()