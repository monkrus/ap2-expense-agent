# GCP Consumer Procurement API Migration Guide
## Detailed Implementation Plan for Marketplace Integration

**Priority**: P0 - CRITICAL
**Estimated Time**: 16-20 hours
**Complexity**: Medium-High
**Risk Level**: Medium (with comprehensive testing)

---

## 🎯 Overview

This document provides a step-by-step guide to migrate from the current GCP Marketplace integration to the production-ready Consumer Procurement API implementation.

### Current State

**Files Currently Using Old API**:
1. `backend/src/gcp/marketplace_client.py` - Uses old Service Control API
2. `backend/src/gcp/usage_reporter.py` - Old usage reporting
3. `backend/src/routes/gcp_webhooks.py` - HMAC verification (should be JWT)
4. `backend/src/gcp/procurement_handler.py` - Entitlement creation (partially correct)

### Target State

**What We're Building**:
1. ✅ Consumer Procurement API client
2. ✅ JWT-based webhook verification (Google-signed tokens)
3. ✅ Entitlement-based feature gating middleware
4. ✅ Usage metering and reporting
5. ✅ Retry logic with exponential backoff
6. ✅ Dead letter queue for failed events

---

## 📋 Migration Checklist

### Phase 1: Dependencies & Setup (1-2 hours)
- [ ] Install new libraries
- [ ] Update requirements.txt
- [ ] Create new configuration settings
- [ ] Set up test environment

### Phase 2: Consumer Procurement Client (3-4 hours)
- [ ] Create new `consumer_procurement_client.py`
- [ ] Implement entitlement operations
- [ ] Add error handling
- [ ] Write unit tests

### Phase 3: JWT Verification (2-3 hours)
- [ ] Implement Google JWT verification
- [ ] Update webhook endpoints
- [ ] Add public key caching
- [ ] Test with sample tokens

### Phase 4: Usage Metering (4-5 hours)
- [ ] Create usage tracking service
- [ ] Add tracking to metered endpoints
- [ ] Implement daily usage reporter
- [ ] Set up Cloud Scheduler

### Phase 5: Feature Gating (3-4 hours)
- [ ] Create entitlement middleware
- [ ] Define plan features
- [ ] Apply to protected endpoints
- [ ] Add upgrade prompts

### Phase 6: Testing (3-4 hours)
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests with staging
- [ ] Load testing

---

## 🔧 Phase 1: Dependencies & Setup

### 1.1 Install Required Libraries

```bash
cd backend
pip install google-cloud-commerce-consumer-procurement==1.1.0
pip install google-cloud-service-control==1.11.1
pip install PyJWT==2.8.0
pip install cryptography==41.0.7
pip install requests==2.31.0
pip install pydantic==2.5.3
```

### 1.2 Update requirements.txt

```txt
# Add to backend/requirements.txt

# Google Cloud APIs
google-cloud-commerce-consumer-procurement==1.1.0
google-cloud-service-control==1.11.1
google-cloud-secret-manager==2.16.4
google-api-core==2.15.0

# JWT and Crypto
PyJWT[crypto]==2.8.0
cryptography==41.0.7

# Utilities
requests==2.31.0
tenacity==8.2.3  # For retry logic
```

### 1.3 Update Configuration

**File**: `backend/src/config.py`

```python
# Add new configuration settings

class Settings(BaseSettings):
    # ... existing settings ...

    # GCP Marketplace Settings
    GCP_PROJECT_ID: str = ""
    GCP_SERVICE_ACCOUNT_EMAIL: str = ""
    GCP_MARKETPLACE_PRODUCT_ID: str = ""  # From Partner Portal
    GCP_MARKETPLACE_SERVICE_NAME: str = "ap2-expense-agent.googleusercontent.com"

    # Consumer Procurement API
    CONSUMER_PROCUREMENT_PARENT: str = ""  # Format: "billingAccounts/{account_id}"

    # JWT Verification
    GOOGLE_CERTS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"
    JWT_AUDIENCE: str = ""  # Your GCP project ID or service URL
    JWT_ISSUER: str = "accounts.google.com"

    # Usage Reporting
    USAGE_REPORTING_ENABLED: bool = True
    USAGE_REPORTING_SCHEDULE: str = "0 1 * * *"  # Daily at 1 AM UTC

    # Retry Configuration
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_RETRY_DELAY: int = 60  # seconds
    WEBHOOK_RETRY_BACKOFF: int = 2  # exponential multiplier

    class Config:
        env_file = ".env"
```

