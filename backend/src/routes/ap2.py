"""
AP2 Protocol Payment API endpoints
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..billing import UsageTracker
from ..database import get_db
from ..models import CartMandate, IntentMandate, PaymentMandate, User
from ..payments import AP2PaymentService
from ..rate_limit import limiter

router = APIRouter(prefix="/api/ap2", tags=["ap2-payments"])


def ensure_intent_mandate_owner(
    db: Session, intent_mandate_id: str, user_id: str
) -> IntentMandate:
    intent_mandate = (
        db.query(IntentMandate).filter_by(id=intent_mandate_id, user_id=user_id).first()
    )
    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent mandate not found",
        )
    return intent_mandate


def ensure_cart_mandate_owner(
    db: Session, cart_mandate_id: str, user_id: str
) -> CartMandate:
    cart_mandate = db.query(CartMandate).filter_by(id=cart_mandate_id).first()
    if not cart_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart mandate not found"
        )

    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=cart_mandate.intent_mandate_id, user_id=user_id)
        .first()
    )
    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this cart mandate",
        )
    return cart_mandate


def ensure_payment_mandate_owner(
    db: Session, payment_mandate_id: str, user_id: str
) -> PaymentMandate:
    payment_mandate = db.query(PaymentMandate).filter_by(id=payment_mandate_id).first()
    if not payment_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment mandate not found",
        )

    cart_mandate = (
        db.query(CartMandate).filter_by(id=payment_mandate.cart_mandate_id).first()
    )
    if not cart_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated cart mandate not found",
        )

    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=cart_mandate.intent_mandate_id, user_id=user_id)
        .first()
    )
    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this payment mandate",
        )

    return payment_mandate


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
    payment_method: str = "stripe"  # stripe, x402_stablecoin, expense_reimbursement
    stripe_customer_id: Optional[str] = None


class RevokeMandateRequest(BaseModel):
    reason: str
    revoke_dependents: bool = True


class CheckAutoApprovalRequest(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    category: str = Field(max_length=100)
    vendor: str = Field(max_length=255)


def _validate_constraints(constraints: Dict):
    """Validate mandate constraints. Reusable across endpoints."""
    # Reject missing max_amount - every mandate must have a spending cap
    if not constraints or not constraints.get("max_amount"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraints must include max_amount (maximum amount per transaction)",
        )

    # Validate max_amount is numeric and positive
    max_amount = constraints.get("max_amount")
    try:
        max_amount = float(max_amount)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraint validation error: max_amount must be a number",
        )
    if max_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraint validation error: max_amount must be greater than zero",
        )

    # Validate monthly_limit if provided
    monthly_limit = constraints.get("monthly_limit")
    if monthly_limit is not None:
        try:
            monthly_limit = float(monthly_limit)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Constraint validation error: monthly_limit must be a number",
            )
        if monthly_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Constraint validation error: monthly_limit must be greater than zero",
            )
        if monthly_limit < max_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Constraint validation error: monthly_limit must be greater than or equal to max_amount",
            )


def _validate_complete_flow_request(data: CompleteAP2FlowRequest):
    """Validate complete-flow request data before processing."""
    # Validate merchant is not empty
    if not data.merchant or not data.merchant.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant name is required and cannot be empty",
        )

    # Validate merchant length
    if len(data.merchant) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merchant name cannot exceed 255 characters",
        )

    # Validate items is not empty
    if not data.items or len(data.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one item is required",
        )

    # Validate each item
    for i, item in enumerate(data.items):
        if "amount" not in item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {i + 1} is missing the 'amount' field",
            )
        try:
            amount = float(item["amount"])
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {i + 1} has an invalid amount",
            )
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {i + 1} amount must be greater than zero",
            )
        if not item.get("description") or not str(item["description"]).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {i + 1} is missing a description",
            )
        if len(str(item.get("description", ""))) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {i + 1} description cannot exceed 500 characters",
            )


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
    # VALIDATION: Validate constraints before creating mandate
    constraints = request.constraints or {}

    # Use shared constraint validation
    _validate_constraints(constraints)

    # Reject missing monthly_limit - every mandate must have a monthly spending cap
    if not constraints.get("monthly_limit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraints must include monthly_limit (total monthly spending cap)",
        )

    # Require at least one category restriction
    has_category = bool(constraints.get("categories") or constraints.get("category"))
    if not has_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraints must include at least one category",
        )

    # Validate expiration_hours is positive
    if request.expiration_hours is not None and request.expiration_hours <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Constraint validation error: expiration_hours must be greater than zero",
        )

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
        # AP2 2026: Agent identity
        "agent_id": intent_mandate.agent_id,
        "authorization_type": intent_mandate.authorization_type,
        "a2a_protocol_version": intent_mandate.a2a_protocol_version,
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
    if not request.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart must contain at least one item",
        )

    ap2_service = AP2PaymentService(db)

    ensure_intent_mandate_owner(db, request.intent_mandate_id, current_user.id)

    try:
        cart_mandate = await ap2_service.create_cart_mandate(
            intent_mandate_id=request.intent_mandate_id,
            items=request.items,
            merchant=request.merchant,
            user_signature=request.user_signature,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    from ..payments.ap2_service import AP2_JSONLD_CONTEXT, AP2_PROTOCOL_VERSION

    return {
        "@context": AP2_JSONLD_CONTEXT,
        "@type": "CartMandate",
        "success": True,
        "cart_mandate_id": cart_mandate.id,
        "status": cart_mandate.status,
        "total": float(cart_mandate.total),
        "merchant": cart_mandate.merchant,
        "items_count": len(request.items),
        "timestamp": cart_mandate.timestamp,
        # AP2 2026: UCP fields
        "ucp_order_id": cart_mandate.ucp_order_id,
        "merchant_agent_signature": cart_mandate.merchant_agent_signature is not None,
    }


@router.post("/payment-mandate")
@limiter.limit("20/minute")  # Rate limit: 20 payment mandate creations per minute
async def create_payment_mandate(
    request: Request,  # Required by rate limiter
    data: CreatePaymentMandateRequest,  # Renamed to avoid conflict
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create Payment Mandate - Prepare for payment execution
    """
    ap2_service = AP2PaymentService(db)

    ensure_cart_mandate_owner(db, data.cart_mandate_id, current_user.id)

    payment_mandate = await ap2_service.create_payment_mandate(
        cart_mandate_id=data.cart_mandate_id, payment_method=data.payment_method
    )

    from ..payments.ap2_service import AP2_JSONLD_CONTEXT, AP2_PROTOCOL_VERSION

    # Parse agent signal summary for response
    agent_signal_summary = None
    if payment_mandate.agent_signal:
        try:
            import json as _json

            sig = _json.loads(payment_mandate.agent_signal)
            agent_signal_summary = {
                "agent_id": sig.get("agent_id"),
                "authorization_type": sig.get("authorization_type"),
                "confidence_score": sig.get("confidence_score"),
            }
        except Exception:
            pass

    return {
        "@context": AP2_JSONLD_CONTEXT,
        "@type": "PaymentMandate",
        "success": True,
        "payment_mandate_id": payment_mandate.id,
        "status": payment_mandate.status,
        "payment_method": payment_mandate.payment_method,
        "timestamp": payment_mandate.timestamp,
        "agent_signal": agent_signal_summary,
    }


