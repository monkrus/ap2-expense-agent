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
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..auth import get_current_active_user
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..billing.tier_limits import get_tier_limits
from ..cache import invalidate_user_cache
from ..database import get_db
from ..email_service import EmailService
from ..models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
    Subscription,
    SubscriptionTier,
    User,
)
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
            db.delete(org)
        db.flush()  # Ensure deletions are committed before checking active orgs

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

    # Get user's subscription tier
    user_subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .filter(Subscription.status.in_(["active", "trialing"]))
        .first()
    )

    # Determine tier (no subscription = Free tier)
    user_tier = user_subscription.tier if user_subscription else SubscriptionTier.FREE
    tier_limits = get_tier_limits(user_tier)

    # Check organization limit for this tier
    if tier_limits.max_organizations is not None:
        # Count how many ACTIVE organizations user already owns
        owned_orgs_count = (
            db.query(OrganizationMember)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .filter(OrganizationMember.user_id == current_user.id)
            .filter(OrganizationMember.role == OrganizationRole.OWNER)
            .filter(OrganizationMember.is_active == True)
            .filter(Organization.is_active == True)
            .count()
        )

        logger.info(
            f"Organization limit check: user={current_user.username}, "
            f"tier={user_tier.value}, owned_orgs={owned_orgs_count}, "
            f"limit={tier_limits.max_organizations}"
        )

        if owned_orgs_count >= tier_limits.max_organizations:
            logger.warning(
                f"Organization limit reached: user={current_user.username}, "
                f"count={owned_orgs_count}, limit={tier_limits.max_organizations}"
            )

            # Get next tier suggestion based on current tier
            upgrade_suggestions = {
                SubscriptionTier.FREE: {
                    "next_tier": "Starter",
                    "next_tier_orgs": 3,
                    "price": "$29/month",
                },
                SubscriptionTier.STARTER: {
                    "next_tier": "Pro",
                    "next_tier_orgs": 10,
                    "price": "$99/month",
                },
                SubscriptionTier.PROFESSIONAL: {
                    "next_tier": "Enterprise",
                    "next_tier_orgs": 25,
                    "price": "$399/month",
                },
            }

            suggestion = upgrade_suggestions.get(user_tier)

            # Build user-friendly message
            if suggestion:
                friendly_message = (
                    f"You've reached your plan's limit of {tier_limits.max_organizations} "
                    f"organization{'s' if tier_limits.max_organizations != 1 else ''}. "
                    f"Upgrade to {suggestion['next_tier']} ({suggestion['price']}) "
                    f"to create up to {suggestion['next_tier_orgs']} organizations."
                )
            else:
                # Enterprise users hitting limit
                friendly_message = (
                    f"You've reached your plan's limit of {tier_limits.max_organizations} organizations. "
                    f"Please contact support for custom enterprise solutions."
                )

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "organization_limit_reached",
                    "message": friendly_message,
                    "upgrade_required": True,
                    "current_tier": tier_limits.name,
                    "current_limit": tier_limits.max_organizations,
                    "current_count": owned_orgs_count,
                    "upgrade_options": suggestion if suggestion else None,
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

    # Note: Organization-level billing subscriptions are managed separately
    # The user-level subscription (created above) controls tier limits
    # Organization-specific billing (GCP Marketplace) is handled via webhooks

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