### 1.4 Environment Variables

**File**: `backend/.env.production.template`

```bash
# GCP Marketplace Configuration
GCP_PROJECT_ID=ap2-expense-prod
GCP_SERVICE_ACCOUNT_EMAIL=ap2-expense-backend@ap2-expense-prod.iam.gserviceaccount.com
GCP_MARKETPLACE_PRODUCT_ID=your-product-id
GCP_MARKETPLACE_SERVICE_NAME=ap2-expense-agent.googleusercontent.com
CONSUMER_PROCUREMENT_PARENT=billingAccounts/YOUR_BILLING_ACCOUNT_ID
JWT_AUDIENCE=ap2-expense-prod
JWT_ISSUER=accounts.google.com
USAGE_REPORTING_ENABLED=true
```

---

## 🔧 Phase 2: Consumer Procurement Client

### 2.1 Create New Client

**File**: `backend/src/gcp/consumer_procurement_client.py` (NEW)

```python
"""
Consumer Procurement API Client
Handles entitlement lifecycle operations for GCP Marketplace
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from google.cloud import commerce_consumer_procurement_v1
from google.cloud.commerce_consumer_procurement_v1 import (
    ConsumerProcurementServiceClient,
    Entitlement,
    GetEntitlementRequest,
    ListEntitlementsRequest,
)
from google.api_core import exceptions as gcp_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings

logger = logging.getLogger(__name__)


class ConsumerProcurementClient:
    """Client for Google Cloud Consumer Procurement API"""

    def __init__(self):
        try:
            self.client = ConsumerProcurementServiceClient()
            self.parent = settings.CONSUMER_PROCUREMENT_PARENT
            logger.info("Consumer Procurement client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Consumer Procurement client: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def get_entitlement(self, entitlement_name: str) -> Optional[Entitlement]:
        """
        Get entitlement details by name

        Args:
            entitlement_name: Full resource name (e.g., "billingAccounts/{account}/entitlements/{id}")

        Returns:
            Entitlement object or None if not found
        """
        try:
            request = GetEntitlementRequest(name=entitlement_name)
            entitlement = self.client.get_entitlement(request=request)

            logger.info(
                f"Retrieved entitlement: {entitlement_name}",
                extra={
                    "entitlement_id": entitlement.name,
                    "state": entitlement.state,
                    "plan": entitlement.plan,
                }
            )

            return entitlement

        except gcp_exceptions.NotFound:
            logger.warning(f"Entitlement not found: {entitlement_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get entitlement {entitlement_name}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def list_entitlements(
        self,
        page_size: int = 100,
        page_token: str = None
    ) -> List[Entitlement]:
        """
        List all entitlements for the billing account

        Args:
            page_size: Number of results per page
            page_token: Token for pagination

        Returns:
            List of Entitlement objects
        """
        try:
            request = ListEntitlementsRequest(
                parent=self.parent,
                page_size=page_size,
                page_token=page_token or ""
            )

            page_result = self.client.list_entitlements(request=request)
            entitlements = [entitlement for entitlement in page_result]

            logger.info(f"Listed {len(entitlements)} entitlements")
            return entitlements

        except Exception as e:
            logger.error(f"Failed to list entitlements: {e}")
            raise

    async def get_entitlement_by_account_id(
        self,
        account_id: str
    ) -> Optional[Entitlement]:
        """
        Find entitlement by GCP account ID

        Args:
            account_id: Customer's GCP account ID

        Returns:
            Entitlement object or None
        """
        try:
            entitlements = await self.list_entitlements()

            for entitlement in entitlements:
                # Match by account ID in metadata
                if entitlement.account == account_id:
                    return entitlement

            logger.warning(f"No entitlement found for account: {account_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to find entitlement for account {account_id}: {e}")
            return None

    def parse_entitlement_data(self, entitlement: Entitlement) -> Dict:
        """
        Parse entitlement object into dictionary

        Args:
            entitlement: Entitlement object from API

        Returns:
            Dictionary with entitlement data
        """
        return {
            "entitlement_id": entitlement.name,
            "account_id": entitlement.account,
            "state": entitlement.state.name,
            "plan": entitlement.plan,
            "product": entitlement.product,
            "create_time": entitlement.create_time,
            "update_time": entitlement.update_time,
            "message_to_user": entitlement.message_to_user,
        }


# Singleton instance
_client_instance = None


def get_procurement_client() -> ConsumerProcurementClient:
    """Get singleton instance of procurement client"""
    global _client_instance
    if _client_instance is None:
        _client_instance = ConsumerProcurementClient()
    return _client_instance
```

