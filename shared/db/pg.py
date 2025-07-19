from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os 
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")

engine = create_engine(POSTGRES_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


