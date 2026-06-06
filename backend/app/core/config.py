from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "Authentra AI"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production-32-chars-minimum"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://authentra:authentra@db:5432/authentra"
    SYNC_DATABASE_URL: str = "postgresql://authentra:authentra@db:5432/authentra"

    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@authentra.ai"
    SMTP_FROM_NAME: str = "Authentra AI"
    SMTP_TLS: bool = True

    FRONTEND_URL: str = "http://localhost:3000"

    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    ENCRYPTION_KEY: str = "your-32-byte-encryption-key-here!!"

    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    MAX_RESUME_SIZE_MB: int = 10

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
