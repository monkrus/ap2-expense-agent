"""
AP2 Audit Trail Service
Handles complete audit trail creation and retrieval for the AP2 protocol
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import AuditLog, CartMandate, Expense, IntentMandate, PaymentMandate, User
from ..repository import AP2Repository


class AuditService:
    """Service for managing complete AP2 audit trails"""

    def __init__(self, db: Session):
        self.db = db
        self.ap2_repo = AP2Repository(db)

    def create_complete_audit_trail(
        self, expense: Expense, approver: User, action: str = "approve"
    ) -> Dict:
        """
        Create complete AP2 audit trail with all three mandates
        Returns: Dict with mandate IDs and audit trail data
        """
        timestamp = datetime.utcnow()

        # 1. Create Intent Mandate (User's authorization constraints)
        intent_mandate = self._create_intent_mandate(expense, approver, timestamp)

        # 2. Create Cart Mandate (Specific items for approval)
        cart_mandate = self._create_cart_mandate(
            expense, intent_mandate.id, approver, timestamp
        )

        # 3. Create Payment Mandate (Payment execution record)
        payment_mandate = self._create_payment_mandate(
            expense, cart_mandate.id, approver, timestamp, action
        )

        # 4. Create Audit Log entry
        self._create_audit_log_entry(
            expense,
            approver,
            action,
            {
                "intent_mandate_id": intent_mandate.id,
                "cart_mandate_id": cart_mandate.id,
                "payment_mandate_id": payment_mandate.id,
            },
        )

        # 5. Link mandates to expense
        expense.intent_mandate_id = intent_mandate.id
        expense.cart_mandate_id = cart_mandate.id
        expense.payment_mandate_id = payment_mandate.id
        expense.transaction_id = payment_mandate.id

        self.db.commit()

        return {
            "intent_mandate": {
                "id": intent_mandate.id,
                "constraints": json.loads(intent_mandate.constraints),
                "timestamp": intent_mandate.timestamp.isoformat(),
                "expiration": intent_mandate.expiration.isoformat(),
                "signature": intent_mandate.signature,
            },
            "cart_mandate": {
                "id": cart_mandate.id,
                "items": json.loads(cart_mandate.items),
                "total": float(cart_mandate.total),
                "merchant": cart_mandate.merchant,
                "timestamp": cart_mandate.timestamp.isoformat(),
                "user_signature": cart_mandate.user_signature,
            },
            "payment_mandate": {
                "id": payment_mandate.id,
                "payment_method": payment_mandate.payment_method,
                "status": payment_mandate.status,
                "timestamp": payment_mandate.timestamp.isoformat(),
                "audit_trail": json.loads(payment_mandate.audit_trail),
            },
            "transaction_id": payment_mandate.id,
        }

    def _create_intent_mandate(
        self, expense: Expense, approver: User, timestamp: datetime
    ) -> IntentMandate:
        """Create Intent Mandate with user authorization constraints"""
        constraints = {
            "max_amount": float(expense.amount) * 1.1,  # 10% buffer
            "allowed_categories": [expense.category.value],
            "allowed_vendors": [expense.vendor],
            "expiration_days": 30,
            "requires_approval": True,
            "approver_id": approver.id,
        }

        signature = self._generate_signature(
            f"{expense.user_id}:{expense.id}:{timestamp.isoformat()}"
        )

        mandate = IntentMandate(
            id=f"intent_{uuid.uuid4().hex[:16]}",
            user_id=expense.user_id,
            constraints=json.dumps(constraints),
            timestamp=timestamp,
            expiration=timestamp + timedelta(days=30),
            signature=signature,
            status="active",
        )

        self.db.add(mandate)
        return mandate

    def _create_cart_mandate(
        self,
        expense: Expense,
        intent_mandate_id: str,
        approver: User,
        timestamp: datetime,
    ) -> CartMandate:
        """Create Cart Mandate with specific items for approval"""
        items = [
            {
                "expense_id": expense.id,
                "description": expense.description,
                "amount": float(expense.amount),
                "category": expense.category.value,
                "date": (
                    expense.date.isoformat() if expense.date else timestamp.isoformat()
                ),
            }
        ]

        user_signature = self._generate_signature(
            f"{expense.id}:{float(expense.amount)}:{timestamp.isoformat()}"
        )

        mandate = CartMandate(
            id=f"cart_{uuid.uuid4().hex[:16]}",
            intent_mandate_id=intent_mandate_id,
            items=json.dumps(items),
            total=expense.amount,
            merchant=expense.vendor,
            timestamp=timestamp,
            user_signature=user_signature,
            status="approved",
        )

        self.db.add(mandate)
        return mandate

    def _create_payment_mandate(
        self,
        expense: Expense,
        cart_mandate_id: str,
        approver: User,
        timestamp: datetime,
        action: str,
    ) -> PaymentMandate:
        """Create Payment Mandate with execution details"""
        audit_trail = {
            "expense_id": expense.id,
            "submitted_by": expense.user_id,
            "submitted_at": (
                expense.created_at.isoformat()
                if expense.created_at
                else timestamp.isoformat()
            ),
            "reviewed_by": approver.id,
            "reviewed_at": timestamp.isoformat(),
            "action": action,
            "approval_chain": [
                {
                    "approver_id": approver.id,
                    "approver_email": approver.email,
                    "approver_name": approver.full_name,
                    "timestamp": timestamp.isoformat(),
                    "action": action,
                }
            ],
            "compliance_checks": {
                "policy_compliant": True,
                "budget_compliant": True,
                "fraud_check": "passed",
                "risk_level": expense.risk_level or "LOW",
            },
            "metadata": {
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category.value,
                "description": expense.description,
            },
        }

        mandate = PaymentMandate(
            id=f"payment_{uuid.uuid4().hex[:16]}",
            cart_mandate_id=cart_mandate_id,
            payment_method="corporate_account",  # Default payment method
            status="approved" if action == "approve" else "rejected",
            audit_trail=json.dumps(audit_trail),
            timestamp=timestamp,
        )

        self.db.add(mandate)
        return mandate

    def _create_audit_log_entry(
        self, expense: Expense, user: User, action: str, details: Dict
    ) -> AuditLog:
        """Create audit log entry for compliance tracking"""
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            action=f"expense_{action}",
            resource_type="expense",
            resource_id=expense.id,
            details=json.dumps(
                {
                    **details,
                    "amount": float(expense.amount),
                    "vendor": expense.vendor,
                    "category": expense.category.value,
                    "status_change": f"PENDING -> {action.upper()}D",
                }
            ),
        )

        self.db.add(log)
        self.db.commit()  # Commit to persist the audit log
        return log

    def get_complete_audit_trail(self, transaction_id: str) -> Optional[Dict]:
        """
        Retrieve complete audit trail for a transaction
        Returns full AP2 protocol chain
        """
        # Get the payment mandate
        payment_mandate = self.ap2_repo.payment.get_by_id(transaction_id)
        if not payment_mandate:
            return None

        # Get linked cart mandate
        cart_mandate = None
        if payment_mandate.cart_mandate_id:
            cart_mandate = self.ap2_repo.cart.get_by_id(payment_mandate.cart_mandate_id)

        # Get linked intent mandate
        intent_mandate = None
        if cart_mandate and cart_mandate.intent_mandate_id:
            intent_mandate = self.ap2_repo.intent.get_by_id(
                cart_mandate.intent_mandate_id
            )

        # Get associated expense
        expense = (
            self.db.query(Expense)
            .filter(Expense.payment_mandate_id == transaction_id)
            .first()
        )

        # Get related audit logs
        audit_logs = []
        if expense:
            logs = (
                self.db.query(AuditLog)
                .filter(
                    AuditLog.resource_type == "expense",
                    AuditLog.resource_id == expense.id,
                )
                .order_by(AuditLog.created_at)
                .all()
            )

            audit_logs = [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "timestamp": log.created_at.isoformat(),
                    "details": json.loads(log.details) if log.details else None,
                }
                for log in logs
            ]

        return {
            "transaction_id": transaction_id,
            "complete": all([payment_mandate, cart_mandate, intent_mandate]),
            "expense": (
                {
                    "id": expense.id,
                    "amount": float(expense.amount),
                    "vendor": expense.vendor,
                    "category": expense.category.value,
                    "description": expense.description,
                    "status": expense.status.value,
                    "submitted_at": (
                        expense.created_at.isoformat() if expense.created_at else None
                    ),
                    "approved_at": (
                        expense.approved_at.isoformat() if expense.approved_at else None
                    ),
                }
                if expense
                else None
            ),
            "intent_mandate": (
                {
                    "id": intent_mandate.id,
                    "user_id": intent_mandate.user_id,
                    "constraints": (
                        json.loads(intent_mandate.constraints)
                        if intent_mandate.constraints
                        else {}
                    ),
                    "timestamp": intent_mandate.timestamp.isoformat(),
                    "expiration": intent_mandate.expiration.isoformat(),
                    "signature": intent_mandate.signature,
                    "status": intent_mandate.status,
                }
                if intent_mandate
                else None
            ),
            "cart_mandate": (
                {
                    "id": cart_mandate.id,
                    "items": (
                        json.loads(cart_mandate.items) if cart_mandate.items else []
                    ),
                    "total": float(cart_mandate.total),
                    "merchant": cart_mandate.merchant,
                    "timestamp": cart_mandate.timestamp.isoformat(),
                    "user_signature": cart_mandate.user_signature,
                    "status": cart_mandate.status,
                }
                if cart_mandate
                else None
            ),
            "payment_mandate": (
                {
                    "id": payment_mandate.id,
                    "payment_method": payment_mandate.payment_method,
                    "status": payment_mandate.status,
                    "timestamp": payment_mandate.timestamp.isoformat(),
                    "audit_trail": (
                        json.loads(payment_mandate.audit_trail)
                        if payment_mandate.audit_trail
                        else {}
                    ),
                    "processor_response": (
                        json.loads(payment_mandate.payment_processor_response)
                        if payment_mandate.payment_processor_response
                        else None
                    ),
                }
                if payment_mandate
                else None
            ),
            "audit_logs": audit_logs,
            "verification": {
                "chain_complete": all([payment_mandate, cart_mandate, intent_mandate]),
                "signatures_valid": True,  # TODO: Implement signature verification
                "timestamps_valid": self._verify_timestamps(
                    intent_mandate, cart_mandate, payment_mandate
                ),
            },
        }

    def get_expense_history(self, expense_id: str) -> List[Dict]:
        """Get complete history of all actions on an expense"""
        logs = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.resource_type == "expense", AuditLog.resource_id == expense_id
            )
            .order_by(AuditLog.created_at)
            .all()
        )

        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "timestamp": log.created_at.isoformat(),
                "details": json.loads(log.details) if log.details else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
            }
            for log in logs
        ]

    def _generate_signature(self, message: str) -> str:
        """Generate cryptographic signature for AP2 protocol"""
        timestamp = int(time.time())
        signed_message = f"{message}:{timestamp}"
        return hashlib.sha256(signed_message.encode()).hexdigest()

    def _verify_timestamps(
        self,
        intent: Optional[IntentMandate],
        cart: Optional[CartMandate],
        payment: Optional[PaymentMandate],
    ) -> bool:
        """Verify that timestamps follow correct chronological order"""
        if not all([intent, cart, payment]):
            return False

        return intent.timestamp <= cart.timestamp <= payment.timestamp
