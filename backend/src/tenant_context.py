"""
Multi-Tenancy Context and Middleware
Provides organization isolation and tenant-aware database queries
"""

from contextvars import ContextVar
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .models import Organization, OrganizationMember
from .models_billing import OrganizationSubscription

# Thread-safe context variable for current organization
current_organization: ContextVar[Optional[str]] = ContextVar(
    "current_organization", default=None
)

FREE_TIER_MAX_MEMBERS = 2


def _get_active_subscription_org_ids(org_ids: list, db: Session) -> set:
    if not org_ids:
        return set()
    rows = (
        db.query(OrganizationSubscription.organization_id)
        .filter(
            OrganizationSubscription.organization_id.in_(org_ids),
            OrganizationSubscription.status.in_(["active", "trialing"]),
        )
        .all()
    )
    return {row[0] for row in rows}


def resolve_org_max_members(organization: Organization, subscribed_org_ids: set) -> int:
    if organization.id not in subscribed_org_ids:
        return FREE_TIER_MAX_MEMBERS
    return organization.max_members or FREE_TIER_MAX_MEMBERS


class TenantContext:
    """Manage tenant/organization context for multi-tenancy"""

    @staticmethod
    def set_organization(organization_id: str):
        """Set the current organization context"""
        current_organization.set(organization_id)

    @staticmethod
    def get_organization() -> Optional[str]:
        """Get the current organization context"""
        return current_organization.get()

    @staticmethod
    def clear():
        """Clear the current organization context"""
        current_organization.set(None)

    @staticmethod
    def require_organization() -> str:
        """Get organization or raise error if not set"""
        org_id = current_organization.get()
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization context required. Please select an organization.",
            )
        return org_id


def get_user_organizations(user_id: str, db: Session) -> list:
    """Get all organizations a user belongs to"""
    memberships = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id, OrganizationMember.is_active == True
        )
        .all()
    )

    org_ids = [m.organization_id for m in memberships]
    organizations = (
        db.query(Organization)
        .filter(Organization.id.in_(org_ids), Organization.is_active == True)
        .all()
    )

    subscribed_org_ids = _get_active_subscription_org_ids(org_ids, db)

    return [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "currency": org.currency,
            "timezone": org.timezone,
            "max_members": resolve_org_max_members(org, subscribed_org_ids),
            "is_active": org.is_active,
            "created_at": org.created_at,
            "role": next(
                (
                    m.role.value if hasattr(m.role, "value") else m.role
                    for m in memberships
                    if m.organization_id == org.id
                ),
                None,
            ),
        }
        for org in organizations
    ]


def get_user_organization_role(
    user_id: str, organization_id: str, db: Session
) -> Optional[str]:
    """Get user's role in a specific organization"""
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    return (
        membership.role.value
        if membership and hasattr(membership.role, "value")
        else (membership.role if membership else None)
    )


def verify_organization_access(user_id: str, organization_id: str, db: Session) -> bool:
    """Verify user has access to organization"""
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not membership:
        return False

    # Check organization is active
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id, Organization.is_active == True)
        .first()
    )

    return organization is not None


async def tenant_middleware(request: Request, call_next):
    """
    Middleware to extract and set organization context from request
    Expects organization ID in header: X-Organization-Id
    """
    # Clear any existing context
    TenantContext.clear()

    # Get organization from header
    org_id = request.headers.get("X-Organization-Id")

    if org_id:
        # Set organization context
        TenantContext.set_organization(org_id)

    # Process request
    response = await call_next(request)

    # Clear context after request
    TenantContext.clear()

    return response


class TenantAwareQuery:
    """Helper class for tenant-aware database queries"""

    @staticmethod
    def filter_by_organization(query, model):
        """
        Add organization filter to query if organization context is set
        Usage: query = TenantAwareQuery.filter_by_organization(query, Expense)
        """
        org_id = TenantContext.get_organization()
        if org_id and hasattr(model, "organization_id"):
            query = query.filter(model.organization_id == org_id)
        return query

    @staticmethod
    def ensure_organization_access(organization_id: str, user_id: str, db: Session):
        """Ensure user has access to organization, raise 403 if not"""
        if not verify_organization_access(user_id, organization_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization",
            )


def get_organization_or_404(organization_id: str, db: Session) -> Organization:
    """Get organization or raise 404"""
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id, Organization.is_active == True)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    return organization


def create_default_organization_for_user(
    user_id: str, email: str, db: Session
) -> Organization:
    """Create a default personal organization for a new user"""
    import secrets
    import uuid

    from .models import OrganizationRole

    # Generate unique slug
    slug = f"personal-{secrets.token_hex(4)}"

    # Create organization
    organization = Organization(
        id=str(uuid.uuid4()),
        name=f"Personal Workspace",
        slug=slug,
        description="Your personal expense workspace",
        max_members=FREE_TIER_MAX_MEMBERS,
        is_active=True,
    )
    db.add(organization)
    db.flush()  # Get organization ID

    # Add user as owner
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=organization.id,
        user_id=user_id,
        role=OrganizationRole.OWNER,
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(organization)

    return organization