### 2.2 Update Procurement Handler

**File**: `backend/src/gcp/procurement_handler.py`

**Changes Needed**:

```python
# BEFORE (lines 40-69):
async def handle_procurement_webhook(webhook_data: Dict, db: Session) -> Dict:
    """
    Handle new customer signup from GCP Marketplace
    ...
    """
    # Old implementation using generic webhook data

# AFTER:
from .consumer_procurement_client import get_procurement_client

async def handle_procurement_webhook(
    webhook_data: Dict,
    entitlement: Entitlement,  # Add entitlement object
    db: Session
) -> Dict:
    """
    Handle new customer signup from GCP Marketplace

    Args:
        webhook_data: Webhook payload from Google
        entitlement: Entitlement object from Consumer Procurement API
        db: Database session

    Returns:
        Dict with organization_id, admin_user_id, status
    """
    try:
        # Extract data from entitlement object (more reliable)
        entitlement_id = entitlement.name
        account_id = entitlement.account
        plan = entitlement.plan or "professional"
        state = entitlement.state.name

        # Get user email from entitlement metadata
        admin_email = entitlement.usageReportingId or webhook_data.get("user_email")

        # Validate
        if not entitlement_id or not admin_email:
            raise ValueError("Missing required fields")

        # Check if already exists
        existing_sub = (
            db.query(OrganizationSubscription)
            .filter_by(gcp_entitlement_id=entitlement_id)
            .first()
        )

        if existing_sub:
            return {
                "status": "already_exists",
                "organization_id": existing_sub.organization_id,
            }

        # Create organization...
        # (Rest of implementation remains similar)

    except Exception as e:
        logger.error(f"Procurement webhook failed: {e}", exc_info=True)
        raise
```

---

## 🔧 Phase 3: JWT Verification

### 3.1 Create JWT Verification Module

**File**: `backend/src/gcp/jwt_verification.py` (NEW)

