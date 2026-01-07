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
        # Default origins include production and development
        return [
            "https://www.litdocket.com",
            "https://litdocket.com",
            "https://litdocket.vercel.app",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    # Database - Auto-detect production (Railway provides DATABASE_URL env var)
    # CRITICAL: Use absolute path for SQLite to prevent data loss from working directory changes
    @property
    def DATABASE_URL(self) -> str:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
        # Use absolute path for SQLite in development
        # This ensures the database is always in the same location regardless of working directory
        import pathlib
        backend_dir = pathlib.Path(__file__).parent.parent.absolute()
        return f"sqlite:///{backend_dir}/docket_assist.db"

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

    # Email (SendGrid)
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    EMAIL_FROM_ADDRESS: str = os.getenv("EMAIL_FROM_ADDRESS", "alerts@litdocket.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "LitDocket Alerts")
    EMAIL_ENABLED: bool = bool(os.getenv("SENDGRID_API_KEY", ""))

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


settings = Settings()
