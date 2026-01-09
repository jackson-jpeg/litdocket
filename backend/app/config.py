from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
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

    # Firebase (for auth only - data is in Supabase)
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"
    FIREBASE_STORAGE_BUCKET: str = ""

    # ============================================
    # SUPABASE - Primary Database (PostgreSQL)
    # ============================================
    # Supabase is the single source of truth for all data
    # including jurisdiction rules, cases, deadlines, etc.

    # Supabase Project URL (e.g., https://xxxxx.supabase.co)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")

    # Supabase anon key (public, safe for client-side)
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # Supabase service role key (secret, server-side only)
    # Used for admin operations bypassing RLS
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Direct PostgreSQL connection string for SQLAlchemy
    # Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")

    @property
    def use_supabase(self) -> bool:
        """Check if Supabase is configured"""
        return bool(self.SUPABASE_DB_URL or self.SUPABASE_URL)

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

    # Database - Supabase PostgreSQL is primary, fallback to local for dev
    @property
    def DATABASE_URL(self) -> str:
        # Priority 1: Supabase direct PostgreSQL connection
        if self.SUPABASE_DB_URL:
            return self.SUPABASE_DB_URL

        # Priority 2: Generic DATABASE_URL (Railway, Heroku, etc.)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Priority 3: Local SQLite for development only
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
