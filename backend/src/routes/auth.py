from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import uuid

from ..database import get_db
from ..models import User, PasswordResetToken, UserRole
from ..schemas import (
    UserCreate, UserResponse, LoginRequest, LoginResponse,
    RefreshTokenRequest, TokenResponse, PasswordResetRequest,
    PasswordResetConfirm, PasswordChange, TOTPSetupResponse,
    TOTPVerifyRequest, TOTPEnableRequest, TOTPDisableRequest
)
from ..auth import (
    AuthService, TOTPService, get_current_active_user,
    require_admin
)
from ..rate_limit import limiter, RateLimits

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.REGISTER)
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=AuthService.hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
        is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=user.id,
        request=request
    )

    return user

@router.post("/login", response_model=LoginResponse)
@limiter.limit(RateLimits.LOGIN)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with username and password"""
    # Find user
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        lockout_minutes = (user.locked_until - datetime.utcnow()).total_seconds() / 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked due to too many failed attempts. Try again in {int(lockout_minutes)} minutes."
        )

    # Verify password
    if not AuthService.verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()

        # Lock account if threshold exceeded (5 attempts)
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts. Try again in 30 minutes."
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password. {5 - user.failed_login_attempts} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Reset failed attempts on successful login
    if user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_failed_login = None

    # Check 2FA if enabled
    if user.totp_enabled:
        if not login_data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA code required"
            )

        if not TOTPService.verify_totp(user.totp_secret, login_data.totp_code):
            # Check backup codes
            backup_codes = user.backup_codes.split(",") if user.backup_codes else []
            if login_data.totp_code not in backup_codes:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid 2FA code"
                )
            # Remove used backup code
            backup_codes.remove(login_data.totp_code)
            user.backup_codes = ",".join(backup_codes)

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = AuthService.create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value}
    )
    refresh_token = AuthService.create_refresh_token(
        user_id=user.id,
        db=db,
        device_info=request.headers.get("User-Agent")
    )

    # Create session
    AuthService.create_session(user_id=user.id, db=db, request=request)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        request=request
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=60 * 60,  # 1 hour
        user=UserResponse.from_orm(user)
    )

@router.post("/login/form", response_model=LoginResponse)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible login endpoint"""
    login_data = LoginRequest(username=form_data.username, password=form_data.password)
    return await login(login_data, request, db)

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(RateLimits.REFRESH_TOKEN)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    refresh_token = AuthService.verify_refresh_token(refresh_data.refresh_token, db)

    # Create new access token
    user = db.query(User).filter(User.id == refresh_token.user_id).first()
    access_token = AuthService.create_access_token(
        data={"sub": user.id, "username": user.username, "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=60 * 60
    )

@router.post("/logout")
async def logout(
    refresh_token: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke refresh token"""
    AuthService.revoke_refresh_token(refresh_token, db)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.logout",
        resource_type="user",
        resource_id=current_user.id,
        request=request
    )

    return {"message": "Successfully logged out"}

@router.post("/password/reset-request")
@limiter.limit(RateLimits.PASSWORD_RESET)
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset"""
    user = db.query(User).filter(User.email == reset_data.email).first()

    if not user:
        # Don't reveal if user exists
        return {"message": "If the email exists, a reset link has been sent"}

    # Create reset token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    reset_token = PasswordResetToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )

    db.add(reset_token)
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.password_reset_request",
        resource_type="user",
        resource_id=user.id,
        request=request
    )

    # TODO: Send email with reset link
    # In production, you would send an email here
    # For now, we'll just return the token (DO NOT do this in production)
    return {
        "message": "If the email exists, a reset link has been sent",
        "reset_token": token  # ONLY FOR DEVELOPMENT
    }

@router.post("/password/reset-confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == reset_data.token,
        PasswordResetToken.used == False
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Update password
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    user.hashed_password = AuthService.hash_password(reset_data.new_password)

    # Mark token as used
    reset_token.used = True

    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=user.id,
        action="user.password_reset_confirm",
        resource_type="user",
        resource_id=user.id,
        request=request
    )

    return {"message": "Password successfully reset"}

@router.post("/password/change")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password for authenticated user"""
    # Verify old password
    if not AuthService.verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = AuthService.hash_password(password_data.new_password)
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.password_change",
        resource_type="user",
        resource_id=current_user.id,
        request=request
    )

    return {"message": "Password successfully changed"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

# 2FA/TOTP Endpoints
@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Setup 2FA for current user"""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )

    # Generate secret
    secret = TOTPService.generate_secret()

    # Generate QR code
    qr_code_url = TOTPService.generate_qr_code(current_user.username, secret)

    # Generate backup codes
    backup_codes = TOTPService.generate_backup_codes()

    # Store secret (not enabled yet)
    current_user.totp_secret = secret
    current_user.backup_codes = ",".join(backup_codes)
    db.commit()

    return TOTPSetupResponse(
        secret=secret,
        qr_code_url=qr_code_url,
        backup_codes=backup_codes
    )

@router.post("/2fa/enable")
async def enable_2fa(
    totp_data: TOTPEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA after verification"""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not completed. Call /2fa/setup first"
        )

    # Verify TOTP code
    if not TOTPService.verify_totp(current_user.totp_secret, totp_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )

    # Enable 2FA
    current_user.totp_enabled = True
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.2fa_enabled",
        resource_type="user",
        resource_id=current_user.id,
        request=request
    )

    return {"message": "2FA successfully enabled"}

@router.post("/2fa/disable")
async def disable_2fa(
    totp_data: TOTPDisableRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA"""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    # Verify password
    if not AuthService.verify_password(totp_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    # Verify TOTP code if provided
    if totp_data.totp_code:
        if not TOTPService.verify_totp(current_user.totp_secret, totp_data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 2FA code"
            )

    # Disable 2FA
    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.2fa_disabled",
        resource_type="user",
        resource_id=current_user.id,
        request=request
    )

    return {"message": "2FA successfully disabled"}

@router.post("/2fa/verify")
async def verify_2fa(
    totp_data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Verify a 2FA code (for testing)"""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    if TOTPService.verify_totp(current_user.totp_secret, totp_data.totp_code):
        return {"valid": True}
    else:
        return {"valid": False}
