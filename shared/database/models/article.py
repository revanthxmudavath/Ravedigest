import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from ..base import Base


class Article(Base):
    __tablename__ = 'rave_articles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    categories = Column(ARRAY(Text), nullable=False, default=list)
    published_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=False, index=True)
    relevance_score = Column(Float, nullable=True)
    developer_focus = Column(Boolean, nullable=False, default=False)
    inserted_at = Column(DateTime, server_default=func.now(), nullable=False)