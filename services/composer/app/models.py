from sqlalchemy import Column, Text, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
import uuid 
from datetime import datetime
# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from shared.database.base import Base

class Digest(Base):

    __tablename__ = "digests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    source = Column(String, nullable=False, index=True)
    inserted_at = Column(DateTime, server_default=func.now(), nullable=False)