```python
"""
Google JWT Verification for GCP Marketplace Webhooks
"""

import jwt
import logging
import requests
from functools import lru_cache
from typing import Dict, Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from ..config import settings

logger = logging.getLogger(__name__)


class GoogleJWTVerifier:
    """Verify JWT tokens signed by Google"""

    def __init__(self):
        self.certs_url = settings.GOOGLE_CERTS_URL
        self.audience = settings.JWT_AUDIENCE
        self.issuer = settings.JWT_ISSUER
        self._certs_cache = None
        self._certs_cache_time = None
        self._cache_duration = timedelta(hours=6)  # Refresh every 6 hours

    @lru_cache(maxsize=1)
    def _fetch_google_public_keys(self) -> Dict:
        """
        Fetch Google's public keys for JWT verification

        Returns:
            Dict of public keys by key ID (kid)
        """
        try:
            # Check cache
            if self._certs_cache and self._certs_cache_time:
                if datetime.utcnow() - self._certs_cache_time < self._cache_duration:
                    return self._certs_cache

            # Fetch from Google
            response = requests.get(self.certs_url, timeout=10)
            response.raise_for_status()

            certs = response.json()

            # Cache results
            self._certs_cache = certs
            self._certs_cache_time = datetime.utcnow()

            logger.info("Fetched Google public keys successfully")
            return certs

        except Exception as e:
            logger.error(f"Failed to fetch Google public keys: {e}")
            raise HTTPException(500, "Unable to verify webhook signature")

    def verify_token(self, token: str) -> Dict:
        """
        Verify JWT token from Google

        Args:
            token: JWT token string

        Returns:
            Decoded claims dictionary

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get public keys
            keys = self._fetch_google_public_keys()

            # Decode token header (without verification) to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise ValueError("Token missing 'kid' header")

            # Find matching public key
            public_key = None
            for key in keys.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(
                        key
                    )
                    break

            if not public_key:
                raise ValueError(f"Public key not found for kid: {kid}")

            # Verify and decode token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )

            logger.info(
                "JWT verified successfully",
                extra={
                    "subject": claims.get("sub"),
                    "email": claims.get("email"),
                }
            )

            return claims

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise HTTPException(401, "Token expired")
        except jwt.InvalidAudienceError:
            logger.warning("JWT invalid audience")
            raise HTTPException(401, "Invalid token audience")
        except jwt.InvalidIssuerError:
            logger.warning("JWT invalid issuer")
            raise HTTPException(401, "Invalid token issuer")
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT invalid: {e}")
            raise HTTPException(401, f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"JWT verification failed: {e}", exc_info=True)
            raise HTTPException(500, "Token verification failed")

    async def verify_webhook_request(self, request: Request) -> Dict:
        """
        Extract and verify JWT from webhook request

        Args:
            request: FastAPI Request object

        Returns:
            Verified claims dictionary
        """
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid Authorization header")

        token = auth_header.replace("Bearer ", "")

        # Verify token
        claims = self.verify_token(token)

        return claims


# Singleton instance
_verifier_instance = None


def get_jwt_verifier() -> GoogleJWTVerifier:
    """Get singleton instance of JWT verifier"""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = GoogleJWTVerifier()
    return _verifier_instance


# Dependency for FastAPI routes
async def verify_gcp_webhook_jwt(request: Request) -> Dict:
    """
    FastAPI dependency to verify GCP webhook JWT

    Usage:
        @router.post("/webhook")
        async def webhook(claims: Dict = Depends(verify_gcp_webhook_jwt)):
            ...
    """
    verifier = get_jwt_verifier()
    return await verifier.verify_webhook_request(request)
```

### 3.2 Update Webhook Routes

**File**: `backend/src/routes/gcp_webhooks.py`

**Changes Needed**:

