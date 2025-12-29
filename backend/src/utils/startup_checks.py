"""
Startup Validation Checks

Validates environment configuration before application starts.
Prevents runtime failures due to missing or invalid configuration.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass


class StartupValidator:
    """Validates environment and configuration at startup"""

    REQUIRED_ENV_VARS = [
        "DATABASE_URL",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
    ]

    OPTIONAL_ENV_VARS = [
        "VITE_API_BASE_URL",
        "GOOGLE_CLOUD_PROJECT",
        "GCP_MARKETPLACE_PRODUCT_ID",
        "STRIPE_SECRET_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
    ]

    @staticmethod
    def validate_environment() -> Tuple[bool, List[str]]:
        """
        Validate all required environment variables are set.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []

        # Check required variables
        for var in StartupValidator.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value:
                errors.append(f"Missing required environment variable: {var}")
            elif len(value.strip()) == 0:
                errors.append(f"Empty environment variable: {var}")

        # Warn about optional variables
        missing_optional = []
        for var in StartupValidator.OPTIONAL_ENV_VARS:
            if not os.getenv(var):
                missing_optional.append(var)

        if missing_optional:
            print(f"[WARN] Warning: Missing optional environment variables: {', '.join(missing_optional)}")
            print("   Some features may not work correctly.")

        return len(errors) == 0, errors

    @staticmethod
    def validate_database_connection() -> Tuple[bool, Optional[str]]:
        """
        Validate database connection.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            from ..database import SessionLocal, engine
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

    @staticmethod
    def validate_required_modules() -> Tuple[bool, List[str]]:
        """
        Validate all required Python modules are installed.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        required_modules = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "pydantic",
            "bcrypt",
            "jose",  # python-jose for JWT
            "passlib",
        ]

        errors = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                errors.append(f"Missing required module: {module}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_secrets() -> Tuple[bool, List[str]]:
        """
        Validate secrets are properly configured (not default/weak values).

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_warnings)
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

    @staticmethod
    def validate_file_structure() -> Tuple[bool, List[str]]:
        """
        Validate required files and directories exist.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        required_files = [
            "src/api.py",
            "src/database.py",
            "src/models.py",
            "src/config.py",
        ]

        required_dirs = [
            "src/routes",
            "src/schemas",
            "src/utils",
        ]

        errors = []

        # Check files
        for file_path in required_files:
            if not os.path.exists(file_path):
                errors.append(f"Missing required file: {file_path}")

        # Check directories
        for dir_path in required_dirs:
            if not os.path.isdir(dir_path):
                errors.append(f"Missing required directory: {dir_path}")

        return len(errors) == 0, errors

    @staticmethod
    def run_all_checks(exit_on_error: bool = True) -> Dict[str, bool]:
        """
        Run all startup validation checks.

        Args:
            exit_on_error: If True, exit the program on critical errors

        Returns:
            Dict[str, bool]: Results of each check
        """
        results = {}
        critical_errors = []
        warnings = []

        print("=" * 70)
        print("STARTUP VALIDATION CHECKS")
        print("=" * 70)

        # 1. Environment variables
        print("\n[1/5] Validating environment variables...")
        env_valid, env_errors = StartupValidator.validate_environment()
        results["environment"] = env_valid
        if env_valid:
            print("[OK] Environment variables: OK")
        else:
            print("[ERROR] Environment variables: FAILED")
            critical_errors.extend(env_errors)

        # 2. Required modules
        print("\n[2/5] Validating required modules...")
        modules_valid, module_errors = StartupValidator.validate_required_modules()
        results["modules"] = modules_valid
        if modules_valid:
            print("[OK] Required modules: OK")
        else:
            print("[ERROR] Required modules: FAILED")
            critical_errors.extend(module_errors)

        # 3. Database connection
        print("\n[3/5] Validating database connection...")
        db_valid, db_error = StartupValidator.validate_database_connection()
        results["database"] = db_valid
        if db_valid:
            print("[OK] Database connection: OK")
        else:
            print("[ERROR] Database connection: FAILED")
            if db_error:
                critical_errors.append(db_error)

        # 4. Secrets validation
        print("\n[4/5] Validating secrets...")
        secrets_valid, secret_warnings = StartupValidator.validate_secrets()
        results["secrets"] = secrets_valid
        if secrets_valid:
            print("[OK] Secrets: OK")
        else:
            print("[WARN]  Secrets: WARNINGS")
            warnings.extend(secret_warnings)

        # 5. File structure
        print("\n[5/5] Validating file structure...")
        files_valid, file_errors = StartupValidator.validate_file_structure()
        results["files"] = files_valid
        if files_valid:
            print("[OK] File structure: OK")
        else:
            print("[ERROR] File structure: FAILED")
            critical_errors.extend(file_errors)

        # Summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)

        all_valid = all(results.values())

        if all_valid and not warnings:
            print("[OK] All checks passed! Application is ready to start.")
        elif all_valid and warnings:
            print("[WARN]  All critical checks passed, but there are warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        else:
            print("[ERROR] Validation FAILED with the following errors:")
            for error in critical_errors:
                print(f"   - {error}")

            if exit_on_error:
                print("\nApplication startup aborted due to validation errors.")
                print("Please fix the issues above and try again.")
                sys.exit(1)

        print("=" * 70)

        return results


def validate_on_startup():
    """
    Convenience function to run all startup checks.
    Call this from your main application startup.
    """
    return StartupValidator.run_all_checks(exit_on_error=True)


if __name__ == "__main__":
    # Allow running as a standalone script
    validate_on_startup()
