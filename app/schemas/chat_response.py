from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    tool: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    data: Optional[Union[Dict[str, Any], List[Any]]] = None
