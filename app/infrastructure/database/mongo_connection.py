from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any

from app.settings import Settings

_client: Any = None


def get_client() -> Any:
    global _client
    if _client is None:
        settings = Settings()
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db() -> Any:
    settings = Settings()
    return get_client()[settings.mongo_db]
