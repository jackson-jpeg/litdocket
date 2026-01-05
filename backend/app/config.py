from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Florida Docketing Assistant"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # CORS - Auto-detect production
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if origins_str:
            return [o.strip() for o in origins_str.split(",")]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    # Database - Auto-detect production (Railway provides DATABASE_URL env var)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./docketassist.db"  # Fallback to SQLite for local dev
    )

    # AI Services
    ANTHROPIC_API_KEY: str = "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"
    DEFAULT_AI_MODEL: str = "claude-sonnet-4-20250514"

    # OpenAI (for embeddings)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = "us-east-1"

    # AWS
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "docketassist-documents"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
