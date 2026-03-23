from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceRef(BaseModel):
    type: str
    id: str
    title: str
    link: Optional[str] = None


class ActionButton(BaseModel):
    label: str
    action: str


class ResponseCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    card_type: str
    answers: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    queryId: str
    userJourneyId: str
    role: Literal["bot"] = "bot"
    responses: list[ResponseCard]
    createdAt: datetime
