"""
AP2 Protocol Payment Service
Implements Google's Agent Payments Protocol for cryptographic payment verification
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session

from ..models import CartMandate, IntentMandate, PaymentMandate, User
from ..security import get_kms_service
from .stripe_processor import StripePaymentProcessor


class AP2PaymentService:
    """
    AP2 Protocol payment flow implementation

    Flow:
    1. Intent Mandate: User authorizes agent to make purchases within constraints
    2. Cart Mandate: Agent builds shopping cart and gets user approval
    3. Payment Mandate: Execute payment with cryptographic audit trail
    """

    def __init__(self, db: Session):
        self.db = db
        self.stripe = StripePaymentProcessor(db)
        self.kms = get_kms_service()  # Cloud KMS for cryptographic signing

    async def create_intent_mandate(
        self, user_id: str, constraints: Dict, expiration_hours: int = 24
    ) -> IntentMandate:
        """
        Create Intent Mandate - User's authorization to make purchases

        Args:
            user_id: User ID
            constraints: Purchase constraints (e.g., max_amount, categories, merchants)
            expiration_hours: How long the mandate is valid

        Returns:
            IntentMandate

        Example constraints:
        {
            "max_amount": 1000.00,
            "categories": ["office_supplies", "software"],
            "merchants": ["Amazon", "Microsoft"],
            "approval_required": True
        }
        """
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        now = datetime.utcnow()
        expiration = now + timedelta(hours=expiration_hours)

        intent_mandate = IntentMandate(
            id=str(uuid.uuid4()),
            user_id=user_id,
            constraints=json.dumps(constraints),
            timestamp=now,
            expiration=expiration,
            status="active",
            signature=self._generate_signature(user_id, constraints, now),
        )

        self.db.add(intent_mandate)
        self.db.commit()
        self.db.refresh(intent_mandate)

        return intent_mandate

    async def create_cart_mandate(
        self,
        intent_mandate_id: str,
        items: list[Dict],
        merchant: str,
        user_signature: str,
    ) -> CartMandate:
        """
        Create Cart Mandate - Specific items for approval

        Args:
            intent_mandate_id: Associated intent mandate
            items: List of items in cart
            merchant: Merchant name
            user_signature: User's signature approving the cart

        Returns:
            CartMandate

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
        # Verify intent mandate exists and is active
        intent_mandate = (
            self.db.query(IntentMandate)
            .filter_by(id=intent_mandate_id, status="active")
            .first()
        )

        if not intent_mandate:
            raise ValueError(
                f"Intent mandate {intent_mandate_id} not found or inactive"
            )

        # Check if expired
        if intent_mandate.expiration < datetime.utcnow():
            intent_mandate.status = "expired"
            self.db.commit()
            raise ValueError("Intent mandate has expired")

        # Validate against constraints
        constraints = json.loads(intent_mandate.constraints)
        total = sum(float(item.get("amount", 0) or 0) for item in items)

        if "max_amount" in constraints and total > constraints["max_amount"]:
            raise ValueError(
                f"Cart total ${total} exceeds max amount ${constraints['max_amount']}"
            )

        allowed_merchants = constraints.get("merchants") or constraints.get("merchant")
        if allowed_merchants:
            if isinstance(allowed_merchants, str):
                allowed_merchants = [allowed_merchants]
            normalized_merchants = {
                str(merchant_name).strip().lower()
                for merchant_name in allowed_merchants
                if merchant_name
            }
            if normalized_merchants and str(merchant).strip().lower() not in normalized_merchants:
                raise ValueError(
                    f"Merchant '{merchant}' is not permitted by the intent mandate"
                )

        allowed_categories = constraints.get("categories") or constraints.get("category")
        if allowed_categories:
            if isinstance(allowed_categories, str):
                allowed_categories = [allowed_categories]
            normalized_categories = {
                str(category_name).strip().lower()
                for category_name in allowed_categories
                if category_name
            }
            if normalized_categories:
                for item in items:
                    item_category = str(item.get("category", "")).strip().lower()
                    if not item_category or item_category not in normalized_categories:
                        raise ValueError(
                            "Cart contains items outside the allowed categories"
                        )

        # Create cart mandate
        cart_mandate = CartMandate(
            id=str(uuid.uuid4()),
            intent_mandate_id=intent_mandate_id,
            items=json.dumps(items),
            total=total,
            merchant=merchant,
            timestamp=datetime.utcnow(),
            user_signature=user_signature,
            status="pending",
        )

        self.db.add(cart_mandate)
        self.db.commit()
        self.db.refresh(cart_mandate)

        return cart_mandate

    async def create_payment_mandate(
        self, cart_mandate_id: str, payment_method: str
    ) -> PaymentMandate:
        """
        Create Payment Mandate - Execute payment with audit trail

        Args:
            cart_mandate_id: Associated cart mandate
            payment_method: Payment method (stripe, crypto, etc.)

        Returns:
            PaymentMandate
        """
        # Verify cart mandate exists
        cart_mandate = self.db.query(CartMandate).filter_by(id=cart_mandate_id).first()

        if not cart_mandate:
            raise ValueError(f"Cart mandate {cart_mandate_id} not found")

        if cart_mandate.status != "pending":
            raise ValueError(
                f"Cart mandate status is {cart_mandate.status}, must be pending"
            )

        # Create audit trail
        audit_trail = {
            "cart_mandate_id": cart_mandate_id,
            "intent_mandate_id": cart_mandate.intent_mandate_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payment_method": payment_method,
            "total_amount": float(cart_mandate.total),
            "merchant": cart_mandate.merchant,
            "items_count": len(json.loads(cart_mandate.items)),
        }

        # Create payment mandate
        payment_mandate = PaymentMandate(
            id=str(uuid.uuid4()),
            cart_mandate_id=cart_mandate_id,
            payment_method=payment_method,
            status="pending",
            audit_trail=json.dumps(audit_trail),
            timestamp=datetime.utcnow(),
        )

        self.db.add(payment_mandate)
        self.db.commit()
        self.db.refresh(payment_mandate)

        return payment_mandate

    async def execute_payment(
        self, payment_mandate_id: str, stripe_customer_id: Optional[str] = None
    ) -> Dict:
        """
        Execute payment using Stripe

        Args:
            payment_mandate_id: Payment mandate ID
            stripe_customer_id: Optional Stripe customer ID

        Returns:
            Payment result
        """
        # Get payment mandate
        payment_mandate = (
            self.db.query(PaymentMandate).filter_by(id=payment_mandate_id).first()
        )

        if not payment_mandate:
            raise ValueError(f"Payment mandate {payment_mandate_id} not found")

        if payment_mandate.status != "pending":
            raise ValueError(
                f"Payment mandate status is {payment_mandate.status}, must be pending"
            )

        # Get cart mandate
        cart_mandate = payment_mandate.cart_mandate

        if not cart_mandate:
            raise ValueError("Associated cart mandate not found")

        # Process payment through Stripe
        try:
            payment_result = await self.stripe.process_payment_mandate(
                payment_mandate=payment_mandate,
                amount=float(cart_mandate.total),
                customer_id=stripe_customer_id,
            )

            if payment_result["success"]:
                # Update statuses
                payment_mandate.status = "completed"
                payment_mandate.payment_processor_response = json.dumps(payment_result)
                cart_mandate.status = "completed"

                self.db.commit()

                return {
                    "success": True,
                    "payment_mandate_id": payment_mandate_id,
                    "transaction_id": payment_result.get("transaction_id"),
                    "amount": float(cart_mandate.total),
                    "status": "completed",
                }
            else:
                # Payment failed
                payment_mandate.status = "failed"
                payment_mandate.payment_processor_response = json.dumps(payment_result)
                cart_mandate.status = "failed"

                self.db.commit()

                return {
                    "success": False,
                    "payment_mandate_id": payment_mandate_id,
                    "error": payment_result.get("error"),
                    "message": payment_result.get("message"),
                }

        except Exception as e:
            # Handle exceptions
            payment_mandate.status = "failed"
            payment_mandate.payment_processor_response = json.dumps({"error": str(e)})

            self.db.commit()

            return {
                "success": False,
                "payment_mandate_id": payment_mandate_id,
                "error": "exception",
                "message": str(e),
            }

    def _generate_signature(
        self, user_id: str, constraints: Dict, timestamp: datetime
    ) -> str:
        """
        Generate cryptographic signature for intent mandate using Cloud KMS

        Uses RSA-2048 asymmetric signing with PSS padding.
        Keys are managed in Google Cloud KMS HSM and never leave the secure enclave.

        Args:
            user_id: User ID creating the mandate
            constraints: Mandate constraints dictionary
            timestamp: Mandate creation timestamp

        Returns:
            Base64-encoded RSA signature (verifiable with public key)
        """
        # Create deterministic data string for signing
        data = f"{user_id}:{json.dumps(constraints, sort_keys=True)}:{timestamp.isoformat()}"

        # Sign using Cloud KMS (RSA-2048 with SHA-256)
        signature = self.kms.sign_mandate(data)

        return signature

    def verify_mandate_signature(
        self, user_id: str, constraints: Dict, timestamp: datetime, signature: str
    ) -> bool:
        """
        Verify mandate signature using Cloud KMS public key

        Args:
            user_id: User ID from mandate
            constraints: Constraints from mandate
            timestamp: Timestamp from mandate
            signature: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        # Reconstruct original data
        data = f"{user_id}:{json.dumps(constraints, sort_keys=True)}:{timestamp.isoformat()}"

        # Verify using KMS public key
        return self.kms.verify_signature(data, signature)

    async def get_mandate_status(
        self, mandate_id: str, mandate_type: str = "payment"
    ) -> Dict:
        """
        Get status of any mandate

        Args:
            mandate_id: Mandate ID
            mandate_type: Type (intent, cart, or payment)

        Returns:
            Status information
        """
        if mandate_type == "intent":
            mandate = self.db.query(IntentMandate).filter_by(id=mandate_id).first()
        elif mandate_type == "cart":
            mandate = self.db.query(CartMandate).filter_by(id=mandate_id).first()
        elif mandate_type == "payment":
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
        else:
            raise ValueError(f"Invalid mandate type: {mandate_type}")

        if not mandate:
            raise ValueError(f"{mandate_type.title()} mandate {mandate_id} not found")

        return {
            "id": mandate.id,
            "type": mandate_type,
            "status": mandate.status,
            "timestamp": (
                mandate.timestamp.isoformat() if hasattr(mandate, "timestamp") else None
            ),
            "created_at": (
                mandate.created_at.isoformat()
                if hasattr(mandate, "created_at")
                else None
            ),
        }

    async def complete_ap2_flow(
        self,
        user_id: str,
        items: list[Dict],
        merchant: str,
        constraints: Optional[Dict] = None,
        stripe_customer_id: Optional[str] = None,
    ) -> Dict:
        """
        Complete full AP2 payment flow in one call

        1. Create Intent Mandate
        2. Create Cart Mandate
        3. Create Payment Mandate
        4. Execute Payment

        Args:
            user_id: User ID
            items: Cart items
            merchant: Merchant name
            constraints: Optional constraints (auto-generated if not provided)
            stripe_customer_id: Optional Stripe customer ID

        Returns:
            Complete flow result
        """
        # Auto-generate constraints if not provided
        if not constraints:
            total = sum(item.get("amount", 0) for item in items)
            constraints = {
                "max_amount": total * 1.1,  # 10% buffer
                "merchant": merchant,
                "approval_required": False,
            }

        # Step 1: Create Intent Mandate
        intent_mandate = await self.create_intent_mandate(
            user_id=user_id, constraints=constraints
        )

        # Step 2: Create Cart Mandate
        # Generate user signature (in production, this would be actual cryptographic signature)
        user_signature = self._generate_signature(
            user_id, {"items": items, "merchant": merchant}, datetime.utcnow()
        )

        cart_mandate = await self.create_cart_mandate(
            intent_mandate_id=intent_mandate.id,
            items=items,
            merchant=merchant,
            user_signature=user_signature,
        )

        # Step 3: Create Payment Mandate
        payment_mandate = await self.create_payment_mandate(
            cart_mandate_id=cart_mandate.id, payment_method="stripe"
        )

        # Step 4: Execute Payment
        payment_result = await self.execute_payment(
            payment_mandate_id=payment_mandate.id, stripe_customer_id=stripe_customer_id
        )

        return {
            "intent_mandate_id": intent_mandate.id,
            "cart_mandate_id": cart_mandate.id,
            "payment_mandate_id": payment_mandate.id,
            "payment_result": payment_result,
            "ap2_flow_complete": payment_result["success"],
        }
