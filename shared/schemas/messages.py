from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RawArticle(BaseModel):
    version: Literal["1.0"] = Field("1.0", description="Schema version")
    id: UUID = Field(..., description="Unique article identifier")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Canonical URL")
    summary: str = Field(..., description="Short summary from RSS or feed")
    categories: str = Field(..., description="Comma-separated categories/tags")
    published_at: datetime | None = Field(None, description="Original publication timestamp")
    source: str = Field(..., description="Origin of the article (e.g., RSS feed name)")

class EnrichedArticle(RawArticle):
    summary: str = Field(..., description="LLM-generated concise summary")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Normalized relevance from 0–1")
    developer_focus: bool = Field(..., description="Flag for developer-focused content")

class DigestReady(BaseModel):
    version: Literal["1.0"] = Field("1.0", description="Schema version")
    digest_id: UUID = Field(..., description="UUID of the generated digest")
    title: str = Field(..., description="Digest title (e.g., “Today’s Digest”)")
    url: str = Field(..., description="Path or external link to the digest")
    source: str = Field(..., description="Service name that produced the digest")
    inserted_at: datetime = Field(..., description="Timestamp when digest was created")
    summary: str = Field(..., description="Unique summary")