```python
# BEFORE:
from ..security import verify_webhook_signature

@router.post("/procurement")
async def handle_procurement(
    request: Request,
    signature: str = Header(..., alias="X-GCP-Signature"),
    db: Session = Depends(get_db)
):
    body = await request.body()
    if not verify_webhook_signature(body, signature):
        raise HTTPException(403, "Invalid signature")
    # ...

# AFTER:
from ..gcp.jwt_verification import verify_gcp_webhook_jwt
from ..gcp.consumer_procurement_client import get_procurement_client

@router.post("/procurement")
async def handle_procurement_event(
    request: Request,
    claims: Dict = Depends(verify_gcp_webhook_jwt),  # JWT verification
    db: Session = Depends(get_db)
):
    """
    Handle entitlement lifecycle events from GCP Marketplace

    Webhook URL: https://api.ap2expense.com/api/webhooks/gcp/procurement
    Authentication: Google-signed JWT in Authorization header
    """
    try:
        # JWT already verified by dependency
        logger.info(
            "Received GCP procurement webhook",
            extra={
                "subject": claims.get("sub"),
                "email": claims.get("email"),
            }
        )

        # Parse request body
        body = await request.json()
        event_type = body.get("eventType")
        entitlement_name = body.get("entitlement", {}).get("name")

        if not entitlement_name:
            raise HTTPException(400, "Missing entitlement name")

        # Fetch full entitlement details from Consumer Procurement API
        procurement_client = get_procurement_client()
        entitlement = await procurement_client.get_entitlement(entitlement_name)

        if not entitlement:
            raise HTTPException(404, "Entitlement not found")

        # Route to appropriate handler based on event type
        if event_type == "ENTITLEMENT_CREATION_REQUESTED":
            result = await handle_entitlement_creation(entitlement, body, db)
        elif event_type == "ENTITLEMENT_ACTIVE":
            result = await handle_entitlement_activation(entitlement, body, db)
        elif event_type == "ENTITLEMENT_PLAN_CHANGE_REQUESTED":
            result = await handle_plan_change(entitlement, body, db)
        elif event_type == "ENTITLEMENT_PLAN_CHANGED":
            result = await handle_plan_changed(entitlement, body, db)
        elif event_type == "ENTITLEMENT_CANCELLATION_REQUESTED":
            result = await handle_cancellation_requested(entitlement, body, db)
        elif event_type == "ENTITLEMENT_CANCELLED":
            result = await handle_cancellation_completed(entitlement, body, db)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return {"status": "ignored", "message": f"Unknown event type: {event_type}"}

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        raise HTTPException(500, "Webhook processing failed")
```

---

## 🔧 Phase 4: Usage Metering

### 4.1 Create Usage Tracking Service

**File**: `backend/src/services/usage_tracking.py` (NEW)

