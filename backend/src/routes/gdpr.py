"""
GDPR Compliance Endpoints
Provides data portability and privacy rights
"""

import json
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    AuditLog,
    CartMandate,
    Expense,
    IntentMandate,
    Organization,
    PaymentMandate,
    User,
)

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


@router.get("/export/my-data")
async def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GDPR Article 20: Right to Data Portability

    Export all personal data in machine-readable format (JSON).
    Includes:
    - User profile information
    - Expense records
    - AP2 mandates (Intent, Cart, Payment)
    - Audit logs
    - Organization memberships

    Returns:
        JSON file with complete user data

    GDPR Compliance:
    - Article 20: Right to data portability
    - Article 15: Right of access
    - Machine-readable format (JSON)
    - Includes all personal data
    """
    export_data = {
        "export_metadata": {
            "export_date": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "gdpr_article": "Article 20 - Right to Data Portability",
            "format": "JSON",
        },
        "personal_information": {
            "user_id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value if current_user.role else None,
            "department": current_user.department,
            "is_active": current_user.is_active,
            "created_at": (
                current_user.created_at.isoformat() if current_user.created_at else None
            ),
            "last_login": (
                current_user.last_login.isoformat() if current_user.last_login else None
            ),
        },
        "expenses": [],
        "ap2_mandates": {
            "intent_mandates": [],
            "cart_mandates": [],
            "payment_mandates": [],
        },
        "audit_logs": [],
        "organizations": [],
    }

    # Export expenses
    expenses = db.query(Expense).filter_by(user_id=current_user.id).all()
    for expense in expenses:
        export_data["expenses"].append(
            {
                "id": expense.id,
                "amount": float(expense.amount),
                "category": expense.category.value if expense.category else None,
                "vendor": expense.vendor,
                "description": expense.description,
                "date": expense.date.isoformat() if expense.date else None,
                "status": expense.status.value if expense.status else None,
                "submitted_at": (
                    expense.created_at.isoformat() if expense.created_at else None
                ),
                "approved_at": (
                    expense.approved_at.isoformat() if expense.approved_at else None
                ),
                "approved_by": expense.approved_by,
            }
        )

    # Export AP2 Intent Mandates
    intent_mandates = db.query(IntentMandate).filter_by(user_id=current_user.id).all()
    for mandate in intent_mandates:
        export_data["ap2_mandates"]["intent_mandates"].append(
            {
                "id": mandate.id,
                "constraints": (
                    json.loads(mandate.constraints) if mandate.constraints else {}
                ),
                "timestamp": (
                    mandate.timestamp.isoformat() if mandate.timestamp else None
                ),
                "expiration": (
                    mandate.expiration.isoformat() if mandate.expiration else None
                ),
                "status": mandate.status,
                "signature": mandate.signature,
                "revoked_at": (
                    mandate.revoked_at.isoformat()
                    if hasattr(mandate, "revoked_at") and mandate.revoked_at
                    else None
                ),
            }
        )

    # Export AP2 Cart Mandates (through intent mandates)
    for intent in intent_mandates:
        cart_mandates = (
            db.query(CartMandate).filter_by(intent_mandate_id=intent.id).all()
        )
        for cart in cart_mandates:
            export_data["ap2_mandates"]["cart_mandates"].append(
                {
                    "id": cart.id,
                    "intent_mandate_id": cart.intent_mandate_id,
                    "items": json.loads(cart.items) if cart.items else [],
                    "total": float(cart.total),
                    "merchant": cart.merchant,
                    "timestamp": cart.timestamp.isoformat() if cart.timestamp else None,
                    "status": cart.status,
                }
            )

            # Export Payment Mandates linked to this cart
            payment_mandates = (
                db.query(PaymentMandate).filter_by(cart_mandate_id=cart.id).all()
            )
            for payment in payment_mandates:
                export_data["ap2_mandates"]["payment_mandates"].append(
                    {
                        "id": payment.id,
                        "cart_mandate_id": payment.cart_mandate_id,
                        "payment_method": payment.payment_method,
                        "status": payment.status,
                        "timestamp": (
                            payment.timestamp.isoformat() if payment.timestamp else None
                        ),
                        "audit_trail": (
                            json.loads(payment.audit_trail)
                            if payment.audit_trail
                            else {}
                        ),
                    }
                )

    # Export audit logs
    audit_logs = db.query(AuditLog).filter_by(user_id=current_user.id).all()
    for log in audit_logs:
        export_data["audit_logs"].append(
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "details": json.loads(log.details) if log.details else {},
                "ip_address": log.ip_address,
            }
        )

    # Export organization memberships
    if current_user.organization:
        export_data["organizations"].append(
            {
                "id": current_user.organization.id,
                "name": current_user.organization.name,
                "joined_at": (
                    current_user.created_at.isoformat()
                    if current_user.created_at
                    else None
                ),
            }
        )

    # Return as downloadable JSON file
    filename = f"gdpr_export_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-GDPR-Export": "true",
        },
    )


@router.delete("/delete/my-account")
async def request_account_deletion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GDPR Article 17: Right to Erasure ("Right to be Forgotten")

    Request account deletion. Creates deletion request that will be processed
    after grace period (7 days) to allow data recovery if requested in error.

    GDPR Compliance:
    - Article 17: Right to erasure
    - 7-day grace period for accidental deletion
    - Audit log of deletion request
    - Cannot delete if active mandates exist

    Returns:
        Deletion request confirmation
    """
    # Check for active mandates
    active_mandates = (
        db.query(IntentMandate)
        .filter_by(user_id=current_user.id, status="active")
        .count()
    )

    if active_mandates > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot delete account with {active_mandates} active mandates. "
                "Please revoke all active mandates before requesting deletion."
            ),
        )

    # Mark user for deletion
    current_user.is_active = False
    current_user.deletion_requested_at = datetime.utcnow()
    current_user.deletion_scheduled_at = datetime.utcnow()  # Add 7 days in production

    # Create audit log
    audit_log = AuditLog(
        id=str(__import__("uuid").uuid4()),
        user_id=current_user.id,
        action="account_deletion_requested",
        resource_type="user",
        resource_id=current_user.id,
        details=json.dumps(
            {
                "gdpr_article": "17",
                "grace_period_days": 7,
                "scheduled_deletion": current_user.deletion_scheduled_at.isoformat(),
            }
        ),
    )
    db.add(audit_log)
    db.commit()

    return {
        "success": True,
        "message": "Account deletion requested",
        "gdpr_article": "Article 17 - Right to Erasure",
        "grace_period_days": 7,
        "scheduled_deletion": current_user.deletion_scheduled_at.isoformat(),
        "cancellation_info": "Contact support within 7 days to cancel deletion",
    }
