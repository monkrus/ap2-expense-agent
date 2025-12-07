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

    # CORS must not allow localhost or wildcards in production/staging
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    insecure_origins = [
        o
        for o in origins
        if "localhost" in o or "127.0.0.1" in o or o == "*" or o == "0.0.0.0"
    ]
    if insecure_origins:
        errors.append(
            "CORS origins include development or wildcard entries; set CORS_ORIGINS to your production domains."
        )

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Insecure production configuration: {joined}")
