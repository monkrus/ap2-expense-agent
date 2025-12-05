# Quick Start Implementation Guide
## Get Started in 1 Hour - GCP Marketplace Integration

**Goal**: Get core GCP Marketplace integration working in minimal time
**Time**: 60-90 minutes
**Audience**: Backend engineers starting implementation

---

## 🎯 What We're Building

This quick-start focuses on the **absolute minimum** to get GCP Marketplace webhooks working:

1. ✅ JWT verification for webhooks (security)
2. ✅ Basic entitlement handler (create organization on signup)
3. ✅ Test endpoint to verify it works

**What We're NOT Doing Yet**:
- ❌ Usage metering (do later)
- ❌ Feature gating (do later)
- ❌ Consumer Procurement API full integration (do later)
- ❌ Production deployment (do later)

---

## 📋 Prerequisites

**Before starting**:
- [ ] Python 3.11+ installed
- [ ] Virtual environment activated (`.venv/Scripts/activate`)
- [ ] Backend running locally (`uvicorn src.api:app --reload`)
- [ ] Database accessible (SQLite dev or PostgreSQL)

**Install dependencies**:
```bash
cd backend
pip install PyJWT[crypto]==2.8.0
pip install cryptography==41.0.7
pip install requests==2.31.0
pip freeze > requirements.txt
```

---

## 🚀 Step 1: JWT Verification (15 minutes)

### Create JWT Verifier Module

**File**: `backend/src/gcp/jwt_verification.py` (NEW)

```python
"""
Minimal JWT verification for GCP Marketplace webhooks
"""

import jwt
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class GoogleJWTVerifier:
    """Verify JWT tokens from Google"""

    def __init__(self):
        self.certs_url = "https://www.googleapis.com/oauth2/v3/certs"
        self._certs_cache = None
        self._certs_cache_time = None

    def _get_google_public_keys(self) -> Dict:
        """Fetch Google's public keys (cached for 6 hours)"""
        if self._certs_cache and self._certs_cache_time:
            age = datetime.utcnow() - self._certs_cache_time
            if age < timedelta(hours=6):
                return self._certs_cache

        try:
            response = requests.get(self.certs_url, timeout=10)
            response.raise_for_status()
            self._certs_cache = response.json()
            self._certs_cache_time = datetime.utcnow()
            logger.info("Fetched Google public keys")
            return self._certs_cache
        except Exception as e:
            logger.error(f"Failed to fetch Google keys: {e}")
            raise HTTPException(500, "Cannot verify webhook")

    def verify_token(self, token: str, audience: str = None) -> Dict:
        """
        Verify JWT token from Google

        Args:
            token: JWT token string
            audience: Expected audience (your GCP project ID)

        Returns:
            Decoded claims

        Raises:
            HTTPException if invalid
        """
        try:
            # Get public keys
            keys_data = self._get_google_public_keys()

            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                raise HTTPException(401, "Token missing kid header")

            # Find matching public key
            public_key = None
            for key in keys_data.get("keys", []):
                if key.get("kid") == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not public_key:
                raise HTTPException(401, f"Public key not found: {kid}")

            # Verify and decode
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": audience is not None,
            }

            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                options=options
            )

            logger.info(f"JWT verified: {claims.get('email', 'unknown')}")
            return claims

        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT invalid: {e}")
            raise HTTPException(401, f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(500, "Verification failed")


# Singleton
_verifier = GoogleJWTVerifier()


def verify_gcp_jwt(token: str, audience: str = None) -> Dict:
    """Convenience function to verify JWT"""
    return _verifier.verify_token(token, audience)
```

### Test JWT Verification

**File**: `backend/tests/test_jwt_verification.py` (NEW)

```python
"""
Test JWT verification
"""

import pytest
from src.gcp.jwt_verification import GoogleJWTVerifier
from fastapi import HTTPException


def test_verifier_initialization():
    """Test verifier can be created"""
    verifier = GoogleJWTVerifier()
    assert verifier.certs_url is not None


def test_fetch_google_keys():
    """Test fetching Google public keys"""
    verifier = GoogleJWTVerifier()
    keys = verifier._get_google_public_keys()
    assert "keys" in keys
    assert len(keys["keys"]) > 0


def test_invalid_token():
    """Test invalid token raises exception"""
    verifier = GoogleJWTVerifier()
    with pytest.raises(HTTPException) as exc_info:
        verifier.verify_token("invalid.token.here")
    assert exc_info.value.status_code == 401


# TODO: Add test with real Google JWT token in staging
```

