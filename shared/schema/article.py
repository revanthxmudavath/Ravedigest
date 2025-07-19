from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class Article(BaseModel):
    title: str
    url: HttpUrl
    summary: Optional[str] = ""
    author: Optional[str] = None
    categories: List[str] = []
    published_at: Optional[datetime] = None
    source: str