@router.post("/execute-payment")
@limiter.limit("10/minute")  # Rate limit: 10 payments per minute per user
async def execute_payment(
    request: Request,  # Required by rate limiter
    data: ExecutePaymentRequest,  # Renamed to avoid conflict
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
    from datetime import datetime

    from ..security.nonce_service import get_nonce_service

    ensure_payment_mandate_owner(db, data.payment_mandate_id, current_user.id)

    # Validate nonce and timestamp (replay attack protection)
    nonce_service = get_nonce_service(db)

    try:
        request_timestamp = datetime.fromisoformat(
            data.timestamp.replace("Z", "+00:00")
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format. Use ISO 8601 format.",
        )

    # Validate and store nonce
    try:
        nonce_valid = nonce_service.validate_and_store_nonce(
            nonce=data.nonce,
            request_timestamp=request_timestamp,
            endpoint="execute_payment",
            user_id=current_user.id,
        )

        if not nonce_valid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nonce already used. Possible replay attack detected.",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Check AP2 transaction limit BEFORE executing payment (BILLING ENFORCEMENT)
    from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
    from ..models import OrganizationMember

    # Get user's organization
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .filter(OrganizationMember.is_active == True)
        .first()
    )

    if membership:
        try:
            limit_enforcer = LimitEnforcer(db)
            limit_enforcer.check_ap2_transaction_limit(
                membership.organization_id, raise_error=True
            )
        except LimitExceededError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)
            )

    ap2_service = AP2PaymentService(db)

    # Track AP2 transaction usage
    tracker = UsageTracker(db)
    try:
        tracker.track_usage(
            user_id=current_user.id, usage_type="ap2_transaction", quantity=1
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        )

    payment_result = await ap2_service.execute_payment(
        payment_mandate_id=data.payment_mandate_id,
        stripe_customer_id=data.stripe_customer_id,
    )

    return payment_result