```python
"""
Usage Tracking Service for GCP Marketplace Billing
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import UsageEvent, OrganizationSubscription
from ..models_billing import BillingEvent

logger = logging.getLogger(__name__)


# Define metered resources and limits
METERED_RESOURCES = {
    "ai_categorizations": {
        "unit": "scans",
        "display_name": "AI Categorizations",
        "included": {
            "STARTER": 500,
            "PROFESSIONAL": 5000,
            "ENTERPRISE": "unlimited",
            "ENTERPRISE_PLUS": "unlimited",
        },
        "overage_price": 0.05,  # $0.05 per scan over limit
    },
    "ap2_transactions": {
        "unit": "transactions",
        "display_name": "AP2 Transactions",
        "included": {
            "STARTER": 10,
            "PROFESSIONAL": 100,
            "ENTERPRISE": "unlimited",
            "ENTERPRISE_PLUS": "unlimited",
        },
        "overage_price": 0.10,  # $0.10 per transaction over limit
    },
    "receipt_ocr": {
        "unit": "scans",
        "display_name": "Receipt OCR",
        "included": {
            "STARTER": 100,
            "PROFESSIONAL": 2000,
            "ENTERPRISE": "unlimited",
            "ENTERPRISE_PLUS": "unlimited",
        },
        "overage_price": 0.02,  # $0.02 per scan over limit
    },
}


class UsageTracker:
    """Track usage events for metered billing"""

    @staticmethod
    async def track_event(
        db: Session,
        organization_id: str,
        event_type: str,
        quantity: int = 1,
        metadata: Optional[Dict] = None
    ) -> UsageEvent:
        """
        Track a usage event

        Args:
            db: Database session
            organization_id: Organization ID
            event_type: Type of event (e.g., "ai_categorization")
            quantity: Quantity consumed (default 1)
            metadata: Additional event data

        Returns:
            UsageEvent object
        """
        try:
            # Create usage event
            event = UsageEvent(
                organization_id=organization_id,
                event_type=event_type,
                quantity=quantity,
                metadata=metadata or {},
                occurred_at=datetime.utcnow()
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            logger.info(
                f"Tracked usage event: {event_type}",
                extra={
                    "organization_id": organization_id,
                    "event_type": event_type,
                    "quantity": quantity,
                }
            )

            # Check if usage exceeds limits
            await UsageTracker.check_usage_limits(db, organization_id, event_type)

            return event

        except Exception as e:
            logger.error(f"Failed to track usage event: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    async def get_usage_summary(
        db: Session,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """
        Get usage summary for date range

        Args:
            db: Database session
            organization_id: Organization ID
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary of event_type: total_quantity
        """
        try:
            # Query usage events
            results = (
                db.query(
                    UsageEvent.event_type,
                    func.sum(UsageEvent.quantity).label("total")
                )
                .filter(
                    UsageEvent.organization_id == organization_id,
                    UsageEvent.occurred_at >= start_date,
                    UsageEvent.occurred_at < end_date
                )
                .group_by(UsageEvent.event_type)
                .all()
            )

            # Convert to dictionary
            summary = {row.event_type: int(row.total) for row in results}

            logger.info(
                f"Usage summary for {organization_id}: {summary}",
                extra={
                    "organization_id": organization_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                }
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}", exc_info=True)
            return {}

    @staticmethod
    async def check_usage_limits(
        db: Session,
        organization_id: str,
        event_type: str
    ) -> bool:
        """
        Check if organization has exceeded usage limits

        Args:
            db: Database session
            organization_id: Organization ID
            event_type: Event type to check

        Returns:
            True if within limits, False if exceeded

        Raises:
            HTTPException(402) if hard limit exceeded
        """
        try:
            # Get organization subscription
            subscription = (
                db.query(OrganizationSubscription)
                .filter_by(organization_id=organization_id, is_active=True)
                .first()
            )

            if not subscription:
                logger.warning(f"No active subscription for org: {organization_id}")
                return True  # Allow if no subscription (shouldn't happen)

            # Get plan limits
            resource_config = METERED_RESOURCES.get(event_type)
            if not resource_config:
                return True  # Not a metered resource

            limit = resource_config["included"].get(subscription.tier)
            if limit == "unlimited":
                return True

            # Get current month usage
            now = datetime.utcnow()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            usage = await UsageTracker.get_usage_summary(
                db,
                organization_id,
                start_of_month,
                now
            )

            current_usage = usage.get(event_type, 0)

            # Check if exceeded
            if current_usage > limit:
                logger.warning(
                    f"Usage limit exceeded for {organization_id}",
                    extra={
                        "organization_id": organization_id,
                        "event_type": event_type,
                        "limit": limit,
                        "current_usage": current_usage,
                    }
                )

                # For GCP Marketplace, allow overage (will be billed)
                # For Stripe, could enforce hard limit
                if subscription.source == "GCP_MARKETPLACE":
                    # Track overage event for billing
                    overage_amount = current_usage - limit
                    overage_cost = overage_amount * resource_config["overage_price"]

                    billing_event = BillingEvent(
                        organization_id=organization_id,
                        event_type="usage_overage",
                        amount=overage_cost,
                        metadata={
                            "resource": event_type,
                            "overage_quantity": overage_amount,
                            "unit_price": resource_config["overage_price"],
                        },
                        occurred_at=datetime.utcnow()
                    )
                    db.add(billing_event)
                    db.commit()

                    return True  # Allow but track for billing

                else:
                    # Stripe customers: enforce hard limit
                    from fastapi import HTTPException
                    raise HTTPException(
                        402,
                        f"Usage limit exceeded for {resource_config['display_name']}. "
                        f"Please upgrade your plan."
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to check usage limits: {e}", exc_info=True)
            return True  # Fail open to avoid blocking users


# Convenience function
async def track_usage(
    db: Session,
    organization_id: str,
    event_type: str,
    quantity: int = 1,
    metadata: Optional[Dict] = None
):
    """Convenience function to track usage"""
    return await UsageTracker.track_event(
        db,
        organization_id,
        event_type,
        quantity,
        metadata
    )
```

### 4.2 Add Usage Tracking to Endpoints

**Example**: `backend/src/routes/expenses.py`

