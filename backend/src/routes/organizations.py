"""
Organization Management API Routes
Handles multi-tenancy, organization creation, member management, and invitations
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..auth import get_current_active_user
from ..cache import invalidate_user_cache
from ..database import get_db
from ..email_service import EmailService
from ..models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
    User,
    Subscription,
    SubscriptionTier,
)
from ..billing.tier_limits import get_tier_limits
from ..schemas import (
    OrganizationCreate,
    OrganizationInvitationCreate,
    OrganizationInvitationResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from ..tenant_context import (
    TenantAwareQuery,
    TenantContext,
    get_organization_or_404,
    get_user_organization_role,
    get_user_organizations,
    verify_organization_access,
)
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


# ============================================================================
# Organization CRUD
# ============================================================================


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new organization"""

    # Check if slug is already taken
    existing = db.query(Organization).filter(Organization.slug == org_data.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already taken",
        )

    # Anti-abuse: Free tier users can only own ONE organization
    user_subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .filter(Subscription.status.in_(["active", "trialing"]))
        .first()
    )

    # Check if user is on Free tier (no subscription = Free, or explicit Free tier)
    is_free_tier = (
        not user_subscription or user_subscription.tier == SubscriptionTier.FREE
    )

    if is_free_tier:
        # Count how many ACTIVE organizations user already owns
        # Join with Organization table to ensure we only count active orgs
        owned_orgs_count = (
            db.query(OrganizationMember)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .filter(OrganizationMember.user_id == current_user.id)
            .filter(OrganizationMember.role == OrganizationRole.OWNER)
            .filter(OrganizationMember.is_active == True)
            .filter(Organization.is_active == True)  # Only count active organizations
            .count()
        )

        logger.info(f"Free tier check: user={current_user.username}, owned_orgs_count={owned_orgs_count}")

        if owned_orgs_count >= 1:
            logger.warning(f"Free tier limit reached for user={current_user.username}, count={owned_orgs_count}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "Free tier limit reached",
                    "message": "Cannot create a second organization on the Free tier.",
                    "upgrade_required": True,
                    "current_limit": 1,
                },
            )

    # Create organization
    organization = Organization(
        id=str(uuid.uuid4()),
        name=org_data.name,
        slug=org_data.slug,
        description=org_data.description,
        currency=org_data.currency or "USD",
        timezone=org_data.timezone or "UTC",
        max_members=org_data.max_members or 25,
        is_active=True,
    )
    db.add(organization)
    db.flush()

    # Add creator as owner
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=organization.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
        is_active=True,
    )
    db.add(membership)

    # Check if user already has a subscription
    existing_subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .filter(Subscription.status.in_(["active", "trialing"]))
        .first()
    )

    # Create explicit Free subscription if none exists
    if not existing_subscription:
        free_limits = get_tier_limits(SubscriptionTier.FREE)
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            tier=SubscriptionTier.FREE,
            status="active",
            max_users=free_limits.max_users,
            max_expenses_per_month=free_limits.max_expenses_per_month,
            max_ai_categorizations=free_limits.max_ai_categorizations,
            max_ap2_transactions=free_limits.max_ap2_transactions,
        )
        db.add(subscription)

    db.commit()
    db.refresh(organization)

    return organization


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """List all organizations user belongs to"""
    organizations = get_user_organizations(current_user.id, db)
    return organizations


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get organization details"""

    # Verify access
    TenantAwareQuery.ensure_organization_access(organization_id, current_user.id, db)

    organization = get_organization_or_404(organization_id, db)
    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update organization details (requires admin role)"""

    # Verify access and role
    role = get_user_organization_role(current_user.id, organization_id, db)
    if role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update settings",
        )

    organization = get_organization_or_404(organization_id, db)

    # Update fields
    if org_data.name is not None:
        organization.name = org_data.name
    if org_data.description is not None:
        organization.description = org_data.description
    if org_data.currency is not None:
        organization.currency = org_data.currency
    if org_data.timezone is not None:
        organization.timezone = org_data.timezone

    db.commit()
    db.refresh(organization)

    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete organization (requires owner role)"""

    # Verify owner role
    role = get_user_organization_role(current_user.id, organization_id, db)
    if role != OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can delete the organization",
        )

    organization = get_organization_or_404(organization_id, db)

    # Get all members to invalidate their caches
    members = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .all()
    )

    # Soft delete
    organization.is_active = False
    db.commit()

    # Invalidate cache for all members
    for member in members:
        invalidate_user_cache(member.user_id)


# ============================================================================
# Organization Members
# ============================================================================


@router.get(
    "/{organization_id}/members", response_model=List[OrganizationMemberResponse]
)
async def list_organization_members(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all members of an organization"""

    # Verify access
    TenantAwareQuery.ensure_organization_access(organization_id, current_user.id, db)

    members = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .all()
    )

    # Fetch user details
    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            result.append(
                {
                    "id": member.id,
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": member.role.value,
                    "joined_at": member.joined_at,
                }
            )

    return result


