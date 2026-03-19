from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.v1.chat_routes import router as chat_router
from app.infrastructure.socketio.server import mount_socketio
from app.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title="Org ChatBot",
        version="0.1.0",
        default_response_class=ORJSONResponse,
    )

    app.include_router(chat_router, prefix="/api/v1")
    mount_socketio(app)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app