@router.post("/complete-flow")
@limiter.limit("5/minute")  # Rate limit: 5 complete flows per minute per user
async def complete_ap2_flow(
    request: Request,  # Required by rate limiter - must be first and named 'request'
    data: CompleteAP2FlowRequest,  # Renamed to avoid parameter conflict
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
    # Validate request data before processing
    _validate_complete_flow_request(data)

    # Validate constraints if provided by the caller
    if data.constraints:
        _validate_constraints(data.constraints)

    # CRITICAL: Check AP2 transaction limit BEFORE processing (FREE TIER ENFORCEMENT)
    from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
    from ..models import OrganizationMember

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .filter(OrganizationMember.is_active == True)
        .first()
    )

    if membership:
        try:
            limit_enforcer = LimitEnforcer(db)
            limit_enforcer.check_ap2_transaction_limit(
                membership.organization_id, raise_error=True
            )
        except LimitExceededError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)
            )

    ap2_service = AP2PaymentService(db)

    # Track AP2 transaction usage
    tracker = UsageTracker(db)
    try:
        tracker.track_usage(
            user_id=current_user.id, usage_type="ap2_transaction", quantity=1
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        )

    try:
        result = await ap2_service.complete_ap2_flow(
            user_id=current_user.id,
            items=data.items,
            merchant=data.merchant,
            constraints=data.constraints,
            payment_method=data.payment_method,
            stripe_customer_id=data.stripe_customer_id,
        )
    except ValueError as exc:
        # Convert validation errors to proper HTTP 400 responses
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

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

    if mandate_type == "intent":
        ensure_intent_mandate_owner(db, mandate_id, current_user.id)
    elif mandate_type == "cart":
        ensure_cart_mandate_owner(db, mandate_id, current_user.id)
    elif mandate_type == "payment":
        ensure_payment_mandate_owner(db, mandate_id, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mandate type: {mandate_type}",
        )

    status_info = await ap2_service.get_mandate_status(
        mandate_id=mandate_id, mandate_type=mandate_type
    )

    return status_info


