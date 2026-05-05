"""
Standardized API Response Schemas

This module defines consistent response structures for all API endpoints.
All responses follow a predictable pattern to prevent frontend-backend contract mismatches.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for data payload
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper"""

    success: bool = Field(True, description="Always true for successful responses")
    message: str = Field(..., description="Human-readable success message")
    data: Optional[T] = Field(None, description="Response payload")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "Example"},
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response"""

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    field: Optional[str] = Field(None, description="Field that caused validation error")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "detail": "Username must be between 3-50 characters",
                "field": "username",
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response"""

    success: bool = Field(True, description="Always true for successful responses")
    data: List[T] = Field(..., description="List of items")
    pagination: Dict[str, Any] = Field(
        ...,
        description="Pagination metadata",
        json_schema_extra={
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            }
        },
    )


# User Response Models
class UserData(BaseModel):
    """User data structure"""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserCreatedResponse(SuccessResponse[UserData]):
    """Response for user creation"""

    user: UserData = Field(..., description="Created user details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "User created successfully",
                "user": {
                    "id": "uuid-123",
                    "username": "employee1",
                    "email": "employee1@example.com",
                    "full_name": "John Doe",
                    "role": "employee",
                    "is_active": True,
                    "is_verified": True,
                    "created_at": "2025-01-01T12:00:00",
                    "updated_at": None,
                    "last_login": None,
                },
            }
        }


class UserDeletedResponse(SuccessResponse[None]):
    """Response for user deletion"""

    user_id: str = Field(..., description="ID of deleted user")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "User 'employee1' deleted successfully",
                "user_id": "uuid-123",
            }
        }


# Expense Response Models
class ExpenseData(BaseModel):
    """Expense data structure"""

    id: str
    amount: float
    vendor: str
    category: str
    description: str
    status: str
    date: datetime
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class ExpenseCreatedResponse(SuccessResponse[ExpenseData]):
    """Response for expense creation"""

    expense: ExpenseData = Field(..., description="Created expense details")


class ExpenseApprovedResponse(SuccessResponse[ExpenseData]):
    """Response for expense approval"""

    expense: ExpenseData = Field(..., description="Approved expense details")


# Organization Response Models
class OrganizationData(BaseModel):
    """Organization data structure"""

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    currency: str
    timezone: str
    is_active: bool
    created_at: datetime


class OrganizationCreatedResponse(SuccessResponse[OrganizationData]):
    """Response for organization creation"""

    organization: OrganizationData = Field(..., description="Created organization")


# Generic CRUD Responses
class CreatedResponse(SuccessResponse[T]):
    """Generic creation response"""

    pass


class UpdatedResponse(SuccessResponse[T]):
    """Generic update response"""

    pass


class DeletedResponse(SuccessResponse[None]):
    """Generic deletion response"""

    resource_id: str = Field(..., description="ID of deleted resource")


# Validation Error Response
class ValidationErrorDetail(BaseModel):
    """Validation error for a specific field"""

    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value provided")


class ValidationErrorResponse(ErrorResponse):
    """Response for validation errors (422)"""

    errors: List[ValidationErrorDetail] = Field(
        ..., description="List of validation errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "VALIDATION_ERROR",
                "message": "Invalid input provided",
                "errors": [
                    {
                        "field": "username",
                        "message": "Username must be between 3-50 characters",
                        "value": "ab",
                    },
                    {
                        "field": "password",
                        "message": "Password must contain at least one uppercase letter",
                        "value": "password123",
                    },
                ],
            }
        }


# Header Validation Error
class MissingHeaderError(ErrorResponse):
    """Response for missing required headers"""

    required_header: str = Field(..., description="Name of missing header")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "MISSING_REQUIRED_HEADER",
                "message": "Required header not provided",
                "detail": "X-Organization-Id header is required for this operation",
                "required_header": "X-Organization-Id",
            }
        }


# Common Error Responses
class UnauthorizedResponse(ErrorResponse):
    """401 Unauthorized response"""

    error: str = "UNAUTHORIZED"


class ForbiddenResponse(ErrorResponse):
    """403 Forbidden response"""

    error: str = "FORBIDDEN"


class NotFoundResponse(ErrorResponse):
    """404 Not Found response"""

    error: str = "NOT_FOUND"


class ConflictResponse(ErrorResponse):
    """409 Conflict response (e.g., duplicate resource)"""

    error: str = "CONFLICT"


class PaymentRequiredResponse(ErrorResponse):
    """402 Payment Required response (tier limit exceeded)"""

    error: str = "PAYMENT_REQUIRED"
    upgrade_message: Optional[str] = Field(
        None, description="Message about upgrading subscription"
    )


# Helper functions for creating responses
def success_response(
    message: str, data: Optional[Any] = None, **kwargs
) -> Dict[str, Any]:
    """Create a standardized success response"""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    response.update(kwargs)
    return response


def error_response(
    error: str, message: str, detail: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """Create a standardized error response"""
    response = {"success": False, "error": error, "message": message}
    if detail:
        response["detail"] = detail
    response.update(kwargs)
    return response


def created_response(message: str, resource: Any, **kwargs) -> Dict[str, Any]:
    """Create a standardized creation response"""
    return {"success": True, "message": message, **kwargs, **resource}


def deleted_response(message: str, resource_id: str) -> Dict[str, Any]:
    """Create a standardized deletion response"""
    return {"success": True, "message": message, "resource_id": resource_id}
