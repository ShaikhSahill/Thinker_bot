from fastapi import APIRouter

from app.schemas.chat_request import ChatRequest
from app.schemas.chat_response import ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    service = ChatService()
    return await service.handle_http(req)
