from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: Optional[str] = None
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_genai_use_vertexai: bool = False
    gcp_project_id: Optional[str] = None  # Used by KMS signing for AP2 mandates

    # Database
    # Default to SQLite for development, override with DATABASE_URL env var for production
    database_url: str = "sqlite:///./test.db"
    redis_url: str = "redis://localhost:6379/0"

    # Database Connection Pooling (Scaled for production: 1000+ concurrent users)
    db_pool_size: int = 20  # Number of connections to keep open (was 5)
    db_max_overflow: int = 40  # Max connections beyond pool_size (was 10)
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour

    # Data Retention (in days)
    audit_log_retention_days: int = 90
    session_retention_days: int = 30
    revoked_token_retention_days: int = 7

    # JWT & Authentication
    jwt_secret: str = "CHANGE-ME-set-JWT_SECRET-env-var"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30

    # Security
    password_reset_expiration_hours: int = 1
    session_expiration_hours: int = 24
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Email Configuration
    smtp_server: Optional[str] = None  # SMTP server (e.g., smtp.gmail.com)
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = (
        None  # From email address (set SMTP_FROM_EMAIL env var)
    )
    from_email: Optional[str] = None  # Alias for backwards compatibility
    notifications_enabled: bool = False  # Enable/disable email notifications

    # Stripe Payment Configuration
    stripe_secret_key: Optional[str] = None
    stripe_test_mode: bool = False  # Enable test mode to bypass Stripe for AP2 testing
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # Subscription & Monetization
    enable_billing: bool = False  # Enable/disable billing features
    trial_period_days: int = 14  # Free trial period
    ap2_transaction_fee: float = 0.10  # Fee per AP2 transaction
    ai_categorization_fee: float = 0.05  # Fee per AI categorization (over limit)
    ocr_scan_fee: float = 0.02  # Fee per OCR scan (over limit)

    # QuickBooks Integration
    quickbooks_client_id: Optional[str] = None
    quickbooks_client_secret: Optional[str] = None
    quickbooks_redirect_uri: Optional[str] = (
        "http://localhost:8000/api/v1/quickbooks/callback"
    )
    quickbooks_environment: str = "sandbox"  # sandbox or production
    quickbooks_webhook_verifier_token: Optional[str] = (
        None  # Intuit webhook HMAC verification
    )

    # Legal URLs (required for Intuit App Store)
    privacy_policy_url: str = "https://your-domain.com/privacy"
    terms_of_service_url: str = "https://your-domain.com/terms"

    # Frontend URL (for emails and redirects)
    frontend_url: Optional[str] = "http://localhost:5173"

    # CORS
    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost,http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    # Environment
    environment: str = "development"
    debug: bool = True
    # Security toggles
    allow_dev_kms_fallback: bool = (
        True  # Auto-enabled for development; overridden to False in production/staging below
    )
    rate_limit_enabled: bool = True  # Disable only for controlled perf tests

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()


# Post-init validation for production/staging
try:
    # pydantic v2: model_post_init
    def _post_init(self):
        if self.environment in ("production", "staging"):
            if not self.jwt_secret:
                raise ValueError("JWT_SECRET must be set in production/staging")
            if not self.database_url:
                raise ValueError("DATABASE_URL must be set in production/staging")
            # Never allow dev KMS fallback in production/staging
            self.allow_dev_kms_fallback = False

    Settings.model_post_init = _post_init  # type: ignore[attr-defined]
except Exception:
    pass
