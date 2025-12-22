"""
Onboarding API Routes
Customer onboarding flow for new users
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..onboarding import OnboardingService

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str


class InviteTeamRequest(BaseModel):
    organization_id: str
    emails: List[EmailStr]


class AddPaymentMethodRequest(BaseModel):
    stripe_payment_method_id: str


@router.get("/status")
async def get_onboarding_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current onboarding progress"""
    service = OnboardingService(db)
    return service._get_onboarding_progress(current_user)


@router.post("/start")
async def start_onboarding(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Start onboarding flow"""
    service = OnboardingService(db)
    return service.start_onboarding(current_user)


@router.post("/steps/{step}/complete")
async def complete_onboarding_step(
    step: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark onboarding step as complete"""
    service = OnboardingService(db)
    return service.complete_step(current_user, step)


@router.post("/organization")
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create organization as part of onboarding"""
    service = OnboardingService(db)
    org = service.create_organization_step(
        user=current_user, org_name=request.name, org_slug=request.slug
    )
    return {"organization_id": org.id, "name": org.name, "slug": org.slug}


@router.post("/invite-team")
async def invite_team(
    request: InviteTeamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite team members as part of onboarding"""
    service = OnboardingService(db)
    invitation_ids = service.invite_team_step(
        user=current_user,
        organization_id=request.organization_id,
        email_addresses=request.emails,
    )
    return {"invitations_sent": len(invitation_ids), "invitation_ids": invitation_ids}


@router.post("/payment-method")
async def add_payment_method(
    request: AddPaymentMethodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add payment method as part of onboarding"""
    service = OnboardingService(db)
    result = service.add_payment_method_step(
        user=current_user, stripe_payment_method_id=request.stripe_payment_method_id
    )
    return result