@router.patch("/{organization_id}/members/{member_id}/role")
async def update_member_role(
    organization_id: str,
    member_id: str,
    role: OrganizationRole,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update member role (requires admin role)"""

    # Verify access and role
    user_role = get_user_organization_role(current_user.id, organization_id, db)
    if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update member roles",
        )

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    # Cannot change owner role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role"
        )

    member.role = role
    db.commit()

    return {"message": "Member role updated successfully"}


@router.delete(
    "/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_organization_member(
    organization_id: str,
    member_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove member from organization (requires admin role)"""

    # Verify access and role
    user_role = get_user_organization_role(current_user.id, organization_id, db)
    if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can remove members",
        )

    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    # Cannot remove owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner",
        )

    # Soft delete (deactivate)
    member.is_active = False
    db.commit()


# ============================================================================
# Organization Invitations
# ============================================================================


@router.post(
    "/{organization_id}/invitations",
    response_model=OrganizationInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    organization_id: str,
    invitation_data: OrganizationInvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Invite a user to join the organization"""

    # Verify access and role
    user_role = get_user_organization_role(current_user.id, organization_id, db)
    if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can invite members",
        )

    organization = get_organization_or_404(organization_id, db)

    # Check user limit (hard block for Free tier)
    try:
        limit_enforcer = LimitEnforcer(db)
        limit_enforcer.check_user_limit(organization_id, raise_error=True)
    except LimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "limit_exceeded",
                "feature": e.feature,
                "limit": e.limit,
                "current": e.current,
                "message": str(e),
                "upgrade_message": e.upgrade_message,
            },
        )

    # Check if user already a member
    existing_user = db.query(User).filter(User.email == invitation_data.email).first()
    if existing_user:
        existing_membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == existing_user.id,
                OrganizationMember.is_active == True,
            )
            .first()
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

    # Check if pending invitation exists
    pending = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.email == invitation_data.email,
            OrganizationInvitation.status == "pending",
        )
        .first()
    )

    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already sent to this email",
        )

    # Create invitation
    invitation = OrganizationInvitation(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        email=invitation_data.email,
        role=invitation_data.role or OrganizationRole.MEMBER,
        invited_by=current_user.id,
        token=secrets.token_urlsafe(32),
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Send invitation email
    EmailService.send_organization_invitation_email(
        to_email=invitation.email,
        organization_name=organization.name,
        inviter_name=current_user.full_name or current_user.username,
        invitation_token=invitation.token,
    )

    return invitation


@router.get(
    "/{organization_id}/invitations",
    response_model=List[OrganizationInvitationResponse],
)
async def list_invitations(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List pending invitations for organization"""

    # Verify access
    TenantAwareQuery.ensure_organization_access(organization_id, current_user.id, db)

    invitations = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.status == "pending",
        )
        .all()
    )

    return invitations


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Accept an organization invitation"""

    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.token == token,
            OrganizationInvitation.status == "pending",
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already used",
        )

    # Check expiration
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired"
        )

    # Check email matches
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    # Check if already a member
    existing = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == invitation.organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this organization",
        )

    # Create membership
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=invitation.organization_id,
        user_id=current_user.id,
        role=invitation.role,
        is_active=True,
    )
    db.add(membership)

    # Update invitation status
    invitation.status = "accepted"
    invitation.accepted_at = datetime.utcnow()

    db.commit()

    return {"message": "Invitation accepted successfully"}


@router.delete(
    "/{organization_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
    organization_id: str,
    invitation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke a pending invitation"""

    # Verify access and role
    user_role = get_user_organization_role(current_user.id, organization_id, db)
    if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can revoke invitations",
        )

    invitation = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    invitation.status = "revoked"
    db.commit()