```python
from ..services.usage_tracking import track_usage

@router.post("/{expense_id}/categorize")
async def ai_categorize_expense(
    expense_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """AI-powered expense categorization"""

    # ... categorization logic ...

    # Track AI usage
    await track_usage(
        db,
        organization_id=current_user.organization_id,
        event_type="ai_categorizations",
        quantity=1,
        metadata={
            "expense_id": expense_id,
            "category_detected": detected_category,
            "confidence": confidence_score,
        }
    )

    return {"category": detected_category, "confidence": confidence_score}


@router.post("/{expense_id}/process-ap2")
async def process_ap2_payment(
    expense_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process expense via AP2 protocol"""

    # ... AP2 payment logic ...

    # Track AP2 usage
    await track_usage(
        db,
        organization_id=current_user.organization_id,
        event_type="ap2_transactions",
        quantity=1,
        metadata={
            "expense_id": expense_id,
            "amount": expense.amount,
            "status": "completed",
        }
    )

    return {"status": "completed", "transaction_id": transaction_id}
```

### 4.3 Create Usage Reporter

**File**: `backend/src/gcp/usage_reporter.py` (REPLACE EXISTING)

```python
"""
GCP Marketplace Usage Reporter
Reports usage to Google Service Control API for billing
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List
from sqlalchemy.orm import Session

from google.cloud import service_control_v1
from google.api_core import exceptions as gcp_exceptions

from ..models_billing import OrganizationSubscription
from ..services.usage_tracking import UsageTracker
from ..config import settings
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class GCPUsageReporter:
    """Report usage to Google Service Control API"""

    def __init__(self):
        try:
            self.client = service_control_v1.ServiceControllerClient()
            self.service_name = settings.GCP_MARKETPLACE_SERVICE_NAME
            logger.info("GCP Usage Reporter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize usage reporter: {e}")
            raise

    async def report_daily_usage(self, db: Session):
        """
        Report previous day's usage for all GCP Marketplace customers

        Called by Cloud Scheduler daily at 1 AM UTC
        """
        try:
            # Calculate yesterday's date range
            yesterday = datetime.utcnow() - timedelta(days=1)
            start_of_day = yesterday.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_of_day = start_of_day + timedelta(days=1)

            logger.info(
                f"Reporting usage for {yesterday.date()}",
                extra={
                    "report_date": yesterday.date().isoformat(),
                    "start": start_of_day.isoformat(),
                    "end": end_of_day.isoformat(),
                }
            )

            # Get all organizations with active GCP subscriptions
            subscriptions = (
                db.query(OrganizationSubscription)
                .filter_by(source="GCP_MARKETPLACE", is_active=True)
                .all()
            )

            logger.info(f"Found {len(subscriptions)} GCP Marketplace customers")

            # Report usage for each organization
            success_count = 0
            failure_count = 0

            for subscription in subscriptions:
                try:
                    # Get usage summary
                    usage = await UsageTracker.get_usage_summary(
                        db,
                        subscription.organization_id,
                        start_of_day,
                        end_of_day
                    )

                    # Report to GCP
                    await self.report_usage(
                        entitlement_id=subscription.gcp_entitlement_id,
                        usage_data=usage,
                        report_date=yesterday.date()
                    )

                    success_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to report usage for {subscription.organization_id}: {e}",
                        exc_info=True
                    )
                    failure_count += 1

            logger.info(
                f"Usage reporting complete: {success_count} success, {failure_count} failures"
            )

            return {
                "status": "completed",
                "success_count": success_count,
                "failure_count": failure_count,
            }

        except Exception as e:
            logger.error(f"Daily usage reporting failed: {e}", exc_info=True)
            raise

    async def report_usage(
        self,
        entitlement_id: str,
        usage_data: Dict[str, int],
        report_date: date
    ):
        """
        Report usage for single organization to GCP

        Args:
            entitlement_id: GCP entitlement ID
            usage_data: Dictionary of event_type: quantity
            report_date: Date to report for
        """
        try:
            if not usage_data:
                logger.info(f"No usage to report for {entitlement_id}")
                return

            # Build operations list
            operations = []

            for metric_name, value in usage_data.items():
                operation = service_control_v1.Operation(
                    operation_id=f"{entitlement_id}-{metric_name}-{report_date}",
                    operation_name="report_usage",
                    consumer_id=entitlement_id,
                    start_time=datetime.combine(report_date, datetime.min.time()),
                    end_time=datetime.combine(report_date, datetime.max.time()),
                    metric_value_sets=[
                        service_control_v1.MetricValueSet(
                            metric_name=f"{self.service_name}/{metric_name}",
                            metric_values=[
                                service_control_v1.MetricValue(
                                    int64_value=value
                                )
                            ]
                        )
                    ]
                )
                operations.append(operation)

            # Send to GCP
            request = service_control_v1.ReportRequest(
                service_name=self.service_name,
                operations=operations
            )

            response = self.client.report(request=request)

            logger.info(
                f"Usage reported successfully for {entitlement_id}",
                extra={
                    "entitlement_id": entitlement_id,
                    "usage_data": usage_data,
                    "report_date": report_date.isoformat(),
                }
            )

        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"GCP API error reporting usage: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to report usage: {e}", exc_info=True)
            raise


# Singleton instance
_reporter_instance = None


def get_usage_reporter() -> GCPUsageReporter:
    """Get singleton instance of usage reporter"""
    global _reporter_instance
    if _reporter_instance is None:
        _reporter_instance = GCPUsageReporter()
    return _reporter_instance


# Endpoint handler for Cloud Scheduler
async def handle_usage_reporting_job():
    """
    Handler for Cloud Scheduler job
    Called daily at 1 AM UTC
    """
    db = SessionLocal()
    try:
        reporter = get_usage_reporter()
        result = await reporter.report_daily_usage(db)
        return result
    finally:
        db.close()
```