@router.get("/user/mandates")
async def get_user_mandates(
    mandate_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all mandates for current user

    Args:
        mandate_type: Filter by type (intent, cart, payment)
        status_filter: Filter by status (active, pending, completed, failed)
        include_deleted: Include deleted/archived mandates (default: False)
        limit: Max number of results
    """
    import logging

    from ..models import CartMandate, IntentMandate, PaymentMandate

    logger = logging.getLogger(__name__)
    logger.info(
        f"get_user_mandates: include_deleted={include_deleted} (type: {type(include_deleted)})"
    )

    results = []

    if mandate_type is None or mandate_type == "intent":
        query = db.query(IntentMandate).filter(IntentMandate.user_id == current_user.id)

        # Exclude deleted mandates by default unless explicitly requested
        if not include_deleted:
            logger.info(
                f"Filtering out deleted mandates (include_deleted={include_deleted})"
            )
            query = query.filter(IntentMandate.status != "deleted")
        else:
            logger.info(
                f"Including deleted mandates (include_deleted={include_deleted})"
            )

        if status_filter:
            query = query.filter(IntentMandate.status == status_filter)
        intent_mandates = (
            query.order_by(IntentMandate.created_at.desc()).limit(limit).all()
        )

        for mandate in intent_mandates:
            # Parse constraints JSON
            import json
            from datetime import datetime

            constraints = {}
            try:
                raw = json.loads(mandate.constraints) if mandate.constraints else {}
                # Strip JSON-LD envelope fields for display
                constraints = {k: v for k, v in raw.items() if not k.startswith("@")}
            except Exception:
                constraints = {}

            # Check if mandate has expired and update status if needed
            current_status = mandate.status
            if mandate.expiration and mandate.expiration < datetime.utcnow():
                if mandate.status == "active":
                    mandate.status = "expired"
                    db.commit()
                current_status = "expired"

            results.append(
                {
                    "type": "intent",
                    "id": mandate.id,
                    "status": current_status,
                    "timestamp": mandate.timestamp,
                    "expiration": mandate.expiration,
                    "created_at": mandate.created_at,
                    "merchant": constraints.get("merchant")
                    or (
                        constraints.get("merchants", [None])[0]
                        if isinstance(constraints.get("merchants"), list)
                        else None
                    ),
                    "max_amount": constraints.get("max_amount"),
                    "monthly_limit": constraints.get("monthly_limit"),
                    "category": constraints.get("category")
                    or (
                        constraints.get("categories", [None])[0]
                        if isinstance(constraints.get("categories"), list)
                        else None
                    ),
                    "constraints": constraints,
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
            # Include total from parent cart mandate
            cart = db.query(CartMandate).filter_by(id=mandate.cart_mandate_id).first()
            results.append(
                {
                    "type": "payment",
                    "id": mandate.id,
                    "cart_mandate_id": mandate.cart_mandate_id,
                    "status": mandate.status,
                    "payment_method": mandate.payment_method,
                    "total": float(cart.total) if cart else None,
                    "merchant": cart.merchant if cart else None,
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

    # First, expire any active mandates that have passed their expiration date
    expired_mandates = (
        db.query(IntentMandate)
        .filter(
            IntentMandate.user_id == current_user.id,
            IntentMandate.status == "active",
            IntentMandate.expiration < datetime.utcnow(),
        )
        .all()
    )
    for mandate in expired_mandates:
        mandate.status = "expired"
    if expired_mandates:
        db.commit()

    # Count mandates by type and status (exclude deleted)
    intent_stats = (
        db.query(IntentMandate.status, func.count(IntentMandate.id).label("count"))
        .filter(
            IntentMandate.user_id == current_user.id,
            IntentMandate.status != "deleted",  # Exclude deleted from stats
        )
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


@router.delete("/mandate/{mandate_id}")
async def delete_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an Intent Mandate

    This soft-deletes the mandate by setting status to 'deleted'.
    """
    from ..models import IntentMandate

    # Get intent mandate
    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=mandate_id, user_id=current_user.id)
        .first()
    )

    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intent mandate not found or you don't have permission to delete it",
        )

    if intent_mandate.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intent mandate is already deleted",
        )

    # Soft delete by changing status
    intent_mandate.status = "deleted"
    db.commit()

    return {
        "success": True,
        "message": "Intent mandate deleted successfully",
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
            detail="Intent mandate not found or you don't have permission to revoke it",
        )

    if intent_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Intent mandate is already revoked",
        )

    # Validate reason is not empty
    if not request.reason or not request.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A revocation reason is required for audit compliance",
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
    from ..models import AuditLog
    from ..services.audit_service import AuditService

    audit_log = AuditLog(
        id=str(__import__("uuid").uuid4()),
        user_id=current_user.id,
        action="mandate_revoked",
        resource_type="intent_mandate",
        resource_id=mandate_id,
        details=__import__("json").dumps(
            {
                "reason": request.reason,
                "revoked_carts": revoked_carts,
                "revoked_payments": revoked_payments,
                "gdpr_article": "7.3",
                "revocation_timestamp": datetime.utcnow().isoformat(),
            }
        ),
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart mandate not found"
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
            detail="You don't have permission to revoke this cart mandate",
        )

    if cart_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart mandate is already revoked",
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment mandate not found"
        )

    # Verify ownership through cart → intent chain
    cart_mandate = (
        db.query(CartMandate).filter_by(id=payment_mandate.cart_mandate_id).first()
    )
    if not cart_mandate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated cart mandate not found",
        )

    intent_mandate = (
        db.query(IntentMandate)
        .filter_by(id=cart_mandate.intent_mandate_id, user_id=current_user.id)
        .first()
    )

    if not intent_mandate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke this payment mandate",
        )

    # Can only revoke pending payments
    if payment_mandate.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke completed payment. Contact support for refunds.",
        )

    if payment_mandate.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment mandate is already revoked",
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


