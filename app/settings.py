from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    # Mongo
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "org_chatbot"
    default_tenant_id: Optional[str] = None

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    use_llm_formatter: bool = False