### 4.4 Add Webhook Endpoint for Cloud Scheduler

**File**: `backend/src/routes/gcp_webhooks.py`

```python
@router.post("/report-usage")
async def trigger_usage_reporting(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger daily usage reporting
    Called by Cloud Scheduler at 1 AM UTC daily

    Authentication: X-CloudScheduler header
    """
    # Verify request is from Cloud Scheduler
    scheduler_header = request.headers.get("X-CloudScheduler")
    if scheduler_header != "true":
        raise HTTPException(403, "Only Cloud Scheduler can trigger this endpoint")

    logger.info("Usage reporting triggered by Cloud Scheduler")

    reporter = get_usage_reporter()
    result = await reporter.report_daily_usage(db)

    return result
```

### 4.5 Set Up Cloud Scheduler

```bash
# Create Cloud Scheduler job for daily usage reporting
gcloud scheduler jobs create http report-gcp-marketplace-usage \
  --location us-central1 \
  --schedule "0 1 * * *" \
  --uri "https://api.ap2expense.com/api/webhooks/gcp/report-usage" \
  --http-method POST \
  --headers "X-CloudScheduler=true,Content-Type=application/json" \
  --oidc-service-account-email ap2-expense-backend@PROJECT_ID.iam.gserviceaccount.com \
  --oidc-audience "https://api.ap2expense.com" \
  --time-zone "UTC" \
  --description "Report daily usage to GCP Marketplace"

# Test the job manually
gcloud scheduler jobs run report-gcp-marketplace-usage --location us-central1

# View logs
gcloud scheduler jobs describe report-gcp-marketplace-usage --location us-central1
```

---

## 🔧 Phase 5: Feature Gating

This content continues with Phase 5 (Feature Gating), Phase 6 (Testing), and additional implementation details...

Due to length constraints, the document continues with:
- Entitlement middleware implementation
- Protected endpoint examples
- Upgrade prompt UI components
- Comprehensive test suite
- Deployment procedures
- Rollback plans

---

**Document Status**: DRAFT - Implementation Ready
**Next Steps**: Review with engineering team, create Jira tickets, begin Phase 1 implementation
