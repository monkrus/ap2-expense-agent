"""
AP2 Protocol Payment API endpoints
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing import UsageTracker
from ..database import get_db
from ..models import User
from ..payments import AP2PaymentService

router = APIRouter(prefix="/api/ap2", tags=["ap2-payments"])


# Pydantic models for requests/responses
class CreateIntentMandateRequest(BaseModel):
    constraints: Dict
    expiration_hours: int = 24


class CreateCartMandateRequest(BaseModel):
    intent_mandate_id: str
    items: List[Dict]
    merchant: str
    user_signature: str


class CreatePaymentMandateRequest(BaseModel):
    cart_mandate_id: str
    payment_method: str = "stripe"


class ExecutePaymentRequest(BaseModel):
    payment_mandate_id: str
    stripe_customer_id: Optional[str] = None


class CompleteAP2FlowRequest(BaseModel):
    items: List[Dict]
    merchant: str
    constraints: Optional[Dict] = None
    stripe_customer_id: Optional[str] = None


# AP2 Protocol endpoints
@router.post("/intent-mandate")
async def create_intent_mandate(
    request: CreateIntentMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Intent Mandate - User authorizes AI agent to make purchases

    Example constraints:
    {
        "max_amount": 1000.00,
        "categories": ["office_supplies", "software"],
        "merchants": ["Amazon", "Microsoft"],
        "approval_required": true
    }
    """
    ap2_service = AP2PaymentService(db)

    intent_mandate = await ap2_service.create_intent_mandate(
        user_id=current_user.id,
        constraints=request.constraints,
        expiration_hours=request.expiration_hours,
    )

    return {
        "success": True,
        "intent_mandate_id": intent_mandate.id,
        "status": intent_mandate.status,
        "timestamp": intent_mandate.timestamp,
        "expiration": intent_mandate.expiration,
        "signature": intent_mandate.signature,
    }


