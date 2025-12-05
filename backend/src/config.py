from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


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

    # Email Configuration
    smtp_server: Optional[str] = None  # SMTP server (e.g., smtp.gmail.com)
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = "noreply@ap2expense.com"  # From email address
    from_email: Optional[str] = (
        "noreply@ap2expense.com"  # Alias for backwards compatibility
    )
    notifications_enabled: bool = False  # Enable/disable email notifications

    # Stripe Payment Configuration
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    # Monthly price IDs
    stripe_price_id_starter_monthly: Optional[str] = None
    stripe_price_id_professional_monthly: Optional[str] = None
    stripe_price_id_enterprise_monthly: Optional[str] = None
    # Annual price IDs
    stripe_price_id_starter_annual: Optional[str] = None
    stripe_price_id_professional_annual: Optional[str] = None
    stripe_price_id_enterprise_annual: Optional[str] = None

    # Subscription & Monetization
    enable_billing: bool = False  # Enable/disable billing features
    trial_period_days: int = 14  # Free trial period
    ap2_transaction_fee: float = 0.10  # Fee per AP2 transaction
    ai_categorization_fee: float = 0.05  # Fee per AI categorization (over limit)
    ocr_scan_fee: float = 0.02  # Fee per OCR scan (over limit)

    # Google Cloud Marketplace Configuration
    gcp_project_id: Optional[str] = None  # GCP Project ID
    gcp_provider_id: Optional[str] = None  # Provider ID for Consumer Procurement (defaults to project_id when unset)
    gcp_service_account_path: Optional[str] = None  # Path to service account JSON file
    gcp_webhook_secret: Optional[str] = None  # Webhook secret from GCP Marketplace
    gcp_webhook_audience: Optional[str] = None  # Expected OIDC audience for Pub/Sub push
    enable_gcp_marketplace: bool = False  # Enable/disable GCP Marketplace integration
    gcp_usage_reporting_enabled: bool = True  # Enable hourly usage reporting to GCP
    gcp_trial_period_days: int = 14  # Free trial length for Marketplace signups
    gcp_grace_period_days: int = 7  # Grace after cancellation/suspension
    gcp_metering_retry_max_attempts: int = 5  # Usage report retry attempts
    gcp_metering_retry_backoff_seconds: int = 60  # Base backoff for retries
    gcp_marketplace_sku_map: dict = Field(
        default_factory=lambda: {
            # Logical feature -> SKU/unit mapping (populate with real SKUs in env)
            "expenses": {"unit": "expense", "sku": None},
            "ai_categorizations": {"unit": "ai_categorization", "sku": None},
            "ap2_transactions": {"unit": "ap2_transaction", "sku": None},
        }
    )

    # Frontend URL (for emails and redirects)
    frontend_url: Optional[str] = "http://localhost:5173"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # Environment
    environment: str = "development"
    debug: bool = True
    # Security toggles
    allow_dev_kms_fallback: bool = False  # Only enable dev signing fallback explicitly (tests/dev)
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
            if self.enable_gcp_marketplace and not self.gcp_webhook_audience:
                raise ValueError(
                    "GCP_WEBHOOK_AUDIENCE must be set when Marketplace integration is enabled"
                )

    Settings.model_post_init = _post_init  # type: ignore[attr-defined]
except Exception:
    pass
