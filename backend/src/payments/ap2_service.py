"""
AP2 Protocol Payment Service
Implements Google's Agent Payments Protocol (AP2 2026 stable spec) for
cryptographic payment verification with A2A 1.0, JSON-LD mandates,
Agent Signal HNP scoring, and x402 stablecoin support.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy.orm import Session

from ..models import CartMandate, IntentMandate, PaymentMandate, User
from ..security import get_kms_service
from .stripe_processor import StripePaymentProcessor

logger = logging.getLogger(__name__)

# AP2 2026 Constants
AP2_JSONLD_CONTEXT = "https://schema.org/ap2/v1"
AP2_PROTOCOL_VERSION = "2026.04"
A2A_PROTOCOL_VERSION = "1.0"
AGENT_ID = "ap2-expense-agent"
AGENT_VERSION = "1.0.0"

# Supported payment methods (AP2 2026: fiat + stablecoin)
PAYMENT_METHODS = {
    "stripe": "Stripe (fiat)",
    "x402_stablecoin": "x402 Stablecoin (USDC)",
    "expense_reimbursement": "Expense Reimbursement",
}


def build_agent_signal(
    authorization_type: str = "human_delegated",
    confidence_score: float = 1.0,
    human_verification: str = "pre_authorized",
    intent_mandate_signature: Optional[str] = None,
) -> Dict:
    """Build standardized Agent Signal for HNP risk scoring (AP2 2026).

    Card networks (Visa, Mastercard, Amex) use this metadata to distinguish
    human-initiated vs agent-initiated transactions and apply appropriate
    fraud scoring and Agent Purchase Protection policies.
    """
    return {
        "@context": AP2_JSONLD_CONTEXT,
        "@type": "AgentSignal",
        "agent_id": AGENT_ID,
        "agent_version": AGENT_VERSION,
        "ap2_protocol_version": AP2_PROTOCOL_VERSION,
        "a2a_protocol_version": A2A_PROTOCOL_VERSION,
        "authorization_type": authorization_type,
        "confidence_score": confidence_score,
        "human_verification": human_verification,
        "intent_mandate_signature": intent_mandate_signature,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


class AP2PaymentService:
    """
    AP2 Protocol payment flow implementation (2026 stable spec)

    Flow:
    1. Intent Mandate (JSON-LD): User authorizes agent within constraints
    2. Cart Mandate (JSON-LD): Merchant agent signs specific items
    3. Payment Mandate: Execute with Agent Signal for HNP risk scoring

    Supports: Stripe (fiat), x402 stablecoin, expense reimbursement
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

        # Defense-in-depth: validate constraints at service layer
        max_amount = constraints.get("max_amount")
        if max_amount is not None:
            try:
                max_amount = float(max_amount)
            except (TypeError, ValueError):
                raise ValueError("max_amount must be a number")
            if max_amount <= 0:
                raise ValueError("max_amount must be greater than zero")

        monthly_limit = constraints.get("monthly_limit")
        if monthly_limit is not None:
            try:
                monthly_limit = float(monthly_limit)
            except (TypeError, ValueError):
                raise ValueError("monthly_limit must be a number")
            if monthly_limit <= 0:
                raise ValueError("monthly_limit must be greater than zero")
            if max_amount is not None and monthly_limit < max_amount:
                raise ValueError(
                    "monthly_limit must be greater than or equal to max_amount"
                )

        if expiration_hours <= 0:
            raise ValueError("expiration_hours must be greater than zero")

        now = datetime.utcnow()
        expiration = now + timedelta(hours=expiration_hours)

        # Wrap constraints in JSON-LD format (AP2 2026)
        jsonld_constraints = {
            "@context": AP2_JSONLD_CONTEXT,
            "@type": "IntentMandate",
            "ap2_protocol_version": AP2_PROTOCOL_VERSION,
            **constraints,
        }

        intent_mandate = IntentMandate(
            id=str(uuid.uuid4()),
            user_id=user_id,
            constraints=json.dumps(jsonld_constraints),
            timestamp=now,
            expiration=expiration,
            status="active",
            signature=self._generate_signature(user_id, constraints, now),
            # AP2 2026: Agent identity fields
            agent_id=AGENT_ID,
            authorization_type=constraints.get("authorization_type", "human_delegated"),
            a2a_protocol_version=A2A_PROTOCOL_VERSION,
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

        # Validate against constraints (strip JSON-LD envelope)
        constraints = json.loads(intent_mandate.constraints)
        constraints = {k: v for k, v in constraints.items() if not k.startswith("@")}
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
            if (
                normalized_merchants
                and str(merchant).strip().lower() not in normalized_merchants
            ):
                raise ValueError(
                    f"Merchant '{merchant}' is not permitted by the intent mandate"
                )

        allowed_categories = constraints.get("categories") or constraints.get(
            "category"
        )
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

        # Wrap items in JSON-LD format (AP2 2026)
        jsonld_items = {
            "@context": AP2_JSONLD_CONTEXT,
            "@type": "CartMandate",
            "ap2_protocol_version": AP2_PROTOCOL_VERSION,
            "items": items,
            "total": total,
            "merchant": merchant,
        }

        # Generate UCP order reference (AP2 2026)
        cart_id = str(uuid.uuid4())
        ucp_order_id = f"ucp-{cart_id[:8]}-{int(datetime.utcnow().timestamp())}"

        # Merchant agent signature — sign cart contents for verification
        merchant_sig_data = f"{merchant}:{total}:{json.dumps(items, sort_keys=True)}"
        merchant_agent_signature = self.kms.sign_mandate(merchant_sig_data)

        # Create cart mandate
        cart_mandate = CartMandate(
            id=cart_id,
            intent_mandate_id=intent_mandate_id,
            items=json.dumps(jsonld_items),
            total=total,
            merchant=merchant,
            timestamp=datetime.utcnow(),
            user_signature=user_signature,
            status="pending",
            # AP2 2026: UCP fields
            ucp_order_id=ucp_order_id,
            merchant_agent_signature=merchant_agent_signature,
        )

        self.db.add(cart_mandate)
        self.db.commit()
        self.db.refresh(cart_mandate)

        return cart_mandate

    async def create_payment_mandate(
        self, cart_mandate_id: str, payment_method: str
    ) -> PaymentMandate:
        """
        Create Payment Mandate - Execute payment with audit trail and Agent Signal

        Args:
            cart_mandate_id: Associated cart mandate
            payment_method: Payment method (stripe, x402_stablecoin, expense_reimbursement)

        Returns:
            PaymentMandate
        """
        # Validate payment method
        if payment_method not in PAYMENT_METHODS:
            raise ValueError(
                f"Invalid payment method '{payment_method}'. "
                f"Supported: {', '.join(PAYMENT_METHODS.keys())}"
            )

        # Verify cart mandate exists
        cart_mandate = self.db.query(CartMandate).filter_by(id=cart_mandate_id).first()

        if not cart_mandate:
            raise ValueError(f"Cart mandate {cart_mandate_id} not found")

        if cart_mandate.status != "pending":
            raise ValueError(
                f"Cart mandate status is {cart_mandate.status}, must be pending"
            )

        # Get intent mandate signature for Agent Signal chain
        intent_mandate = (
            self.db.query(IntentMandate)
            .filter_by(id=cart_mandate.intent_mandate_id)
            .first()
        )
        intent_signature = intent_mandate.signature if intent_mandate else None

        # Build Agent Signal for HNP risk scoring (AP2 2026)
        agent_signal = build_agent_signal(
            authorization_type=(
                intent_mandate.authorization_type
                if intent_mandate
                else "human_delegated"
            ),
            confidence_score=1.0,
            human_verification="pre_authorized",
            intent_mandate_signature=intent_signature,
        )

        # Parse items safely — handle JSON-LD wrapped format
        items_data = json.loads(cart_mandate.items)
        items_list = (
            items_data.get("items", items_data)
            if isinstance(items_data, dict)
            else items_data
        )

        # Create audit trail with Agent Signal
        audit_trail = {
            "@context": AP2_JSONLD_CONTEXT,
            "@type": "PaymentMandate",
            "ap2_protocol_version": AP2_PROTOCOL_VERSION,
            "cart_mandate_id": cart_mandate_id,
            "intent_mandate_id": cart_mandate.intent_mandate_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payment_method": payment_method,
            "total_amount": float(cart_mandate.total),
            "merchant": cart_mandate.merchant,
            "items_count": len(items_list) if isinstance(items_list, list) else 0,
            "agent_signal": agent_signal,
        }

        # Create payment mandate
        payment_mandate = PaymentMandate(
            id=str(uuid.uuid4()),
            cart_mandate_id=cart_mandate_id,
            payment_method=payment_method,
            status="pending",
            audit_trail=json.dumps(audit_trail),
            timestamp=datetime.utcnow(),
            # AP2 2026: Store Agent Signal for HNP risk scoring
            agent_signal=json.dumps(agent_signal),
        )

        self.db.add(payment_mandate)
        self.db.commit()
        self.db.refresh(payment_mandate)

        return payment_mandate

    async def execute_payment(
        self, payment_mandate_id: str, stripe_customer_id: Optional[str] = None
    ) -> Dict:
        """
        Execute payment via the appropriate processor (AP2 2026)

        Routes to Stripe (fiat), x402 stablecoin stub, or expense reimbursement
        based on payment_method. Passes Agent Signal as processor metadata.

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

        # Parse Agent Signal for processor metadata
        agent_signal = None
        if payment_mandate.agent_signal:
            try:
                agent_signal = json.loads(payment_mandate.agent_signal)
            except (json.JSONDecodeError, TypeError):
                pass

        # Route to payment processor based on method
        try:
            method = payment_mandate.payment_method

            if method == "x402_stablecoin":
                # x402 stablecoin (Coinbase via Stripe Bridge) — stub
                payment_result = {
                    "success": False,
                    "error": "not_implemented",
                    "message": "x402 stablecoin payments coming soon (Coinbase/Stripe Bridge)",
                }
            elif method == "expense_reimbursement":
                # Internal reimbursement — mark as completed immediately
                payment_result = {
                    "success": True,
                    "transaction_id": f"reimb-{payment_mandate.id[:8]}",
                    "processor": "internal_reimbursement",
                }
            else:
                # Default: Stripe (fiat)
                payment_result = await self.stripe.process_payment_mandate(
                    payment_mandate=payment_mandate,
                    amount=float(cart_mandate.total),
                    customer_id=stripe_customer_id,
                    metadata=(
                        {"agent_signal": json.dumps(agent_signal)}
                        if agent_signal
                        else None
                    ),
                )

            if payment_result.get("success"):
                payment_mandate.status = "completed"
                payment_mandate.payment_processor_response = json.dumps(payment_result)
                cart_mandate.status = "completed"

                self.db.commit()

                return {
                    "success": True,
                    "payment_mandate_id": payment_mandate_id,
                    "transaction_id": payment_result.get("transaction_id"),
                    "amount": float(cart_mandate.total),
                    "payment_method": method,
                    "status": "completed",
                }
            else:
                payment_mandate.status = "failed"
                payment_mandate.payment_processor_response = json.dumps(payment_result)
                cart_mandate.status = "failed"

                self.db.commit()

                return {
                    "success": False,
                    "payment_mandate_id": payment_mandate_id,
                    "payment_method": method,
                    "error": payment_result.get("error"),
                    "message": payment_result.get("message"),
                }

        except Exception as e:
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

        type_map = {
            "intent": "IntentMandate",
            "cart": "CartMandate",
            "payment": "PaymentMandate",
        }

        result = {
            "@context": AP2_JSONLD_CONTEXT,
            "@type": type_map.get(mandate_type, "Mandate"),
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

        # Add type-specific fields
        if mandate_type == "intent" and hasattr(mandate, "agent_id"):
            result["agent_id"] = mandate.agent_id
            result["authorization_type"] = mandate.authorization_type
        elif mandate_type == "cart" and hasattr(mandate, "ucp_order_id"):
            result["ucp_order_id"] = mandate.ucp_order_id
            result["merchant"] = mandate.merchant
            result["total"] = float(mandate.total) if mandate.total else None
        elif mandate_type == "payment" and hasattr(mandate, "payment_method"):
            result["payment_method"] = mandate.payment_method
            if mandate.agent_signal:
                try:
                    sig = json.loads(mandate.agent_signal)
                    result["agent_signal"] = {
                        "agent_id": sig.get("agent_id"),
                        "authorization_type": sig.get("authorization_type"),
                        "confidence_score": sig.get("confidence_score"),
                    }
                except (json.JSONDecodeError, TypeError):
                    pass

        return result

    async def complete_ap2_flow(
        self,
        user_id: str,
        items: list[Dict],
        merchant: str,
        constraints: Optional[Dict] = None,
        payment_method: str = "stripe",
        stripe_customer_id: Optional[str] = None,
    ) -> Dict:
        """
        Complete full AP2 payment flow in one call (AP2 2026)

        1. Create Intent Mandate (JSON-LD + agent identity)
        2. Create Cart Mandate (JSON-LD)
        3. Create Payment Mandate (Agent Signal for HNP scoring)
        4. Execute Payment (routed by payment_method)

        Args:
            user_id: User ID
            items: Cart items
            merchant: Merchant name
            constraints: Optional constraints (auto-generated if not provided)
            payment_method: Payment method (stripe, x402_stablecoin, expense_reimbursement)
            stripe_customer_id: Optional Stripe customer ID

        Returns:
            Complete flow result with AP2 2026 metadata
        """
        # NOTE: Usage tracking is handled by the route handler in ap2.py
        # Do NOT track here to avoid double-counting

        # Auto-generate constraints if not provided
        if not constraints:
            total = sum(item.get("amount", 0) for item in items)
            import math

            constraints = {
                "max_amount": math.ceil(total * 1.05 * 100)
                / 100,  # 5% buffer (matches frontend)
                "merchant": merchant,
                "approval_required": False,
            }

        # Step 1: Create Intent Mandate
        intent_mandate = await self.create_intent_mandate(
            user_id=user_id, constraints=constraints
        )

        # Step 2: Create Cart Mandate
        user_signature = self._generate_signature(
            user_id, {"items": items, "merchant": merchant}, datetime.utcnow()
        )

        cart_mandate = await self.create_cart_mandate(
            intent_mandate_id=intent_mandate.id,
            items=items,
            merchant=merchant,
            user_signature=user_signature,
        )

        # Step 3: Create Payment Mandate (with Agent Signal)
        payment_mandate = await self.create_payment_mandate(
            cart_mandate_id=cart_mandate.id, payment_method=payment_method
        )

        # Step 4: Execute Payment
        payment_result = await self.execute_payment(
            payment_mandate_id=payment_mandate.id, stripe_customer_id=stripe_customer_id
        )

        return {
            "@context": AP2_JSONLD_CONTEXT,
            "@type": "AP2FlowResult",
            "ap2_protocol_version": AP2_PROTOCOL_VERSION,
            "intent_mandate_id": intent_mandate.id,
            "cart_mandate_id": cart_mandate.id,
            "payment_mandate_id": payment_mandate.id,
            "payment_method": payment_method,
            "payment_result": payment_result,
            "ap2_flow_complete": payment_result["success"],
        }

    def find_matching_intent_mandate(
        self,
        user_id: str,
        amount: float,
        category: str,
        merchant: str,
        organization_id: str,
    ) -> Optional[IntentMandate]:
        """
        Find active Intent Mandate that authorizes this expense.

        This is the CORE of AP2 autonomous approval - checks if user has
        pre-authorized an AI agent to approve expenses matching these criteria.

        Args:
            user_id: User submitting the expense
            amount: Expense amount
            category: Expense category
            merchant: Vendor/merchant name
            organization_id: Organization context

        Returns:
            IntentMandate if match found, None otherwise

        Example:
            Intent Mandate: "Auto-approve Amazon office_supplies up to $200/month"
            Expense: $45 from Amazon for office_supplies
            Result: Match! Auto-approve via AP2
        """
        now = datetime.utcnow()

        # Find active, non-expired Intent Mandates for this user
        mandates = (
            self.db.query(IntentMandate)
            .filter(
                IntentMandate.user_id == user_id,
                IntentMandate.status == "active",
                IntentMandate.expiration > now,
            )
            .all()
        )

        logger.info(
            f"[AP2] Found {len(mandates)} active Intent Mandates for user {user_id}"
        )

        # Try each mandate (most specific first if we add priority later)
        for mandate in mandates:
            try:
                constraints = json.loads(mandate.constraints)
                # Strip JSON-LD envelope if present
                constraints = {
                    k: v for k, v in constraints.items() if not k.startswith("@")
                }

                # Check if expense matches this mandate's constraints
                if self._expense_matches_constraints(
                    amount, category, merchant, constraints, mandate.id, organization_id
                ):
                    logger.info(
                        f"[AP2] Expense matches Intent Mandate {mandate.id}: "
                        f"${amount} from {merchant} ({category})"
                    )
                    return mandate
                else:
                    logger.debug(
                        f"[AP2] Expense does not match Intent Mandate {mandate.id}"
                    )
            except Exception as e:
                logger.error(f"[AP2] Error evaluating Intent Mandate {mandate.id}: {e}")
                continue

        logger.info(f"[AP2] No matching Intent Mandate found for expense")
        return None

    def _expense_matches_constraints(
        self,
        amount: float,
        category: str,
        merchant: str,
        constraints: Dict,
        mandate_id: str,
        organization_id: str,
    ) -> bool:
        """
        Check if expense satisfies Intent Mandate constraints.

        Validates:
        - Amount limits (max_amount)
        - Category restrictions
        - Merchant whitelist
        - Monthly spending limits

        Args:
            amount: Expense amount
            category: Expense category
            merchant: Merchant name
            constraints: Mandate constraints dict
            mandate_id: Intent Mandate ID (for usage tracking)
            organization_id: Organization context

        Returns:
            True if expense matches all constraints, False otherwise
        """
        # 1. Check per-expense amount limit
        if "max_amount" in constraints:
            max_amt = float(constraints["max_amount"])
            if amount > max_amt:
                logger.debug(f"[AP2] Amount ${amount} exceeds max ${max_amt}")
                return False

        # 2. Check category restrictions
        allowed_categories = constraints.get("categories") or constraints.get(
            "category"
        )
        if allowed_categories:
            # Normalize to list
            if isinstance(allowed_categories, str):
                allowed_categories = [allowed_categories]

            # Case-insensitive matching
            normalized_categories = {
                str(cat).strip().lower() for cat in allowed_categories if cat
            }

            if normalized_categories:
                category_lower = str(category).strip().lower()
                if category_lower not in normalized_categories:
                    logger.debug(
                        f"[AP2] Category '{category}' not in allowed: {normalized_categories}"
                    )
                    return False

        # 3. Check merchant restrictions
        allowed_merchants = constraints.get("merchants") or constraints.get("merchant")
        if allowed_merchants:
            # Normalize to list
            if isinstance(allowed_merchants, str):
                allowed_merchants = [allowed_merchants]

            # Case-insensitive matching
            normalized_merchants = {
                str(merch).strip().lower() for merch in allowed_merchants if merch
            }

            if normalized_merchants:
                merchant_lower = str(merchant).strip().lower()
                if merchant_lower not in normalized_merchants:
                    logger.debug(
                        f"[AP2] Merchant '{merchant}' not in allowed: {normalized_merchants}"
                    )
                    return False

        # 4. Check monthly spending limit
        if "monthly_limit" in constraints:
            monthly_limit = float(constraints["monthly_limit"])
            current_usage = self._get_mandate_monthly_usage(mandate_id, organization_id)

            if current_usage + amount > monthly_limit:
                logger.debug(
                    f"[AP2] Monthly limit exceeded: ${current_usage + amount} > ${monthly_limit}"
                )
                return False

        # All constraints satisfied
        logger.debug(f"[AP2] All constraints satisfied for mandate {mandate_id}")
        return True

    def _get_mandate_monthly_usage(
        self, mandate_id: str, organization_id: str
    ) -> float:
        """
        Calculate total spending this month for a specific Intent Mandate.

        Sums all expenses auto-approved via this mandate in current calendar month.

        Args:
            mandate_id: Intent Mandate ID
            organization_id: Organization context

        Returns:
            Total amount spent via this mandate this month
        """
        from sqlalchemy import func

        from ..models import Expense

        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sum expenses approved via this Intent Mandate this month
        total = (
            self.db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.intent_mandate_id == mandate_id,
                Expense.organization_id == organization_id,
                Expense.auto_approved == True,
                Expense.created_at >= start_of_month,
            )
            .scalar()
        ) or 0

        return float(total)
