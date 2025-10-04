from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    google_api_key: Optional[str] = None
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False

    # Database
    database_url: str = "postgresql://ap2user:changeme@localhost:5432/expenses"
    redis_url: str = "redis://localhost:6379/0"

    # JWT & Authentication
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30

    # Security
    password_reset_expiration_hours: int = 1
    session_expiration_hours: int = 24
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Email (for password reset)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = "noreply@ap2expense.com"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # Environment
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
