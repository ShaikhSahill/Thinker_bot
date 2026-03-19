from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    tenantId: Optional[str] = None
    sessionId: Optional[str] = None
