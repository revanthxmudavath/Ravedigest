import uuid

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from shared.database.base import Base


class Digest(Base):
    """Database model for composed digests."""

    __tablename__ = "digests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    source = Column(String, nullable=False, index=True)
    inserted_at = Column(DateTime, server_default=func.now(), nullable=False)
