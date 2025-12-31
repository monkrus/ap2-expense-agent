import os
import logging
from typing import List, Tuple, Optional

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


def validate_environment_variables() -> Tuple[bool, List[str]]:
    """
    Validate required environment variables are set.
    Returns: (is_valid, list_of_errors)
    """
    required_vars = ["DATABASE_URL", "SECRET_KEY", "JWT_SECRET_KEY"]
    errors = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Missing required environment variable: {var}")
        elif len(value.strip()) == 0:
            errors.append(f"Empty environment variable: {var}")

    return len(errors) == 0, errors


def validate_database_connection() -> Tuple[bool, Optional[str]]:
    """
    Validate database connection.
    Returns: (is_valid, error_message)
    """
    try:
        from .database import SessionLocal, engine
        from sqlalchemy import text

        # Try to connect
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Try to create a session
        db = SessionLocal()
        db.close()

        return True, None

    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


def validate_secrets() -> Tuple[bool, List[str]]:
    """
    Validate secrets are properly configured (not weak values).
    Returns: (is_valid, list_of_warnings)
    """
    warnings = []

    # Check SECRET_KEY
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        if len(secret_key) < 32:
            warnings.append("SECRET_KEY is too short (should be at least 32 characters)")
        if secret_key in ["changeme", "secret", "dev"]:
            warnings.append("SECRET_KEY appears to be a default/weak value")

    # Check JWT_SECRET_KEY
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if jwt_secret:
        if len(jwt_secret) < 32:
            warnings.append("JWT_SECRET_KEY is too short (should be at least 32 characters)")
        if jwt_secret == secret_key:
            warnings.append("JWT_SECRET_KEY should be different from SECRET_KEY")

    return len(warnings) == 0, warnings


def run_comprehensive_checks(exit_on_error: bool = False) -> None:
    """
    Run comprehensive startup validation checks (optional, for debugging).

    Args:
        exit_on_error: If True, exit the program on critical errors
    """
    logger = logging.getLogger(__name__)

    if os.getenv("TESTING") in ("true", "True", "1"):
        return

    logger.info("=" * 70)
    logger.info("STARTUP VALIDATION CHECKS")
    logger.info("=" * 70)

    all_valid = True
    warnings = []

    # 1. Environment variables
    logger.info("[1/3] Validating environment variables...")
    env_valid, env_errors = validate_environment_variables()
    if env_valid:
        logger.info("✅ Environment variables: OK")
    else:
        logger.error("❌ Environment variables: FAILED")
        for error in env_errors:
            logger.error(f"   - {error}")
        all_valid = False

    # 2. Database connection
    logger.info("[2/3] Validating database connection...")
    db_valid, db_error = validate_database_connection()
    if db_valid:
        logger.info("✅ Database connection: OK")
    else:
        logger.error("❌ Database connection: FAILED")
        if db_error:
            logger.error(f"   - {db_error}")
        all_valid = False

    # 3. Secrets validation
    logger.info("[3/3] Validating secrets...")
    secrets_valid, secret_warnings = validate_secrets()
    if secrets_valid:
        logger.info("✅ Secrets: OK")
    else:
        logger.warning("⚠️  Secrets: WARNINGS")
        for warning in secret_warnings:
            logger.warning(f"   - {warning}")
        warnings.extend(secret_warnings)

    # Summary
    logger.info("=" * 70)
    if all_valid and not warnings:
        logger.info("✅ All checks passed! Application is ready to start.")
    elif all_valid and warnings:
        logger.warning("⚠️  All critical checks passed, but there are warnings:")
        for warning in warnings:
            logger.warning(f"   - {warning}")
    else:
        logger.error("❌ Validation FAILED")
        if exit_on_error:
            raise RuntimeError("Startup validation failed")
    logger.info("=" * 70)