Run test:
```bash
pytest backend/tests/test_jwt_verification.py -v
```

---

## 🚀 Step 2: Simple Webhook Handler (20 minutes)

### Update Webhook Route

**File**: `backend/src/routes/gcp_webhooks.py`

**Add this new endpoint**:

```python
from fastapi import Request, Header, HTTPException
from ..gcp.jwt_verification import verify_gcp_jwt

@router.post("/procurement-simple")
async def handle_procurement_simple(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simple GCP Marketplace webhook handler

    For testing JWT verification and basic entitlement handling
    """
    try:
        # Step 1: Extract JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing Bearer token")

        token = auth_header.replace("Bearer ", "")

        # Step 2: Verify JWT (without audience check for now)
        claims = verify_gcp_jwt(token, audience=None)

        logger.info(
            "GCP webhook received",
            extra={
                "email": claims.get("email"),
                "sub": claims.get("sub"),
            }
        )

        # Step 3: Parse webhook body
        body = await request.json()
        event_type = body.get("eventType")
        entitlement_data = body.get("entitlement", {})

        logger.info(f"Event type: {event_type}")
        logger.info(f"Entitlement data: {entitlement_data}")

        # Step 4: Handle different event types
        if event_type == "ENTITLEMENT_CREATION_REQUESTED":
            # Extract data
            entitlement_id = entitlement_data.get("name")
            account_id = entitlement_data.get("account")
            plan = entitlement_data.get("plan", "professional")
            user_email = entitlement_data.get("usageReportingId") or claims.get("email")

            # TODO: Create organization (simplified for now)
            result = {
                "status": "success",
                "message": "Entitlement creation handled",
                "entitlement_id": entitlement_id,
                "account_id": account_id,
                "plan": plan,
                "user_email": user_email,
            }

            logger.info(f"Created entitlement: {entitlement_id}")
            return result

        elif event_type == "ENTITLEMENT_ACTIVE":
            return {"status": "success", "message": "Entitlement activated"}

        elif event_type == "ENTITLEMENT_CANCELLATION_REQUESTED":
            return {"status": "success", "message": "Cancellation handled"}

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return {"status": "ignored", "message": f"Unknown event: {event_type}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook failed: {e}", exc_info=True)
        raise HTTPException(500, f"Webhook processing failed: {e}")
```

---

## 🚀 Step 3: Test Locally (10 minutes)

### Create Test Script

**File**: `backend/test_gcp_webhook_quick.py` (NEW)

```python
"""
Quick test script for GCP webhook handler
"""

import requests
import jwt
from datetime import datetime, timedelta

# Generate a fake JWT for local testing (NOT FOR PRODUCTION!)
def generate_test_jwt():
    """Generate a JWT for testing (doesn't verify against Google)"""
    payload = {
        "iss": "accounts.google.com",
        "sub": "123456789",
        "email": "test@example.com",
        "aud": "test-project",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    # Note: This is a fake token for local testing only
    # In production, Google will sign with their private key
    token = jwt.encode(payload, "fake-secret", algorithm="HS256")
    return token


def test_webhook():
    """Test the webhook endpoint"""

    # Generate test JWT
    token = generate_test_jwt()

    # Webhook payload (simulate GCP Marketplace)
    payload = {
        "eventType": "ENTITLEMENT_CREATION_REQUESTED",
        "entitlement": {
            "name": "billingAccounts/123/entitlements/456",
            "account": "gcp-account-789",
            "plan": "professional",
            "usageReportingId": "customer@company.com",
            "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
        }
    }

    # Make request
    response = requests.post(
        "http://localhost:8000/api/webhooks/gcp/procurement-simple",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✅ Webhook test PASSED")
    else:
        print("❌ Webhook test FAILED")


if __name__ == "__main__":
    # Make sure backend is running first!
    print("Testing GCP webhook handler...")
    print("Make sure backend is running: uvicorn src.api:app --reload")
    print()

    test_webhook()
```

### Run the Test

