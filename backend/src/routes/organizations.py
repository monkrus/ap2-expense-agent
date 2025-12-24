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
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..auth import get_current_active_user
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..cache import invalidate_user_cache
from ..config import settings
from ..database import get_db
from ..email_service import EmailService
from ..models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
    User,
)
from ..models_billing import OrganizationSubscription
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
    FREE_TIER_MAX_MEMBERS,
    get_organization_or_404,
    get_user_organization_role,
    get_user_organizations,
    verify_organization_access,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


# ============================================================================
# Validation Helpers
# ============================================================================


@router.get("/validate/name")
async def check_name_availability(
    name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if organization name is available (real-time validation)"""

    if not name or len(name.strip()) == 0:
        return {"available": False, "message": "Name cannot be empty"}

    # Check if name is already taken (case-insensitive, only ACTIVE organizations)
    existing_name = (
        db.query(Organization)
        .filter(func.lower(Organization.name) == func.lower(name))
        .filter(Organization.is_active == True)
        .first()
    )

    if existing_name:
        suggestions = [
            f"{name} Team",
            f"{name} Inc",
            f"{name} Group",
            f"The {name}",
        ]
        return {
            "available": False,
            "message": f"The name '{name}' is already in use",
            "suggestions": suggestions,
            "hint": "Names are case-insensitive",
        }

    return {"available": True, "message": "Name is available"}


@router.get("/validate/slug")
async def check_slug_availability(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check if organization slug is available (real-time validation)"""

    if not slug or len(slug.strip()) == 0:
        return {"available": False, "message": "Slug cannot be empty"}

    # Check if slug is already taken (only check ACTIVE organizations)
    existing_slug = (
        db.query(Organization)
        .filter(Organization.slug == slug)
        .filter(Organization.is_active == True)
        .first()
    )

    if existing_slug:
        suggestions = [
            f"{slug}-team",
            f"{slug}-inc",
            f"{slug}-co",
        ]
        return {
            "available": False,
            "message": f"The slug '{slug}' is already in use",
            "suggestions": suggestions,
        }

    return {"available": True, "message": "Slug is available"}


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
    logger.info(f"[CREATE_ORG] User {current_user.id} ({current_user.username}) attempting to create org: {org_data.name}")
    if settings.enable_gcp_marketplace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizations are provisioned via Google Cloud Marketplace.",
        )

    # Clean up any soft-deleted organizations with the same slug
    # This prevents UNIQUE constraint violations while allowing slug reuse
    soft_deleted_with_slug = (
        db.query(Organization)
        .filter(Organization.slug == org_data.slug)
        .filter(Organization.is_active == False)
        .all()
    )
    if soft_deleted_with_slug:
        logger.info(
            f"Hard-deleting {len(soft_deleted_with_slug)} soft-deleted "
            f"organization(s) with slug '{org_data.slug}' to free up the slug"
        )
        for org in soft_deleted_with_slug:
            # Hard delete to free up the slug
            db.delete(org)
        # CRITICAL: Must commit (not just flush) to release UNIQUE constraint
        db.commit()

    # Check if slug is already taken (only check ACTIVE organizations)
    existing_slug = (
        db.query(Organization)
        .filter(Organization.slug == org_data.slug)
        .filter(Organization.is_active == True)
        .first()
    )
    if existing_slug:
        # Provide helpful suggestions for alternative slugs
        suggestions = [
            f"{org_data.slug}-team",
            f"{org_data.slug}-inc",
            f"{org_data.slug}-co",
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "slug_already_taken",
                "message": f"The slug '{org_data.slug}' is already in use by another active organization.",
                "field": "slug",
                "suggestions": suggestions,
            },
        )

    # Check if name is already taken (case-insensitive, only ACTIVE organizations)
    existing_name = (
        db.query(Organization)
        .filter(func.lower(Organization.name) == func.lower(org_data.name))
        .filter(Organization.is_active == True)
        .first()
    )
    if existing_name:
        # Provide helpful suggestions for alternative names
        suggestions = [
            f"{org_data.name} Team",
            f"{org_data.name} Inc",
            f"{org_data.name} Group",
            f"The {org_data.name}",
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "name_already_taken",
                "message": f"The organization name '{org_data.name}' is already in use. Please choose a different name.",
                "field": "name",
                "suggestions": suggestions,
                "hint": "Names are case-insensitive. You can reuse names from deleted organizations.",
            },
        )

    # Check organization count limit (Free tier can only create 1 organization)
    try:
        limit_enforcer = LimitEnforcer(db)
        limit_enforcer.check_organization_limit(current_user.id, raise_error=True)
    except LimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "limit_exceeded",
                "feature": e.feature,
                "current_tier": "Free",
                "current_limit": e.limit,
                "current_count": e.current,
                "message": str(e),
                "upgrade_message": e.upgrade_message,
                "upgrade_options": [
                    {
                        "tier": "Starter",
                        "price": "$29/month",
                        "organizations": 3,
                        "users": 25,
                    },
                    {
                        "tier": "Professional",
                        "price": "$99/month",
                        "organizations": 10,
                        "users": 100,
                    },
                ],
            },
        )

    # Create organization with error handling for UNIQUE constraint violations
    try:
        organization = Organization(
            id=str(uuid.uuid4()),
            name=org_data.name,
            slug=org_data.slug,
            description=org_data.description,
            currency=org_data.currency or "USD",
            timezone=org_data.timezone or "UTC",
            max_members=(
                org_data.max_members
                if org_data.max_members is not None
                else FREE_TIER_MAX_MEMBERS
            ),
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

        db.commit()
        db.refresh(organization)

        return organization

    except IntegrityError as e:
        db.rollback()

        # Check if it's a UNIQUE constraint error on slug
        error_message = str(e)
        if "UNIQUE constraint failed: organizations.slug" in error_message or "slug" in error_message.lower():
            logger.error(
                f"UNIQUE constraint violation on slug '{org_data.slug}' despite checks. "
                f"This indicates a race condition or incomplete cleanup. Error: {e}"
            )

            # Last resort: Try one more time after aggressive cleanup
            logger.warning(f"Attempting aggressive cleanup for slug '{org_data.slug}'")
            try:
                # Hard delete ALL organizations (active and inactive) with this slug except active ones
                conflicting_orgs = (
                    db.query(Organization)
                    .filter(Organization.slug == org_data.slug)
                    .filter(Organization.is_active == False)
                    .all()
                )
                for org in conflicting_orgs:
                    db.delete(org)
                db.commit()

                logger.info(
                    f"Aggressive cleanup removed {len(conflicting_orgs)} "
                    f"soft-deleted organizations with slug '{org_data.slug}'"
                )
            except Exception as cleanup_error:
                logger.error(f"Aggressive cleanup failed: {cleanup_error}")

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "slug_conflict",
                    "message": f"The slug '{org_data.slug}' is already in use. Please try a different slug or contact support.",
                    "field": "slug",
                    "suggestions": [
                        f"{org_data.slug}-new",
                        f"{org_data.slug}-{uuid.uuid4().hex[:6]}",
                        f"my-{org_data.slug}",
                    ],
                },
            )
        else:
            # Some other integrity error
            logger.error(f"Unexpected IntegrityError during organization creation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while creating the organization. Please try again.",
            )


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
    subscription = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == organization_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        )
        .first()
    )
    if not subscription:
        organization.max_members = FREE_TIER_MAX_MEMBERS
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

    # Soft delete organization AND its members
    organization.is_active = False

    # Also deactivate all organization members
    for member in members:
        member.is_active = False

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
    from sqlalchemy.orm import joinedload

    # Verify access
    TenantAwareQuery.ensure_organization_access(organization_id, current_user.id, db)

    # ⚡ PERFORMANCE FIX: Use eager loading to prevent N+1 query
    # BEFORE: 1 query for members + N queries for users (26 queries for 25 members!)
    # AFTER: 1 query with JOIN (2 queries total = -92% reduction)
    members = (
        db.query(OrganizationMember)
        .options(joinedload(OrganizationMember.user))  # Eager load user relationship
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .all()
    )

    # Build response using eager-loaded user data
    result = []
    for member in members:
        if member.user:  # User is already loaded from the JOIN
            result.append(
                {
                    "id": member.id,
                    "user_id": member.user.id,
                    "email": member.user.email,
                    "full_name": member.user.full_name,
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

    # SECURITY FIX (CRITICAL-2): Prevent self-role modification
    if member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own role. Contact another administrator.",
        )

    # Cannot change owner role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role"
        )

    # SECURITY FIX (CRITICAL-1): Only OWNER can grant OWNER role
    if role == OrganizationRole.OWNER and user_role != OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization OWNER can grant OWNER role to others.",
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

    # SECURITY FIX (HIGH-2): Only OWNER can remove ADMINs
    if member.role == OrganizationRole.ADMIN and user_role != OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization OWNER can remove administrators.",
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
    await EmailService.send_organization_invitation_email(
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
