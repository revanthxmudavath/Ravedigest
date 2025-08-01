import logging 
from uuid import UUID
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DigestOut(BaseModel):
    digest_id: UUID = Field(..., description="The UUID of the created digest")
    title: str = Field(..., description="The title of the digest")
    summary: str = Field(..., description="Description of the digest") 
    url: str = Field(..., description="The public URL of the digest")
    source: str = Field(..., description="Which service published this digest")

    class Config:
        orm_mode = True

logger.info("pydantic schema initiated: DigestOut")