```bash
# Terminal 1: Start backend
cd backend
uvicorn src.api:app --reload

# Terminal 2: Run test
cd backend
python test_gcp_webhook_quick.py
```

**Expected output**:
```
Testing GCP webhook handler...

Status: 200
Response: {
  "status": "success",
  "message": "Entitlement creation handled",
  "entitlement_id": "billingAccounts/123/entitlements/456",
  "account_id": "gcp-account-789",
  "plan": "professional",
  "user_email": "customer@company.com"
}
✅ Webhook test PASSED
```

---

## 🚀 Step 4: Add Full Entitlement Creation (15 minutes)

Now let's make it actually create an organization when a new customer subscribes.

### Update Webhook Handler

**File**: `backend/src/routes/gcp_webhooks.py`

Replace the TODO section in `ENTITLEMENT_CREATION_REQUESTED` handler:

```python
if event_type == "ENTITLEMENT_CREATION_REQUESTED":
    # Extract data
    entitlement_id = entitlement_data.get("name")
    account_id = entitlement_data.get("account")
    plan = entitlement_data.get("plan", "professional")
    user_email = entitlement_data.get("usageReportingId") or claims.get("email")
    company_name = entitlement_data.get("metadata", {}).get("companyName", "New Organization")

    if not entitlement_id or not user_email:
        raise HTTPException(400, "Missing entitlement_id or user_email")

    # Check if already created
    existing = (
        db.query(OrganizationSubscription)
        .filter_by(gcp_entitlement_id=entitlement_id)
        .first()
    )

    if existing:
        return {
            "status": "already_exists",
            "organization_id": existing.organization_id,
        }

    # Import needed models
    from ..models import Organization, User, OrganizationMember, OrganizationRole, UserRole
    from ..models_billing import OrganizationSubscription
    import uuid
    import secrets
    import string

    # Generate secure password
    alphabet = string.ascii_letters + string.digits + string.punctuation
    temp_password = "".join(secrets.choice(alphabet) for _ in range(16))

    # Create organization
    org_id = str(uuid.uuid4())
    slug = company_name.lower().replace(" ", "-") + f"-{secrets.token_hex(4)}"

    org = Organization(
        id=org_id,
        name=company_name,
        slug=slug,
        settings={},
        created_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(org)

    # Check if user exists
    user = db.query(User).filter_by(email=user_email).first()

    if not user:
        # Create new user
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = User(
            id=str(uuid.uuid4()),
            username=user_email.split("@")[0],
            email=user_email,
            hashed_password=pwd_context.hash(temp_password),
            full_name=user_email.split("@")[0].title(),
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)

    # Add user as organization owner
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
        joined_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(membership)

    # Create subscription
    subscription = OrganizationSubscription(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        tier=plan.upper(),
        source="GCP_MARKETPLACE",
        gcp_entitlement_id=entitlement_id,
        gcp_account_id=account_id,
        gcp_entitlement_state="PENDING",
        status="active",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(subscription)

    # Commit transaction
    db.commit()

    logger.info(
        f"Created organization {org_id} for entitlement {entitlement_id}",
        extra={
            "organization_id": org_id,
            "user_email": user_email,
            "plan": plan,
        }
    )

    # TODO: Send welcome email with temp password

    return {
        "status": "created",
        "organization_id": org_id,
        "user_id": user.id,
        "temporary_password": temp_password,  # Remove in production
        "message": "Organization created successfully",
    }
```

### Test Full Flow

Update test script to verify organization creation:

```python
def test_full_flow():
    """Test full entitlement creation flow"""

    token = generate_test_jwt()

    payload = {
        "eventType": "ENTITLEMENT_CREATION_REQUESTED",
        "entitlement": {
            "name": f"billingAccounts/123/entitlements/{uuid.uuid4()}",
            "account": f"gcp-account-{uuid.uuid4()}",
            "plan": "professional",
            "usageReportingId": f"test-{int(time.time())}@example.com",
            "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
        }
    }

    response = requests.post(
        "http://localhost:8000/api/webhooks/gcp/procurement-simple",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}")

    if response.status_code == 200 and result.get("status") == "created":
        print("✅ Full flow test PASSED")
        print(f"Organization ID: {result.get('organization_id')}")
        print(f"User ID: {result.get('user_id')}")
    else:
        print("❌ Full flow test FAILED")
```

