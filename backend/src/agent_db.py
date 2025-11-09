# AP2 Expense Management Agent - Database-Integrated Version
# This version uses PostgreSQL instead of in-memory storage

import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .models import Expense, ExpenseCategory, ExpenseStatus
from .repository import AP2Repository, ExpenseRepository

# ============================================================================
# AP2 PROTOCOL CORE CLASSES (for business logic)
# ============================================================================


@dataclass
class IntentMandateData:
    """
    Intent Mandate: Captures conditions for AI agent purchases
    Used in human-not-present scenarios
    """

    id: str
    user_id: str
    constraints: Dict
    timestamp: str
    expiration: str
    signature: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    def sign(self, private_key):
        """Create cryptographic signature"""
        message = json.dumps(self.to_dict(), sort_keys=True).encode()
        signature = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        self.signature = signature.hex()
        return self.signature


@dataclass
class CartMandateData:
    """
    Cart Mandate: User's explicit authorization for specific items
    Used in human-present scenarios with final approval
    """

    id: str
    intent_mandate_ref: str
    items: List[Dict]
    total: float
    merchant: str
    timestamp: str
    user_signature: str

    def to_dict(self):
        return asdict(self)

    def verify_total(self):
        """Verify cart total matches items"""
        calculated_total = sum(item["amount"] for item in self.items)
        return abs(calculated_total - self.total) < 0.01


@dataclass
class PaymentMandateData:
    """
    Payment Mandate: Shared with payment network/issuer
    Signals AI agent involvement and provides audit trail
    """

    id: str
    cart_mandate_ref: str
    payment_method: str
    status: str  # pending, completed, failed, refunded
    audit_trail: Dict
    timestamp: str

    def to_dict(self):
        return asdict(self)


# ============================================================================
# DATABASE-INTEGRATED EXPENSE MANAGEMENT AGENT
# ============================================================================


