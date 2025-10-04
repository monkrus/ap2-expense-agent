from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from .models import UserRole

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.EMPLOYEE

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
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
