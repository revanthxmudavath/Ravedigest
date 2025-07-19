import uuid
from sqlalchemy import Column, Text, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from shared.db.pg import Base

class ArticleORM(Base):
    __tablename__ = 'rave_articles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    author = Column(Text, nullable=True)
    categories = Column(ARRAY(Text), nullable=False, default=[])
    published_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=False)
    inserted_at = Column(DateTime, server_default=func.now(), nullable=False)