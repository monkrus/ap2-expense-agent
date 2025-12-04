import os

from .config import settings


def validate_settings() -> None:
    """
    Fail fast in production-like environments when unsafe defaults are present.

    This is intentionally strict for prod/staging. It is bypassed in tests via
    the TESTING env var.
    """
    if os.getenv("TESTING") in ("true", "True", "1"):
        return

    if settings.environment not in ("production", "staging"):
        return

    errors = []

    if settings.jwt_secret == "your-secret-key-change-in-production":
        errors.append("JWT_SECRET is using the default placeholder value.")

    if settings.debug:
        errors.append("debug must be False in production/staging.")

    if settings.database_url.startswith("sqlite"):
        errors.append("DATABASE_URL points to sqlite; use a managed database.")

    if settings.allow_dev_kms_fallback:
        errors.append("allow_dev_kms_fallback must be false in production/staging.")

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Insecure production configuration: {joined}")
