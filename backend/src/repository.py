"""
Database repository layer for expense management and AP2 mandates.
Provides abstraction between business logic and database operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import json

from .models import (
    Expense, ExpenseStatus, ExpenseCategory,
    IntentMandate, CartMandate, PaymentMandate,
    User
)


class ExpenseRepository:
    """Repository for Expense operations with multi-tenancy support"""

    def __init__(self, db: Session, organization_id: Optional[str] = None):
        self.db = db
        self.organization_id = organization_id  # Multi-tenancy

    def _apply_tenant_filter(self, query):
        """Apply organization filter to query for tenant isolation"""
        if self.organization_id:
            query = query.filter(Expense.organization_id == self.organization_id)
        return query

    def create(self, expense_data: Dict) -> Expense:
        """Create a new expense"""
        # Ensure organization_id is set for multi-tenancy
        if self.organization_id and 'organization_id' not in expense_data:
            expense_data['organization_id'] = self.organization_id

        expense = Expense(**expense_data)
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def get_by_id(self, expense_id: str) -> Optional[Expense]:
        """Get expense by ID (tenant-aware)"""
        query = self.db.query(Expense).filter(Expense.id == expense_id)
        query = self._apply_tenant_filter(query)
        return query.first()

    def get_by_user(self, user_id: str, status: Optional[ExpenseStatus] = None) -> List[Expense]:
        """Get all expenses for a user, optionally filtered by status (tenant-aware)"""
        query = self.db.query(Expense).filter(Expense.user_id == user_id)
        query = self._apply_tenant_filter(query)
        if status:
            query = query.filter(Expense.status == status)
        return query.order_by(desc(Expense.created_at)).all()

    def get_all(self, limit: int = 100, offset: int = 0, status: Optional[ExpenseStatus] = None) -> List[Expense]:
        """Get all expenses with pagination (tenant-aware)"""
        query = self.db.query(Expense)
        query = self._apply_tenant_filter(query)
        if status:
            query = query.filter(Expense.status == status)
        return query.order_by(desc(Expense.created_at)).limit(limit).offset(offset).all()

    def update(self, expense_id: str, update_data: Dict) -> Optional[Expense]:
        """Update an expense"""
        expense = self.get_by_id(expense_id)
        if not expense:
            return None

        for key, value in update_data.items():
            setattr(expense, key, value)

        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense_id: str) -> bool:
        """Delete an expense"""
        expense = self.get_by_id(expense_id)
        if not expense:
            return False

        self.db.delete(expense)
        self.db.commit()
        return True

    def approve(self, expense_id: str, approver_id: str) -> Optional[Expense]:
        """Approve an expense"""
        return self.update(expense_id, {
            'status': ExpenseStatus.APPROVED,
            'approved_by': approver_id,
            'approved_at': datetime.utcnow()
        })

    def reject(self, expense_id: str, approver_id: str, reason: str) -> Optional[Expense]:
        """Reject an expense"""
        return self.update(expense_id, {
            'status': ExpenseStatus.REJECTED,
            'approved_by': approver_id,
            'approved_at': datetime.utcnow(),
            'rejection_reason': reason
        })

    def get_pending_count(self, user_id: Optional[str] = None) -> int:
        """Get count of pending expenses (tenant-aware)"""
        query = self.db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING)
        query = self._apply_tenant_filter(query)
        if user_id:
            query = query.filter(Expense.user_id == user_id)
        return query.count()

    def get_total_amount(self, user_id: Optional[str] = None, status: Optional[ExpenseStatus] = None) -> float:
        """Get total amount of expenses (tenant-aware)"""
        query = self.db.query(Expense)
        query = self._apply_tenant_filter(query)
        if user_id:
            query = query.filter(Expense.user_id == user_id)
        if status:
            query = query.filter(Expense.status == status)

        expenses = query.all()
        return float(sum(e.amount for e in expenses))

    def get_category_breakdown(self, user_id: Optional[str] = None) -> Dict[str, float]:
        """Get expense breakdown by category"""
        query = self.db.query(Expense)
        if user_id:
            query = query.filter(Expense.user_id == user_id)

        expenses = query.all()
        breakdown = {}
        for expense in expenses:
            category = expense.category.value if isinstance(expense.category, ExpenseCategory) else expense.category
            breakdown[category] = breakdown.get(category, 0.0) + float(expense.amount)

        return breakdown


class IntentMandateRepository:
    """Repository for Intent Mandate operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, mandate_data: Dict) -> IntentMandate:
        """Create a new intent mandate"""
        # Convert constraints dict to JSON string
        if 'constraints' in mandate_data and isinstance(mandate_data['constraints'], dict):
            mandate_data['constraints'] = json.dumps(mandate_data['constraints'])

        mandate = IntentMandate(**mandate_data)
        self.db.add(mandate)
        self.db.commit()
        self.db.refresh(mandate)
        return mandate

    def get_by_id(self, mandate_id: str) -> Optional[IntentMandate]:
        """Get intent mandate by ID"""
        return self.db.query(IntentMandate).filter(IntentMandate.id == mandate_id).first()

    def get_by_user(self, user_id: str, active_only: bool = True) -> List[IntentMandate]:
        """Get all intent mandates for a user"""
        query = self.db.query(IntentMandate).filter(IntentMandate.user_id == user_id)
        if active_only:
            query = query.filter(
                and_(
                    IntentMandate.status == "active",
                    IntentMandate.expiration > datetime.utcnow()
                )
            )
        return query.order_by(desc(IntentMandate.created_at)).all()

    def update_status(self, mandate_id: str, status: str) -> Optional[IntentMandate]:
        """Update mandate status"""
        mandate = self.get_by_id(mandate_id)
        if not mandate:
            return None

        mandate.status = status
        self.db.commit()
        self.db.refresh(mandate)
        return mandate

    def expire_old_mandates(self) -> int:
        """Expire all mandates past their expiration date"""
        count = self.db.query(IntentMandate).filter(
            and_(
                IntentMandate.status == "active",
                IntentMandate.expiration <= datetime.utcnow()
            )
        ).update({"status": "expired"})
        self.db.commit()
        return count