@router.post("/cart-mandate")
async def create_cart_mandate(
    request: CreateCartMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Cart Mandate - Specific items for approval

    Example items:
    [
        {
            "id": "exp-123",
            "description": "Office supplies",
            "amount": 45.99,
            "category": "office_supplies"
        }
    ]
    """
    ap2_service = AP2PaymentService(db)

    cart_mandate = await ap2_service.create_cart_mandate(
        intent_mandate_id=request.intent_mandate_id,
        items=request.items,
        merchant=request.merchant,
        user_signature=request.user_signature,
    )

    return {
        "success": True,
        "cart_mandate_id": cart_mandate.id,
        "status": cart_mandate.status,
        "total": float(cart_mandate.total),
        "merchant": cart_mandate.merchant,
        "items_count": len(request.items),
        "timestamp": cart_mandate.timestamp,
    }


@router.post("/payment-mandate")
async def create_payment_mandate(
    request: CreatePaymentMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Payment Mandate - Prepare for payment execution
    """
    ap2_service = AP2PaymentService(db)

    payment_mandate = await ap2_service.create_payment_mandate(
        cart_mandate_id=request.cart_mandate_id, payment_method=request.payment_method
    )

    return {
        "success": True,
        "payment_mandate_id": payment_mandate.id,
        "status": payment_mandate.status,
        "payment_method": payment_mandate.payment_method,
        "timestamp": payment_mandate.timestamp,
    }


@router.post("/execute-payment")
async def execute_payment(
    request: ExecutePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute payment using Stripe

    This is the final step in the AP2 flow.
    """
    ap2_service = AP2PaymentService(db)

    # Track AP2 transaction usage
    tracker = UsageTracker(db)
    tracker.track_usage(
        user_id=current_user.id, usage_type="ap2_transaction", quantity=1
    )

    payment_result = await ap2_service.execute_payment(
        payment_mandate_id=request.payment_mandate_id,
        stripe_customer_id=request.stripe_customer_id,
    )

    return payment_result


@router.post("/complete-flow")
async def complete_ap2_flow(
    request: CompleteAP2FlowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Complete full AP2 payment flow in one API call

    This is a convenience endpoint that:
    1. Creates Intent Mandate
    2. Creates Cart Mandate
    3. Creates Payment Mandate
    4. Executes Payment

    Use this for simple payment flows. For complex flows with user approvals,
    use individual endpoints.
    """
    ap2_service = AP2PaymentService(db)

    # Track AP2 transaction usage
    tracker = UsageTracker(db)
    tracker.track_usage(
        user_id=current_user.id, usage_type="ap2_transaction", quantity=1
    )

    result = await ap2_service.complete_ap2_flow(
        user_id=current_user.id,
        items=request.items,
        merchant=request.merchant,
        constraints=request.constraints,
        stripe_customer_id=request.stripe_customer_id,
    )

    return result


@router.get("/mandate/{mandate_id}/status")
async def get_mandate_status(
    mandate_id: str,
    mandate_type: str = "payment",  # intent, cart, or payment
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of any mandate

    mandate_type: intent, cart, or payment
    """
    ap2_service = AP2PaymentService(db)

    status_info = await ap2_service.get_mandate_status(
        mandate_id=mandate_id, mandate_type=mandate_type
    )

    return status_info


@router.get("/user/mandates")
async def get_user_mandates(
    mandate_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all mandates for current user

    Args:
        mandate_type: Filter by type (intent, cart, payment)
        status_filter: Filter by status (active, pending, completed, failed)
        limit: Max number of results
    """
    from ..models import CartMandate, IntentMandate, PaymentMandate

    results = []

    if mandate_type is None or mandate_type == "intent":
        query = db.query(IntentMandate).filter(IntentMandate.user_id == current_user.id)
        if status_filter:
            query = query.filter(IntentMandate.status == status_filter)
        intent_mandates = (
            query.order_by(IntentMandate.created_at.desc()).limit(limit).all()
        )

        for mandate in intent_mandates:
            results.append(
                {
                    "type": "intent",
                    "id": mandate.id,
                    "status": mandate.status,
                    "timestamp": mandate.timestamp,
                    "expiration": mandate.expiration,
                    "created_at": mandate.created_at,
                }
            )

    if mandate_type is None or mandate_type == "cart":
        query = (
            db.query(CartMandate)
            .join(IntentMandate)
            .filter(IntentMandate.user_id == current_user.id)
        )
        if status_filter:
            query = query.filter(CartMandate.status == status_filter)
        cart_mandates = query.order_by(CartMandate.created_at.desc()).limit(limit).all()

        for mandate in cart_mandates:
            results.append(
                {
                    "type": "cart",
                    "id": mandate.id,
                    "status": mandate.status,
                    "total": float(mandate.total),
                    "merchant": mandate.merchant,
                    "timestamp": mandate.timestamp,
                    "created_at": mandate.created_at,
                }
            )

    if mandate_type is None or mandate_type == "payment":
        query = (
            db.query(PaymentMandate)
            .join(CartMandate)
            .join(IntentMandate)
            .filter(IntentMandate.user_id == current_user.id)
        )
        if status_filter:
            query = query.filter(PaymentMandate.status == status_filter)
        payment_mandates = (
            query.order_by(PaymentMandate.created_at.desc()).limit(limit).all()
        )

        for mandate in payment_mandates:
            results.append(
                {
                    "type": "payment",
                    "id": mandate.id,
                    "status": mandate.status,
                    "payment_method": mandate.payment_method,
                    "timestamp": mandate.timestamp,
                    "created_at": mandate.created_at,
                }
            )

    # Sort by created_at
    results.sort(key=lambda x: x["created_at"], reverse=True)

    return {"mandates": results[:limit], "count": len(results)}


@router.get("/stats")
async def get_ap2_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get AP2 usage statistics for current user
    """
    from sqlalchemy import func

    from ..models import CartMandate, IntentMandate, PaymentMandate

    # Count mandates by type and status
    intent_stats = (
        db.query(IntentMandate.status, func.count(IntentMandate.id).label("count"))
        .filter(IntentMandate.user_id == current_user.id)
        .group_by(IntentMandate.status)
        .all()
    )

    cart_stats = (
        db.query(CartMandate.status, func.count(CartMandate.id).label("count"))
        .join(IntentMandate)
        .filter(IntentMandate.user_id == current_user.id)
        .group_by(CartMandate.status)
        .all()
    )

    payment_stats = (
        db.query(PaymentMandate.status, func.count(PaymentMandate.id).label("count"))
        .join(CartMandate)
        .join(IntentMandate)
        .filter(IntentMandate.user_id == current_user.id)
        .group_by(PaymentMandate.status)
        .all()
    )

    # Calculate total amount processed
    total_amount = (
        db.query(func.sum(CartMandate.total))
        .join(PaymentMandate)
        .join(IntentMandate)
        .filter(
            IntentMandate.user_id == current_user.id,
            PaymentMandate.status == "completed",
        )
        .scalar()
        or 0
    )

    return {
        "intent_mandates": {stat.status: stat.count for stat in intent_stats},
        "cart_mandates": {stat.status: stat.count for stat in cart_stats},
        "payment_mandates": {stat.status: stat.count for stat in payment_stats},
        "total_amount_processed": float(total_amount),
    }