# ============================================================================
# AP2 2026 Phase 2: Agent Discovery & Protocol Info
# ============================================================================


@router.get("/.well-known/agent.json")
async def agent_card():
    """
    A2A 1.0 Agent Card — standardized agent discovery endpoint.

    Used by other agents, GEAP (Gemini Enterprise Agent Platform), and
    orchestration platforms to discover this agent's capabilities.
    """
    from ..payments.ap2_service import (
        A2A_PROTOCOL_VERSION,
        AGENT_ID,
        AGENT_VERSION,
        AP2_JSONLD_CONTEXT,
        AP2_PROTOCOL_VERSION,
        PAYMENT_METHODS,
    )

    return {
        "@context": AP2_JSONLD_CONTEXT,
        "@type": "AgentCard",
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "name": "AP2 Expense Management Agent",
        "description": "AI-powered expense management with AP2 protocol payment verification",
        "protocol": {
            "ap2_version": AP2_PROTOCOL_VERSION,
            "a2a_version": A2A_PROTOCOL_VERSION,
        },
        "capabilities": [
            "intent_mandates",
            "cart_mandates",
            "payment_mandates",
            "complete_flow",
            "mandate_revocation",
            "agent_signal_hnp",
            "json_ld_mandates",
        ],
        "payment_methods": list(PAYMENT_METHODS.keys()),
        "endpoints": {
            "intent_mandate": "/api/ap2/intent-mandate",
            "cart_mandate": "/api/ap2/cart-mandate",
            "payment_mandate": "/api/ap2/payment-mandate",
            "execute_payment": "/api/ap2/execute-payment",
            "complete_flow": "/api/ap2/complete-flow",
            "mandate_status": "/api/ap2/mandate/{mandate_id}/status",
            "user_mandates": "/api/ap2/user/mandates",
            "stats": "/api/ap2/stats",
            "protocol_info": "/api/ap2/protocol-info",
            "agent_card": "/api/ap2/.well-known/agent.json",
        },
        "authentication": {
            "type": "bearer_token",
            "header": "Authorization",
        },
        "organization": {
            "header": "X-Organization-Id",
            "required": True,
        },
    }


@router.get("/protocol-info")
async def protocol_info():
    """
    AP2 protocol information — versions, capabilities, supported features.
    Public endpoint for frontend and external agent discovery.
    """
    from ..payments.ap2_service import (
        A2A_PROTOCOL_VERSION,
        AGENT_ID,
        AGENT_VERSION,
        AP2_JSONLD_CONTEXT,
        AP2_PROTOCOL_VERSION,
        PAYMENT_METHODS,
    )

    return {
        "@context": AP2_JSONLD_CONTEXT,
        "@type": "ProtocolInfo",
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "ap2_protocol_version": AP2_PROTOCOL_VERSION,
        "a2a_protocol_version": A2A_PROTOCOL_VERSION,
        "payment_methods": {k: v for k, v in PAYMENT_METHODS.items()},
        "features": {
            "json_ld_mandates": True,
            "agent_signal_hnp": True,
            "ucp_order_reference": True,
            "x402_stablecoin": False,  # Stub -- not yet live
            "mandate_revocation": True,
            "cryptographic_signing": True,
        },
    }


def _resolve_org_id(http_request: Request, db: Session, user_id: str) -> str:
    """Resolve organisation ID from header or user's membership."""
    org_id = http_request.headers.get("X-Organization-Id", "").strip()
    if not org_id:
        from ..models import OrganizationMember

        membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user_id,
                OrganizationMember.is_active == True,
            )
            .first()
        )
        org_id = membership.organization_id if membership else ""
    return org_id


