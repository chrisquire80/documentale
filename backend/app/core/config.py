from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Documentale DMS"
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_ENABLED: bool = True

    STORAGE_PATH: str = "/app/storage/documents"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
