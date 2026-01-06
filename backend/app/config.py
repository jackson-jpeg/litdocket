from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "LitDocket"
    DEBUG: bool = Field(default=False, env="DEBUG")  # Default to False for security
    API_V1_PREFIX: str = "/api/v1"
    PORT: int = 8000

    # Security - REQUIRED from environment
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required - use secrets.token_urlsafe(64)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # JWT - REQUIRED from environment
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")  # Required - use secrets.token_urlsafe(64)

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    FIREBASE_STORAGE_BUCKET: str = ""

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
        "sqlite:///./docket_assist.db"  # Fallback to SQLite for local dev
    )

    # AI Services - REQUIRED from environment
    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")  # Required - NEVER hardcode
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
        extra = "allow"  # Allow extra fields from .env


settings = Settings()