# ── Auto-approval preview ──────────────────────────────────────────
@router.post("/check-auto-approval")
@limiter.limit("20/minute")
async def check_auto_approval(
    http_request: Request,
    request: CheckAutoApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview whether an expense would be auto-approved by an existing
    Intent Mandate. Does NOT create any records -- read-only check.
    """
    import json as _json

    ap2_service = AP2PaymentService(db)
    org_id = _resolve_org_id(http_request, db, current_user.id)

    matching_mandate = ap2_service.find_matching_intent_mandate(
        user_id=current_user.id,
        amount=request.amount,
        category=request.category,
        merchant=request.vendor,
        organization_id=org_id,
    )

    if matching_mandate:
        try:
            constraints = _json.loads(matching_mandate.constraints)
        except Exception:
            constraints = {}
        remaining_monthly = None
        monthly_limit = constraints.get("monthly_limit")
        if monthly_limit:
            current_usage = ap2_service._get_mandate_monthly_usage(
                matching_mandate.id, org_id
            )
            remaining_monthly = float(monthly_limit) - current_usage

        return {
            "will_auto_approve": True,
            "via": "intent_mandate",
            "mandate_id": matching_mandate.id,
            "mandate_constraints": {
                k: v for k, v in constraints.items() if not k.startswith("@")
            },
            "remaining_monthly": remaining_monthly,
        }

    # Also check approval policies as fallback info
    try:
        from ..models import Expense, ExpenseCategory
        from ..services.approval_policy_service import ApprovalPolicyService

        policy_service = ApprovalPolicyService(db)
        # Build a lightweight stub expense for evaluation
        stub = type(
            "Stub",
            (),
            {
                "amount": request.amount,
                "category": request.category,
                "vendor": request.vendor,
                "organization_id": org_id,
            },
        )()
        should_approve, policy, reason = policy_service.evaluate_expense(
            stub, current_user
        )
        if should_approve and policy:
            return {
                "will_auto_approve": True,
                "via": "approval_policy",
                "policy_name": policy.name,
                "policy_id": policy.id,
            }
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Approval policy check failed: {e}")

    return {"will_auto_approve": False}


# ── Suggest mandate from expense ────────────────────────────────────
@router.post("/suggest-mandate")
@limiter.limit("20/minute")
async def suggest_mandate_from_expense(
    http_request: Request,
    request: CheckAutoApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Given expense details, suggest Intent Mandate constraints that would
    auto-approve similar expenses in the future.
    """
    import math

    # Round up max_amount to nearest $25 for headroom
    suggested_max = math.ceil(request.amount / 25) * 25
    if suggested_max < request.amount * 1.2:
        suggested_max = math.ceil(request.amount * 1.2 / 25) * 25

    suggested_monthly = suggested_max * 5  # allow ~5 similar expenses/month

    return {
        "suggested_constraints": {
            "max_amount": suggested_max,
            "monthly_limit": suggested_monthly,
            "category": request.category,
            "merchant": request.vendor,
        },
        "explanation": (
            f"This mandate would auto-approve {request.vendor} expenses "
            f"in {request.category} up to ${suggested_max:.2f} each, "
            f"with a ${suggested_monthly:.2f}/month limit."
        ),
    }


# ── Monthly summary ────────────────────────────────────────────────
class MonthlySummaryRequest(BaseModel):
    year: Optional[int] = Field(default=None, ge=2000, le=2100)
    month: Optional[int] = Field(default=None, ge=1, le=12)


@router.post("/send-monthly-summary")
@limiter.limit("2/hour")
async def send_monthly_summary(
    http_request: Request,
    request: MonthlySummaryRequest = MonthlySummaryRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send the monthly auto-approval summary email to the current user.
    Defaults to the previous month. Admins can trigger for all users
    by adding ?all=true.
    """
    from ..services.monthly_summary_service import (
        gather_user_monthly_stats,
        send_user_monthly_summary,
    )

    now = datetime.utcnow()
    year = request.year
    month = request.month
    if year is None or month is None:
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month - 1

    summary = await send_user_monthly_summary(db, current_user.id, year, month)
    if not summary:
        return {"detail": "No expenses found for the requested month", "sent": False}

    return {
        "sent": summary["auto_approved_count"] > 0,
        "summary": summary,
    }


@router.post("/send-monthly-summary/all")
@limiter.limit("2/hour")
async def send_all_monthly_summaries_endpoint(
    http_request: Request,
    request: MonthlySummaryRequest = MonthlySummaryRequest(),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin-only: Send monthly summary emails to users in the admin's
    organization who had auto-approved expenses in the target month.
    """
    org_id = _resolve_org_id(http_request, db, current_user.id)

    from ..services.monthly_summary_service import send_all_monthly_summaries

    result = await send_all_monthly_summaries(
        request.year, request.month, organization_id=org_id
    )
    return result


# ── AI Pattern Detection / Mandate Suggestions ─────────────────────
@router.get("/mandate-suggestions")
@limiter.limit("10/minute")
async def get_mandate_suggestions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze the user's expense history and suggest Intent Mandates
    for recurring vendor/category patterns that aren't yet covered.
    """
    from ..services.pattern_service import detect_patterns

    org_id = _resolve_org_id(request, db, current_user.id)
    suggestions = detect_patterns(db, current_user.id, org_id)
    return {"suggestions": suggestions, "count": len(suggestions)}


# ── Onboarding: sample mandate templates ────────────────────────────
@router.get("/sample-mandates")
async def get_sample_mandates(
    current_user: User = Depends(get_current_user),
):
    """
    Return sample Intent Mandate templates for onboarding.
    Users can one-click create from these.
    """
    return {
        "templates": [
            {
                "name": "Office Supplies",
                "description": "Auto-approve office supply purchases from common vendors",
                "constraints": {
                    "max_amount": 100.00,
                    "monthly_limit": 300.00,
                    "category": "OFFICE_SUPPLIES",
                },
                "expiration_hours": 720,
            },
            {
                "name": "Software Subscriptions",
                "description": "Auto-approve software and SaaS subscriptions",
                "constraints": {
                    "max_amount": 50.00,
                    "monthly_limit": 200.00,
                    "category": "SOFTWARE",
                },
                "expiration_hours": 720,
            },
            {
                "name": "Team Meals",
                "description": "Auto-approve meals and team lunches",
                "constraints": {
                    "max_amount": 75.00,
                    "monthly_limit": 300.00,
                    "category": "MEALS",
                },
                "expiration_hours": 720,
            },
            {
                "name": "Travel Expenses",
                "description": "Auto-approve travel costs under $200",
                "constraints": {
                    "max_amount": 200.00,
                    "monthly_limit": 1000.00,
                    "category": "TRAVEL",
                },
                "expiration_hours": 720,
            },
        ],
    }


# ── Analytics: trends, cost savings, bottlenecks ────────────────────
@router.get("/analytics/trends")
@limiter.limit("10/minute")
async def get_auto_approval_trends(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Auto-approval trends over the last N days.
    Returns daily counts of auto-approved vs manual expenses.
    """
    from collections import defaultdict

    from sqlalchemy import Date, cast
    from sqlalchemy import func as sqlfunc

    org_id = _resolve_org_id(request, db, current_user.id)
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)

    from ..models import Expense

    expenses = (
        db.query(
            sqlfunc.date(Expense.created_at).label("day"),
            Expense.auto_approved,
            Expense.auto_approved_via,
            sqlfunc.count().label("cnt"),
            sqlfunc.sum(Expense.amount).label("total"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= cutoff,
        )
        .group_by(
            sqlfunc.date(Expense.created_at),
            Expense.auto_approved,
            Expense.auto_approved_via,
        )
        .all()
    )

    # Build daily buckets
    daily = defaultdict(
        lambda: {
            "date": None,
            "auto_mandate": 0,
            "auto_policy": 0,
            "manual": 0,
            "total": 0,
            "auto_amount": 0.0,
            "manual_amount": 0.0,
        }
    )

    for row in expenses:
        day_str = str(row.day)
        daily[day_str]["date"] = day_str
        cnt = row.cnt
        amt = float(row.total or 0)
        daily[day_str]["total"] += cnt
        if row.auto_approved:
            daily[day_str]["auto_amount"] += amt
            if row.auto_approved_via == "intent_mandate":
                daily[day_str]["auto_mandate"] += cnt
            else:
                daily[day_str]["auto_policy"] += cnt
        else:
            daily[day_str]["manual"] += cnt
            daily[day_str]["manual_amount"] += amt

    trend_data = sorted(daily.values(), key=lambda d: d["date"])

    # Compute overall rate
    total_all = sum(d["total"] for d in trend_data)
    total_auto = sum(d["auto_mandate"] + d["auto_policy"] for d in trend_data)
    overall_rate = (total_auto / total_all * 100) if total_all > 0 else 0

    return {
        "days": days,
        "trend": trend_data,
        "overall_auto_approval_rate": round(overall_rate, 1),
        "total_expenses": total_all,
        "total_auto_approved": total_auto,
    }


@router.get("/analytics/cost-savings")
@limiter.limit("10/minute")
async def get_cost_savings(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cost savings from auto-approval: time saved, estimated dollar value.
    """
    from sqlalchemy import func as sqlfunc

    org_id = _resolve_org_id(request, db, current_user.id)
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)

    from ..models import Expense

    auto_count = (
        db.query(sqlfunc.count())
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= cutoff,
            Expense.auto_approved == True,
        )
        .scalar()
        or 0
    )

    auto_amount = (
        db.query(sqlfunc.sum(Expense.amount))
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= cutoff,
            Expense.auto_approved == True,
        )
        .scalar()
        or 0
    )

    total_count = (
        db.query(sqlfunc.count())
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= cutoff,
        )
        .scalar()
        or 0
    )

    minutes_saved = auto_count * 3  # 3 min per auto-approval
    hours_saved = round(minutes_saved / 60, 1)
    # Estimated cost savings at $50/hr manager time
    dollar_savings = round(hours_saved * 50, 2)

    return {
        "days": days,
        "auto_approved_count": auto_count,
        "auto_approved_amount": float(auto_amount),
        "total_count": total_count,
        "minutes_saved": minutes_saved,
        "hours_saved": hours_saved,
        "estimated_dollar_savings": dollar_savings,
        "rate": round(auto_count / total_count * 100, 1) if total_count > 0 else 0,
    }


@router.get("/analytics/bottlenecks")
@limiter.limit("10/minute")
async def get_bottlenecks(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Identify bottlenecks: categories/vendors with lowest auto-approval
    rates or highest rejection rates.
    """
    from collections import defaultdict

    from sqlalchemy import func as sqlfunc

    org_id = _resolve_org_id(request, db, current_user.id)
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(days=days)

    from ..models import Expense, ExpenseStatus

    expenses = (
        db.query(Expense)
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= cutoff,
        )
        .all()
    )

    # Group by category
    cat_stats = defaultdict(
        lambda: {"total": 0, "auto": 0, "rejected": 0, "pending": 0, "amount": 0.0}
    )
    vendor_stats = defaultdict(
        lambda: {"total": 0, "auto": 0, "rejected": 0, "pending": 0, "amount": 0.0}
    )

    for e in expenses:
        cat = e.category.value if hasattr(e.category, "value") else str(e.category)
        vendor = e.vendor or "Unknown"
        status = e.status.value if hasattr(e.status, "value") else str(e.status)
        amt = float(e.amount)

        for stats, key in [(cat_stats, cat), (vendor_stats, vendor)]:
            stats[key]["total"] += 1
            stats[key]["amount"] += amt
            if e.auto_approved:
                stats[key]["auto"] += 1
            if status == "rejected":
                stats[key]["rejected"] += 1
            if status == "pending":
                stats[key]["pending"] += 1

    def build_bottleneck_list(stats_dict):
        items = []
        for name, s in stats_dict.items():
            if s["total"] < 2:
                continue
            auto_rate = (s["auto"] / s["total"] * 100) if s["total"] > 0 else 0
            rejection_rate = (s["rejected"] / s["total"] * 100) if s["total"] > 0 else 0
            items.append(
                {
                    "name": name,
                    "total": s["total"],
                    "auto_approved": s["auto"],
                    "rejected": s["rejected"],
                    "pending": s["pending"],
                    "amount": round(s["amount"], 2),
                    "auto_approval_rate": round(auto_rate, 1),
                    "rejection_rate": round(rejection_rate, 1),
                }
            )
        # Sort by auto_approval_rate ascending (worst first)
        items.sort(key=lambda x: x["auto_approval_rate"])
        return items

    return {
        "days": days,
        "category_bottlenecks": build_bottleneck_list(cat_stats),
        "vendor_bottlenecks": build_bottleneck_list(vendor_stats)[:10],
    }
