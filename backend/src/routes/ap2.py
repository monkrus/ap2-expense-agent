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
    nonce: str  # Required for replay attack protection
    timestamp: str  # ISO format timestamp


class CompleteAP2FlowRequest(BaseModel):
    items: List[Dict]
    merchant: str
    constraints: Optional[Dict] = None
    stripe_customer_id: Optional[str] = None


class RevokeMandateRequest(BaseModel):
    reason: str
    revoke_dependents: bool = True


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

    Security:
    - Requires nonce to prevent replay attacks
    - Timestamp must be within ±5 minutes of server time
    - Each nonce can only be used once
    """
    from ..security.nonce_service import get_nonce_service
    from datetime import datetime

    # Validate nonce and timestamp (replay attack protection)
    nonce_service = get_nonce_service(db)

    try:
        request_timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format. Use ISO 8601 format."
        )

    # Validate and store nonce
    try:
        nonce_valid = nonce_service.validate_and_store_nonce(
            nonce=request.nonce,
            request_timestamp=request_timestamp,
            endpoint="execute_payment",
            user_id=current_user.id
        )

        if not nonce_valid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nonce already used. Possible replay attack detected."
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

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


@router.post("/intent-mandate/{mandate_id}/revoke")
async def revoke_intent_mandate(
    mandate_id: str,
    request: RevokeMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke Intent Mandate - GDPR Right to Withdraw Consent

    This endpoint allows users to revoke their payment authorization.
    When revoked, all dependent cart and payment mandates are also revoked.

    Args:
        mandate_id: Intent mandate ID to revoke
        request: Revocation request with reason
        current_user: Authenticated user (must be mandate owner)

    Returns:
        Revocation status and affected mandates

    GDPR Compliance:
    - Article 7(3): Right to withdraw consent at any time
    - Creates immutable audit log of revocation
    - Cannot be undone (mandate status changes to 'revoked')
    """
    from ..models import CartMandate, IntentMandate, PaymentMandate

    # Get intent mandate
    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=mandate_id, user_id=current_user.id)
        .first()
    )

    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent mandate not found or you don't have permission to revoke it"
        )

    if intent_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intent mandate is already revoked"
        )

    # Revoke intent mandate
    intent_mandate.status = "revoked"
    intent_mandate.revoked_at = datetime.utcnow()
    intent_mandate.revocation_reason = request.reason

    revoked_carts = []
    revoked_payments = []

    # Cascade revoke dependent mandates if requested
    if request.revoke_dependents:
        # Revoke all associated cart mandates
        cart_mandates = (
            db.query(CartMandate)
            .filter_by(intent_mandate_id=mandate_id)
            .filter(CartMandate.status.in_(["pending", "approved"]))
            .all()
        )

        for cart in cart_mandates:
            cart.status = "revoked"
            cart.revoked_at = datetime.utcnow()
            revoked_carts.append(cart.id)

            # Revoke associated payment mandates
            payment_mandates = (
                db.query(PaymentMandate)
                .filter_by(cart_mandate_id=cart.id)
                .filter(PaymentMandate.status == "pending")
                .all()
            )

            for payment in payment_mandates:
                payment.status = "revoked"
                payment.revoked_at = datetime.utcnow()
                revoked_payments.append(payment.id)

    # Create audit log
    from ..services.audit_service import AuditService
    from ..models import AuditLog

    audit_log = AuditLog(
        id=str(__import__("uuid").uuid4()),
        user_id=current_user.id,
        action="mandate_revoked",
        resource_type="intent_mandate",
        resource_id=mandate_id,
        details=__import__("json").dumps({
            "reason": request.reason,
            "revoked_carts": revoked_carts,
            "revoked_payments": revoked_payments,
            "gdpr_article": "7.3",
            "revocation_timestamp": datetime.utcnow().isoformat(),
        })
    )
    db.add(audit_log)

    db.commit()

    return {
        "success": True,
        "intent_mandate_id": mandate_id,
        "status": "revoked",
        "revoked_at": intent_mandate.revoked_at.isoformat(),
        "dependent_mandates_revoked": request.revoke_dependents,
        "revoked_cart_mandates": len(revoked_carts),
        "revoked_payment_mandates": len(revoked_payments),
        "message": "Mandate successfully revoked. This action cannot be undone.",
    }


@router.post("/cart-mandate/{mandate_id}/revoke")
async def revoke_cart_mandate(
    mandate_id: str,
    request: RevokeMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke Cart Mandate

    Revokes a specific shopping cart before payment execution.
    Does not affect the parent Intent Mandate.

    Args:
        mandate_id: Cart mandate ID to revoke
        request: Revocation request with reason

    Returns:
        Revocation status
    """
    from ..models import CartMandate, IntentMandate, PaymentMandate

    # Get cart mandate and verify ownership through intent mandate
    cart_mandate = db.query(CartMandate).filter_by(id=mandate_id).first()

    if not cart_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart mandate not found"
        )

    # Verify user owns the parent intent mandate
    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=cart_mandate.intent_mandate_id, user_id=current_user.id)
        .first()
    )

    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke this cart mandate"
        )

    if cart_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart mandate is already revoked"
        )

    # Revoke cart mandate
    cart_mandate.status = "revoked"
    cart_mandate.revoked_at = datetime.utcnow()
    cart_mandate.revocation_reason = request.reason

    # Revoke dependent payment mandates
    revoked_payments = []
    if request.revoke_dependents:
        payment_mandates = (
            db.query(PaymentMandate)
            .filter_by(cart_mandate_id=mandate_id)
            .filter(PaymentMandate.status == "pending")
            .all()
        )

        for payment in payment_mandates:
            payment.status = "revoked"
            payment.revoked_at = datetime.utcnow()
            revoked_payments.append(payment.id)

    db.commit()

    return {
        "success": True,
        "cart_mandate_id": mandate_id,
        "status": "revoked",
        "revoked_at": cart_mandate.revoked_at.isoformat(),
        "revoked_payment_mandates": len(revoked_payments),
    }


@router.post("/payment-mandate/{mandate_id}/revoke")
async def revoke_payment_mandate(
    mandate_id: str,
    request: RevokeMandateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke Payment Mandate

    Cancels a pending payment before execution.
    Can only revoke payments that haven't been processed yet.

    Args:
        mandate_id: Payment mandate ID to revoke
        request: Revocation request with reason

    Returns:
        Revocation status
    """
    from ..models import CartMandate, IntentMandate, PaymentMandate

    # Get payment mandate
    payment_mandate = db.query(PaymentMandate).filter_by(id=mandate_id).first()

    if not payment_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment mandate not found"
        )

    # Verify ownership through cart → intent chain
    cart_mandate = db.query(CartMandate).filter_by(id=payment_mandate.cart_mandate_id).first()
    if not cart_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated cart mandate not found"
        )

    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=cart_mandate.intent_mandate_id, user_id=current_user.id)
        .first()
    )

    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke this payment mandate"
        )

    # Can only revoke pending payments
    if payment_mandate.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke completed payment. Contact support for refunds."
        )

    if payment_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment mandate is already revoked"
        )

    # Revoke payment mandate
    payment_mandate.status = "revoked"
    payment_mandate.revoked_at = datetime.utcnow()
    payment_mandate.revocation_reason = request.reason

    db.commit()

    return {
        "success": True,
        "payment_mandate_id": mandate_id,
        "status": "revoked",
        "revoked_at": payment_mandate.revoked_at.isoformat(),
        "message": "Payment cancelled successfully",
    }
