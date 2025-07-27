from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

class Article(BaseModel):
    id: UUID
    title: str
    url: str
    summary: Optional[str]
    categories: List[str]
    published_at: Optional[datetime]
    source: str