class CartMandateRepository:
    """Repository for Cart Mandate operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, mandate_data: Dict) -> CartMandate:
        """Create a new cart mandate"""
        # Convert items list to JSON string
        if 'items' in mandate_data and isinstance(mandate_data['items'], list):
            mandate_data['items'] = json.dumps(mandate_data['items'])

        mandate = CartMandate(**mandate_data)
        self.db.add(mandate)
        self.db.commit()
        self.db.refresh(mandate)
        return mandate

    def get_by_id(self, mandate_id: str) -> Optional[CartMandate]:
        """Get cart mandate by ID"""
        return self.db.query(CartMandate).filter(CartMandate.id == mandate_id).first()

    def get_by_intent_mandate(self, intent_mandate_id: str) -> List[CartMandate]:
        """Get all cart mandates for an intent mandate"""
        return self.db.query(CartMandate).filter(
            CartMandate.intent_mandate_id == intent_mandate_id
        ).order_by(desc(CartMandate.created_at)).all()

    def update_status(self, mandate_id: str, status: str) -> Optional[CartMandate]:
        """Update mandate status"""
        mandate = self.get_by_id(mandate_id)
        if not mandate:
            return None

        mandate.status = status
        self.db.commit()
        self.db.refresh(mandate)
        return mandate


class PaymentMandateRepository:
    """Repository for Payment Mandate operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, mandate_data: Dict) -> PaymentMandate:
        """Create a new payment mandate"""
        # Convert audit_trail dict to JSON string
        if 'audit_trail' in mandate_data and isinstance(mandate_data['audit_trail'], dict):
            mandate_data['audit_trail'] = json.dumps(mandate_data['audit_trail'])

        # Convert payment_processor_response dict to JSON string if present
        if 'payment_processor_response' in mandate_data and isinstance(mandate_data['payment_processor_response'], dict):
            mandate_data['payment_processor_response'] = json.dumps(mandate_data['payment_processor_response'])

        mandate = PaymentMandate(**mandate_data)
        self.db.add(mandate)
        self.db.commit()
        self.db.refresh(mandate)
        return mandate

    def get_by_id(self, mandate_id: str) -> Optional[PaymentMandate]:
        """Get payment mandate by ID"""
        return self.db.query(PaymentMandate).filter(PaymentMandate.id == mandate_id).first()

    def get_by_cart_mandate(self, cart_mandate_id: str) -> List[PaymentMandate]:
        """Get all payment mandates for a cart mandate"""
        return self.db.query(PaymentMandate).filter(
            PaymentMandate.cart_mandate_id == cart_mandate_id
        ).order_by(desc(PaymentMandate.created_at)).all()

    def get_by_status(self, status: str) -> List[PaymentMandate]:
        """Get all payment mandates by status"""
        return self.db.query(PaymentMandate).filter(
            PaymentMandate.status == status
        ).order_by(desc(PaymentMandate.created_at)).all()

    def update_status(self, mandate_id: str, status: str, processor_response: Optional[Dict] = None) -> Optional[PaymentMandate]:
        """Update mandate status"""
        mandate = self.get_by_id(mandate_id)
        if not mandate:
            return None

        mandate.status = status
        if processor_response:
            mandate.payment_processor_response = json.dumps(processor_response)

        self.db.commit()
        self.db.refresh(mandate)
        return mandate

    def get_audit_trail(self, mandate_id: str) -> Optional[Dict]:
        """Get complete audit trail for a payment mandate"""
        payment_mandate = self.get_by_id(mandate_id)
        if not payment_mandate:
            return None

        cart_mandate = self.db.query(CartMandate).filter(
            CartMandate.id == payment_mandate.cart_mandate_id
        ).first()

        intent_mandate = None
        if cart_mandate:
            intent_mandate = self.db.query(IntentMandate).filter(
                IntentMandate.id == cart_mandate.intent_mandate_id
            ).first()

        return {
            'transaction_id': mandate_id,
            'payment_mandate': {
                'id': payment_mandate.id,
                'status': payment_mandate.status,
                'payment_method': payment_mandate.payment_method,
                'timestamp': payment_mandate.timestamp.isoformat(),
                'audit_trail': json.loads(payment_mandate.audit_trail) if payment_mandate.audit_trail else None,
            },
            'cart_mandate': {
                'id': cart_mandate.id,
                'items': json.loads(cart_mandate.items) if cart_mandate.items else [],
                'total': float(cart_mandate.total),
                'merchant': cart_mandate.merchant,
                'timestamp': cart_mandate.timestamp.isoformat(),
            } if cart_mandate else None,
            'intent_mandate': {
                'id': intent_mandate.id,
                'user_id': intent_mandate.user_id,
                'constraints': json.loads(intent_mandate.constraints) if intent_mandate.constraints else {},
                'timestamp': intent_mandate.timestamp.isoformat(),
                'expiration': intent_mandate.expiration.isoformat(),
                'signature': intent_mandate.signature,
            } if intent_mandate else None,
            'audit_trail_complete': all([payment_mandate, cart_mandate, intent_mandate])
        }


class AP2Repository:
    """Unified repository for all AP2 mandate operations"""

    def __init__(self, db: Session):
        self.db = db
        self.intent = IntentMandateRepository(db)
        self.cart = CartMandateRepository(db)
        self.payment = PaymentMandateRepository(db)
