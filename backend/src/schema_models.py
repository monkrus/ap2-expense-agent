from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .models import UserRole


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.EMPLOYEE

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    role: UserRole
    is_active: bool
    is_verified: bool
    totp_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# Authentication Schemas
class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# 2FA Schemas
class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TOTPVerifyRequest(BaseModel):
    totp_code: str


class TOTPEnableRequest(BaseModel):
    totp_code: str


class TOTPDisableRequest(BaseModel):
    password: str
    totp_code: Optional[str] = None


# Session Schemas
class SessionResponse(BaseModel):
    id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_current: bool = False

    class Config:
        from_attributes = True


# OAuth2 Schemas
class OAuth2AuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    response_type: str = "code"
    scope: Optional[str] = "read write"
    state: Optional[str] = None


class OAuth2TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


# ============================================================================
# Organization Schemas (Multi-Tenancy)
# ============================================================================


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    # Note: min_length validation removed - custom validation in route provides better error message
    slug: str = Field(..., max_length=255, pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    currency: Optional[str] = "USD"
    timezone: Optional[str] = "UTC"
    max_members: Optional[int] = 1


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    currency: str
    timezone: str
    max_members: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class OrganizationInvitationCreate(BaseModel):
    email: EmailStr
    role: Optional[str] = "member"


class OrganizationInvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Expense Schemas
# ============================================================================


class ExpenseSubmission(BaseModel):
    amount: float
    vendor: str
    category: str  # Will be validated against ExpenseCategory enum values
    description: str
    date: Optional[str] = (
        None  # ISO format date string (YYYY-MM-DD), defaults to today if not provided
    )
    # Note: user_id is derived from the authenticated user (current_user), not from the request

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        # Security: Prevent unreasonably large amounts (max $1,000,000 per expense)
        if v > 1000000:
            raise ValueError("Amount cannot exceed $1,000,000 per expense")
        return v

    @validator("description")
    def sanitize_description(cls, v):
        """Sanitize description to prevent XSS attacks"""
        import html

        # HTML escape any dangerous characters
        sanitized = html.escape(v)
        # Also limit length
        if len(sanitized) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        return sanitized

    @validator("vendor")
    def sanitize_vendor(cls, v):
        """Sanitize vendor name to prevent XSS attacks"""
        import html

        sanitized = html.escape(v)
        if len(sanitized) > 200:
            raise ValueError("Vendor name cannot exceed 200 characters")
        return sanitized

    @validator("category")
    def validate_category(cls, v):
        from .models import ExpenseCategory

        # Check if the value matches any of the enum values
        valid_categories = [e.value for e in ExpenseCategory]
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v

    @validator("date")
    def validate_date(cls, v):
        if v is None:
            return None
        # Validate date format
        from datetime import datetime

        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


class ExpenseUpdate(BaseModel):
    """Schema for partial expense updates - all fields optional"""
    amount: Optional[float] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None

    @validator("amount")
    def validate_amount(cls, v):
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be positive")
            if v > 1000000:
                raise ValueError("Amount cannot exceed $1,000,000 per expense")
        return v

    @validator("description")
    def sanitize_description(cls, v):
        if v is not None:
            import html
            sanitized = html.escape(v)
            if len(sanitized) > 1000:
                raise ValueError("Description cannot exceed 1000 characters")
            return sanitized
        return v

    @validator("vendor")
    def sanitize_vendor(cls, v):
        if v is not None:
            import html
            sanitized = html.escape(v)
            if len(sanitized) > 200:
                raise ValueError("Vendor name cannot exceed 200 characters")
            return sanitized
        return v

    @validator("category")
    def validate_category(cls, v):
        if v is not None:
            from .models import ExpenseCategory
            valid_categories = [e.value for e in ExpenseCategory]
            if v not in valid_categories:
                raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v

    @validator("date")
    def validate_date(cls, v):
        if v is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(v)
                return v
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v
