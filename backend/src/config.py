from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    google_api_key: Optional[str] = None
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False

    # Database
    # Default to SQLite for development, override with DATABASE_URL env var for production
    database_url: str = "sqlite:///./test.db"
    redis_url: str = "redis://localhost:6379/0"

    # Database Connection Pooling
    db_pool_size: int = 5  # Number of connections to keep open
    db_max_overflow: int = 10  # Max connections beyond pool_size
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Data Retention (in days)
    audit_log_retention_days: int = 90
    session_retention_days: int = 30
    revoked_token_retention_days: int = 7

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

    # Stripe Payment Configuration
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id_starter: Optional[str] = None  # Stripe Price ID for Starter tier
    stripe_price_id_professional: Optional[str] = None  # Stripe Price ID for Professional tier
    stripe_price_id_enterprise: Optional[str] = None  # Stripe Price ID for Enterprise tier

    # Subscription & Monetization
    enable_billing: bool = False  # Enable/disable billing features
    trial_period_days: int = 14  # Free trial period
    ap2_transaction_fee: float = 0.10  # Fee per AP2 transaction
    ai_categorization_fee: float = 0.05  # Fee per AI categorization (over limit)
    ocr_scan_fee: float = 0.02  # Fee per OCR scan (over limit)

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # Environment
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