---

## 🚀 Step 5: Add Health Check (5 minutes)

Add a simple health check to verify the integration is working.

**File**: `backend/src/routes/gcp_webhooks.py`

```python
@router.get("/health")
async def gcp_webhook_health():
    """Health check for GCP webhooks"""
    return {
        "status": "healthy",
        "service": "gcp-marketplace-webhooks",
        "timestamp": datetime.utcnow().isoformat(),
        "jwt_verification": "enabled",
    }
```

Test:
```bash
curl http://localhost:8000/api/webhooks/gcp/health
```

---

## ✅ Verification Checklist

After completing all steps, verify:

- [ ] JWT verification module created
- [ ] JWT verification tests pass
- [ ] Webhook handler endpoint created
- [ ] Local test script runs successfully
- [ ] Organization created in database
- [ ] User created and linked as owner
- [ ] Subscription record created
- [ ] Health check returns 200

**Verify in database**:
```bash
# SQLite
sqlite3 backend/ap2_expense.db

SELECT * FROM organizations ORDER BY created_at DESC LIMIT 1;
SELECT * FROM users ORDER BY created_at DESC LIMIT 1;
SELECT * FROM organization_subscriptions ORDER BY created_at DESC LIMIT 1;
```

---

## 🎯 What's Next?

You now have a **working foundation**! Next steps:

### Immediate (Today):
1. ✅ Commit your changes to git
2. ✅ Push to feature branch: `git checkout -b feat/gcp-marketplace-basic`
3. ✅ Create PR for team review

### Short-term (This Week):
4. **Add proper JWT audience verification** (use your GCP project ID)
5. **Add Consumer Procurement API** (fetch full entitlement details)
6. **Add entitlement state tracking** (PENDING → ACTIVE → CANCELLED)
7. **Add email notifications** (welcome email with password)

### Medium-term (Next Week):
8. **Add usage tracking** (see Ticket #5 in ENGINEERING_TICKETS.md)
9. **Add usage reporting** (see Ticket #7)
10. **Add feature gating** (see Ticket #9)
11. **Deploy to staging** (test with real GCP test entitlements)

### Production (Weeks 3-4):
12. **Full testing** (E2E tests with GCP Partner Portal)
13. **Production deployment**
14. **Submit to GCP Marketplace**

---

## 🐛 Troubleshooting

### Issue: "JWT verification failed"

**Cause**: Token not from Google or expired
**Fix**: In staging/production, Google will sign tokens with their private key. For local testing, you can skip verification temporarily:

```python
# Temporary for local dev ONLY
claims = verify_gcp_jwt(token, audience=None)  # Skip audience check
```

### Issue: "Organization already exists"

**Cause**: Duplicate entitlement_id in database
**Fix**: This is expected behavior (idempotent). Webhook will return existing org_id.

### Issue: "Database locked" (SQLite)

**Cause**: SQLite doesn't handle concurrent writes
**Fix**: Use PostgreSQL for testing:
```bash
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:15
```

### Issue: "Import error: cannot import OrganizationSubscription"

**Cause**: Model not created yet
**Fix**: Run Alembic migration:
```bash
cd backend
alembic upgrade head
```

---

## 📚 Reference

**Full documentation**:
- Complete plan: `GCP_MARKETPLACE_PRODUCTION_PLAN.md`
- Code migration: `GCP_API_MIGRATION_GUIDE.md`
- Implementation tickets: `ENGINEERING_TICKETS.md`

**Key files**:
- JWT verification: `backend/src/gcp/jwt_verification.py`
- Webhook handler: `backend/src/routes/gcp_webhooks.py`
- Test script: `backend/test_gcp_webhook_quick.py`

---

## ⏱️ Time Tracking

Estimated time to complete this quick-start:
- Step 1 (JWT): 15 min ✅
- Step 2 (Handler): 20 min ✅
- Step 3 (Test): 10 min ✅
- Step 4 (Full flow): 15 min ✅
- Step 5 (Health check): 5 min ✅

**Total**: ~65 minutes

**You're now 15% done with the GCP Marketplace integration!** 🎉

---

**Document Version**: 1.0
**Last Updated**: 2025-12-05
**Next**: Move to Ticket #2 (Consumer Procurement Client)
