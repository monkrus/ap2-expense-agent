"""
Request Validators and Helper Functions

Provides validation utilities for API requests including headers, parameters, and input data.
"""

from typing import Optional

from fastapi import HTTPException, Request, status


class HeaderValidator:
    """Validates required headers in API requests"""

    @staticmethod
    def require_organization_id(request: Request) -> str:
        """
        Validate that X-Organization-Id header is present and not empty.

        Args:
            request: FastAPI Request object

        Returns:
            str: Organization ID from header

        Raises:
            HTTPException: 400 if header is missing or empty
        """
        org_id = request.headers.get("X-Organization-Id")

        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "MISSING_REQUIRED_HEADER",
                    "message": "Organization context required",
                    "detail": "You must select an organization before performing this action. Please ensure you are logged in and have an organization assigned to your account.",
                    "required_header": "X-Organization-Id",
                },
            )

        return org_id.strip()

    @staticmethod
    def get_organization_id(request: Request) -> Optional[str]:
        """
        Get X-Organization-Id header if present (non-required version).

        Args:
            request: FastAPI Request object

        Returns:
            Optional[str]: Organization ID from header or None
        """
        org_id = request.headers.get("X-Organization-Id")
        return org_id.strip() if org_id else None


class InputValidator:
    """Validates input data"""

    @staticmethod
    def validate_username(username: str) -> None:
        """
        Validate username format and length.

        Args:
            username: Username to validate

        Raises:
            HTTPException: 422 if validation fails
        """
        if not username:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Username is required",
                    "field": "username",
                },
            )

        if len(username) < 3 or len(username) > 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Username must be between 3-50 characters",
                    "field": "username",
                    "value": username,
                },
            )

        # Check for valid characters (alphanumeric, underscore, dash)
        if not all(c.isalnum() or c in ["_", "-"] for c in username):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Username can only contain letters, numbers, underscores, and dashes",
                    "field": "username",
                    "value": username,
                },
            )

    @staticmethod
    def validate_password(password: str) -> None:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Raises:
            HTTPException: 422 if validation fails
        """
        if not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Password is required",
                    "field": "password",
                },
            )

        if len(password) < 8 or len(password) > 128:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Password must be between 8-128 characters",
                    "field": "password",
                },
            )

        # Check password strength requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Password must contain at least one uppercase letter, one lowercase letter, and one digit",
                    "field": "password",
                },
            )

    @staticmethod
    def validate_email(email: str) -> None:
        """
        Validate email format.

        Args:
            email: Email to validate

        Raises:
            HTTPException: 422 if validation fails
        """
        if not email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Email is required",
                    "field": "email",
                },
            )

        # Basic email validation
        if "@" not in email or "." not in email.split("@")[-1]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "Invalid email format",
                    "field": "email",
                    "value": email,
                },
            )


def require_header(header_name: str, error_message: str):
    """
    Dependency factory for requiring specific headers.

    Usage:
        @app.get("/endpoint")
        def endpoint(
            org_id: str = Depends(require_header("X-Organization-Id", "Organization ID required"))
        ):
            ...
    """

    def validate_header(request: Request) -> str:
        value = request.headers.get(header_name)
        if not value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "MISSING_REQUIRED_HEADER",
                    "message": "Required header not provided",
                    "detail": error_message,
                    "required_header": header_name,
                },
            )
        return value.strip()

    return validate_header