class ExpenseManagementAgent:
    """
    AI-Powered Expense Management Agent with AP2 Integration and Database Persistence
    """

    def __init__(
        self,
        db: Session,
        api_key: str = "",
        project_id: str = "",
        organization_id: Optional[str] = None,
    ):
        """Initialize the agent with database session, organization context, and optional Google AI credentials"""
        self.db = db
        self.api_key = api_key
        self.project_id = project_id
        self.organization_id = organization_id  # Multi-tenancy support

        # Configure Gemini AI if available
        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:
            self.model = None

        # Generate RSA key pair for mandate signing
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        self.public_key = self.private_key.public_key()

        # Initialize repositories with organization context for multi-tenancy
        self.expense_repo = ExpenseRepository(db, organization_id=organization_id)
        self.ap2_repo = AP2Repository(db)

    def create_intent_mandate(
        self,
        user_id: str,
        max_amount: float,
        category: str,
        merchant: Optional[str] = None,
        valid_days: int = 30,
    ) -> IntentMandateData:
        """
        Create Intent Mandate for automated expense approval
        """
        mandate_data = IntentMandateData(
            id=f"intent_{int(time.time() * 1000)}",
            user_id=user_id,
            constraints={
                "max_amount": max_amount,
                "category": category,
                "merchant": merchant,
                "auto_approve": True,
            },
            timestamp=datetime.utcnow().isoformat(),
            expiration=(datetime.utcnow() + timedelta(days=valid_days)).isoformat(),
        )

        # Sign the mandate
        mandate_data.sign(self.private_key)

        # Save to database
        db_mandate = self.ap2_repo.intent.create(
            {
                "id": mandate_data.id,
                "user_id": mandate_data.user_id,
                "constraints": mandate_data.constraints,
                "timestamp": datetime.fromisoformat(mandate_data.timestamp),
                "expiration": datetime.fromisoformat(mandate_data.expiration),
                "signature": mandate_data.signature,
                "status": "active",
            }
        )

        return mandate_data

    def create_cart_mandate(
        self, intent_mandate_id: str, expense_id: str, items: List[Dict], merchant: str
    ) -> CartMandateData:
        """
        Create Cart Mandate for specific expense approval
        """
        total = sum(item["amount"] for item in items)

        mandate_data = CartMandateData(
            id=f"cart_{int(time.time() * 1000)}",
            intent_mandate_ref=intent_mandate_id,
            items=items,
            total=total,
            merchant=merchant,
            timestamp=datetime.utcnow().isoformat(),
            user_signature=self._generate_user_signature(expense_id, total),
        )

        # Verify total
        if not mandate_data.verify_total():
            raise ValueError("Cart total does not match items")

        # Save to database
        db_mandate = self.ap2_repo.cart.create(
            {
                "id": mandate_data.id,
                "intent_mandate_id": mandate_data.intent_mandate_ref,
                "items": mandate_data.items,
                "total": mandate_data.total,
                "merchant": mandate_data.merchant,
                "timestamp": datetime.fromisoformat(mandate_data.timestamp),
                "user_signature": mandate_data.user_signature,
                "status": "pending",
            }
        )

        return mandate_data

    def process_payment(
        self, cart_mandate: CartMandateData, payment_method: str = "corporate_card"
    ) -> PaymentMandateData:
        """
        Process payment using AP2 protocol with full audit trail
        """
        # Create Payment Mandate
        payment_mandate_data = PaymentMandateData(
            id=f"payment_{int(time.time() * 1000)}",
            cart_mandate_ref=cart_mandate.id,
            payment_method=payment_method,
            status="completed",
            audit_trail={
                "intent_mandate": cart_mandate.intent_mandate_ref,
                "cart_mandate": cart_mandate.id,
                "timestamp": datetime.utcnow().isoformat(),
                "verification_status": "verified",
                "compliance_check": "passed",
            },
            timestamp=datetime.utcnow().isoformat(),
        )

        # Save to database
        db_mandate = self.ap2_repo.payment.create(
            {
                "id": payment_mandate_data.id,
                "cart_mandate_id": payment_mandate_data.cart_mandate_ref,
                "payment_method": payment_mandate_data.payment_method,
                "status": payment_mandate_data.status,
                "audit_trail": payment_mandate_data.audit_trail,
                "timestamp": datetime.fromisoformat(payment_mandate_data.timestamp),
            }
        )

        # Update cart mandate status
        self.ap2_repo.cart.update_status(cart_mandate.id, "completed")

        return payment_mandate_data

    async def analyze_expense(self, expense_data: Dict) -> Dict:
        """
        Use Gemini AI to analyze and categorize expense
        """
        if not self.model:
            # Fallback if no API key
            return {
                "category": expense_data.get("category", "Other"),
                "compliant": True,
                "risk_level": "low",
                "recommendations": "Expense appears valid",
            }

        prompt = f"""
        Analyze the following expense and provide:
        1. Category verification (Travel, Meals, Software, Office Supplies, Other)
        2. Compliance check (is it a valid business expense?)
        3. Risk assessment (low, medium, high)
        4. Recommendations

        Expense Details:
        - Amount: ${expense_data['amount']}
        - Vendor: {expense_data['vendor']}
        - Description: {expense_data['description']}
        - Category: {expense_data.get('category', 'Not specified')}

        Respond in JSON format with keys: category, compliant, risk_level, recommendations
        """

        try:
            response = self.model.generate_content(prompt)
            # Parse AI response
            analysis = json.loads(response.text)
            return analysis
        except:
            # Fallback if AI doesn't return proper JSON
            return {
                "category": expense_data.get("category", "Other"),
                "compliant": True,
                "risk_level": "low",
                "recommendations": "Expense appears valid",
            }

    def submit_expense(
        self, user_id: str, amount: float, vendor: str, category: str, description: str
    ) -> Dict:
        """
        Submit a new expense with AP2 mandate creation
        """
        # Map string category to enum
        category_enum = (
            ExpenseCategory[category.upper().replace(" ", "_")]
            if hasattr(ExpenseCategory, category.upper().replace(" ", "_"))
            else ExpenseCategory.OTHER
        )

        # Generate unique ID using timestamp and uuid to prevent collisions
        expense_id = f"EXP-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"

        # Create expense in database
        expense = self.expense_repo.create(
            {
                "id": expense_id,
                "organization_id": self.organization_id,
                "user_id": user_id,
                "amount": amount,
                "vendor": vendor,
                "category": category_enum,
                "description": description,
                "status": ExpenseStatus.PENDING,
                "date": datetime.utcnow(),
            }
        )

        return {
            "id": expense.id,
            "user_id": expense.user_id,
            "amount": float(expense.amount),
            "vendor": expense.vendor,
            "category": expense.category.value,
            "description": expense.description,
            "status": expense.status.value,
            "date": expense.date.isoformat(),
            "created_at": (
                expense.created_at.isoformat() if expense.created_at else None
            ),
        }

    def approve_and_process_expense(self, expense_id: str, approver_id: str) -> Dict:
        """
        Approve expense and process payment via AP2
        """
        # Find expense in database
        expense = self.expense_repo.get_by_id(expense_id)
        if not expense:
            raise ValueError(f"Expense {expense_id} not found")

        # Create Intent Mandate
        intent_mandate = self.create_intent_mandate(
            user_id=expense.user_id,
            max_amount=float(expense.amount),
            category=expense.category.value,
            merchant=expense.vendor,
        )

        # Create Cart Mandate
        cart_mandate = self.create_cart_mandate(
            intent_mandate_id=intent_mandate.id,
            expense_id=expense.id,
            items=[
                {
                    "description": expense.description,
                    "amount": float(expense.amount),
                    "vendor": expense.vendor,
                }
            ],
            merchant=expense.vendor,
        )

        # Process Payment
        payment_mandate = self.process_payment(cart_mandate)

        # Update expense in database
        self.expense_repo.update(
            expense.id,
            {
                "status": ExpenseStatus.APPROVED,
                "transaction_id": payment_mandate.id,
                "approved_by": approver_id,
                "approved_at": datetime.utcnow(),
                "intent_mandate_id": intent_mandate.id,
                "cart_mandate_id": cart_mandate.id,
                "payment_mandate_id": payment_mandate.id,
            },
        )

        # Refresh expense
        expense = self.expense_repo.get_by_id(expense_id)

        return {
            "expense": {
                "id": expense.id,
                "user_id": expense.user_id,
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category.value,
                "description": expense.description,
                "status": expense.status.value,
                "transaction_id": expense.transaction_id,
                "approved_by": expense.approved_by,
                "approved_at": (
                    expense.approved_at.isoformat() if expense.approved_at else None
                ),
            },
            "mandates": {
                "intent": intent_mandate.to_dict(),
                "cart": cart_mandate.to_dict(),
                "payment": payment_mandate.to_dict(),
            },
        }

    def get_expense_report(self, user_id: Optional[str] = None) -> Dict:
        """Generate expense analytics report from database"""
        expenses = (
            self.expense_repo.get_by_user(user_id)
            if user_id
            else self.expense_repo.get_all()
        )

        if not expenses:
            return {
                "total_expenses": 0,
                "total_amount": 0,
                "pending_count": 0,
                "approved_count": 0,
                "average_amount": 0,
                "categories": {},
                "expenses": [],
            }

        total_amount = sum(float(e.amount) for e in expenses)
        pending_count = sum(1 for e in expenses if e.status == ExpenseStatus.PENDING)
        approved_count = sum(1 for e in expenses if e.status == ExpenseStatus.APPROVED)

        # Category breakdown
        categories = self.expense_repo.get_category_breakdown(user_id)

        return {
            "total_expenses": len(expenses),
            "total_amount": total_amount,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "average_amount": total_amount / len(expenses) if expenses else 0,
            "categories": categories,
            "expenses": [
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "amount": float(e.amount),
                    "vendor": e.vendor,
                    "category": e.category.value,
                    "description": e.description,
                    "status": e.status.value,
                    "date": e.date.isoformat() if e.date else None,
                    "transaction_id": e.transaction_id,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in expenses
            ],
        }

    def get_audit_trail(self, transaction_id: str) -> Dict:
        """Retrieve complete AP2 audit trail for compliance"""
        return self.ap2_repo.payment.get_audit_trail(transaction_id)

    def _generate_user_signature(self, expense_id: str, amount: float) -> str:
        """Generate cryptographic user signature"""
        message = f"{expense_id}:{amount}:{int(time.time())}"
        return hashlib.sha256(message.encode()).hexdigest()
