from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    queryId: Optional[str] = None
    userJourneyId: Optional[str] = None
    tenantId: Optional[str] = None
    sessionId: Optional[str] = None
