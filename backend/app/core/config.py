from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Documentale DMS"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/db"
    SECRET_KEY: str = "test-secret-key-change-it-in-production"
    DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240  # 4 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    ALGORITHM: str = "HS256"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_ENABLED: bool = True

    STORAGE_PATH: str = "/app/storage/documents"
    REDIS_URL: str = "redis://redis:6379/0"

    AUTO_USER_EMAIL: str = "admin@example.com"
    WATCH_DIR: str = "/app/auto_ingest"
    ALLOWED_EXTENSIONS: set[str] = {'.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
