from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from ..database import get_db
from ..models import User, Session as UserSession, UserRole
from ..schemas import UserResponse, UserUpdate, UserCreate, SessionResponse, PasswordChange
from ..auth import (
    get_current_active_user,
    require_admin,
    require_manager,
    AuthService
)

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """List all users (requires manager or admin role)"""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific user"""
    # Users can view their own profile, managers/accountants can view all
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (requires admin role)"""
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
        is_verified=True  # Admin-created users are pre-verified
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.create",
        resource_type="user",
        resource_id=user.id,
        details={"created_by": current_user.id, "role": user.role.value},
        request=request
    )

    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a user"""
    # Users can update their own profile (except role and is_active)
    # Admins can update any user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    is_self_update = current_user.id == user_id
    is_admin = current_user.role == UserRole.ADMIN

    # Only admins can change role and is_active
    if user_data.role is not None and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )

    if user_data.is_active is not None and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can activate/deactivate users"
        )

    # Regular users can only update themselves
    if not is_self_update and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Update user fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.update",
        resource_type="user",
        resource_id=user.id,
        details={"updated_fields": list(update_data.keys())},
        request=request
    )

    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a user (requires admin role)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Log audit event before deletion
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="user.delete",
        resource_type="user",
        resource_id=user.id,
        details={"deleted_user": user.username},
        request=request
    )

    db.delete(user)
    db.commit()

    return None

@router.get("/{user_id}/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all sessions for a user"""
    # Users can only view their own sessions, admins/managers/accountants can view all
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these sessions"
        )

    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked == False
    ).all()

    # Mark current session
    session_responses = []
    for session in sessions:
        session_dict = SessionResponse.from_orm(session).dict()
        session_dict['is_current'] = False  # You could track this with session token
        session_responses.append(SessionResponse(**session_dict))

    return session_responses

@router.delete("/{user_id}/sessions/{session_id}")
async def revoke_session(
    user_id: str,
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    # Users can only revoke their own sessions, admins/managers/accountants can revoke any
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this session"
        )

    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    session.revoked = True
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="session.revoke",
        resource_type="session",
        resource_id=session.id,
        request=request
    )

    return {"message": "Session revoked successfully"}

@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change the current user's password"""
    # Verify old password
    if not AuthService.verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Hash and update new password
    current_user.hashed_password = AuthService.hash_password(password_data.new_password)
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="password.change",
        resource_type="user",
        resource_id=current_user.id,
        request=request
    )

    return {"message": "Password changed successfully"}

