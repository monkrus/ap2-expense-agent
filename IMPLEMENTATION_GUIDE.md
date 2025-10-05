# AP2 Expense Agent - Complete Implementation Guide

## Prerequisites Completed ✅
- Official AP2 SDK cloned to: `C:\Users\robot\Desktop\ap2-sdk`
- Test suite passing (34/35 tests)
- Basic auth/authorization complete
- Custom AP2 implementation exists (needs replacement)

---

## Phase 1: Official AP2 SDK Integration (Week 1-2)

### Step 1.1: Install AP2 SDK

```bash
cd backend
# Install using uv (recommended by AP2 team)
pip install uv
uv pip install git+https://github.com/google-agentic-commerce/AP2.git@main

# Or add to requirements.txt
echo "git+https://github.com/google-agentic-commerce/AP2.git@main" >> requirements.txt
pip install -r requirements.txt
```

### Step 1.2: Study Key AP2 Files

**Essential files to review:**
```
ap2-sdk/
├── src/ap2/types/          # Core protocol types
├── samples/python/src/
│   ├── common/
│   │   ├── a2a_extension_utils.py    # A2A protocol helpers
│   │   ├── a2a_message_builder.py    # Message construction
│   │   ├── payment_remote_a2a_client.py  # Payment agent client
│   │   └── server.py                 # Agent server implementation
│   └── scenarios/          # Example implementations
```

**Key Python modules to import:**
```python
from ap2.types import IntentMandate, CartMandate, PaymentMandate
from samples.python.src.common.a2a_message_builder import A2AMessageBuilder
from samples.python.src.common.payment_remote_a2a_client import PaymentRemoteA2AClient
```

### Step 1.3: Create New AP2 Integration Module

**File: `backend/src/ap2_official/__init__.py`**
```python
"""
Official AP2 SDK Integration
Replaces custom implementation in agent.py
"""
from .mandates import AP2MandateManager
from .agents import ShoppingAgent, MerchantAgent, PaymentProcessorAgent
from .transport import A2ATransport

__all__ = ['AP2MandateManager', 'ShoppingAgent', 'MerchantAgent', 'PaymentProcessorAgent', 'A2ATransport']
```

### Step 1.4: Create Database Models for AP2

**File: `backend/alembic/versions/004_add_ap2_mandate_tables.py`**
```python
"""Add AP2 mandate storage tables

Revision ID: 004_add_ap2_mandates
Revises: bd28e09de1fa
Create Date: 2025-10-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004_add_ap2_mandates'
down_revision = 'bd28e09de1fa'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Intent Mandates table
    op.create_table(
        'intent_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('constraints', sa.JSON, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('expiration', sa.DateTime, nullable=False),
        sa.Column('signature', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Cart Mandates table
    op.create_table(
        'cart_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('intent_mandate_id', sa.String(255), sa.ForeignKey('intent_mandates.id'), nullable=False),
        sa.Column('items', sa.JSON, nullable=False),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('merchant', sa.String(255), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('user_signature', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Payment Mandates table
    op.create_table(
        'payment_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('cart_mandate_id', sa.String(255), sa.ForeignKey('cart_mandates.id'), nullable=False),
        sa.Column('payment_method', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('audit_trail', sa.JSON, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('payment_processor_response', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Add indexes
    op.create_index('ix_intent_mandates_user_id', 'intent_mandates', ['user_id'])
    op.create_index('ix_intent_mandates_status', 'intent_mandates', ['status'])
    op.create_index('ix_cart_mandates_intent_id', 'cart_mandates', ['intent_mandate_id'])
    op.create_index('ix_payment_mandates_cart_id', 'payment_mandates', ['cart_mandate_id'])
    op.create_index('ix_payment_mandates_status', 'payment_mandates', ['status'])

def downgrade() -> None:
    op.drop_table('payment_mandates')
    op.drop_table('cart_mandates')
    op.drop_table('intent_mandates')
```

### Step 1.5: Update Models

**File: `backend/src/models.py` (add to existing file)**
```python
class IntentMandate(Base):
    """AP2 Intent Mandate - User's authorization constraints"""
    __tablename__ = "intent_mandates"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    constraints = Column(JSON, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    expiration = Column(DateTime, nullable=False)
    signature = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="intent_mandates")
    cart_mandates = relationship("CartMandate", back_populates="intent_mandate")

class CartMandate(Base):
    """AP2 Cart Mandate - Specific items for approval"""
    __tablename__ = "cart_mandates"

    id = Column(String(255), primary_key=True)
    intent_mandate_id = Column(String(255), ForeignKey("intent_mandates.id"), nullable=False)
    items = Column(JSON, nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String(255), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    user_signature = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    intent_mandate = relationship("IntentMandate", back_populates="cart_mandates")
    payment_mandates = relationship("PaymentMandate", back_populates="cart_mandate")

class PaymentMandate(Base):
    """AP2 Payment Mandate - Payment execution record"""
    __tablename__ = "payment_mandates"

    id = Column(String(255), primary_key=True)
    cart_mandate_id = Column(String(255), ForeignKey("cart_mandates.id"), nullable=False)
    payment_method = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    audit_trail = Column(JSON, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    payment_processor_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    cart_mandate = relationship("CartMandate", back_populates="payment_mandates")

# Update User model to add relationship
User.intent_mandates = relationship("IntentMandate", back_populates="user")
```

---

## Phase 2: Google Cloud Platform Setup (Week 3-4)

### Step 2.1: Create GCP Project

```bash
# Install Google Cloud SDK
# Windows: Download from https://cloud.google.com/sdk/docs/install

# Initialize gcloud
gcloud init

# Create project
gcloud projects create ap2-expense-agent --name="AP2 Expense Management Agent"

# Set as default
gcloud config set project ap2-expense-agent

# Enable billing (must do via console)
# https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage-component.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  aiplatform.googleapis.com
```

### Step 2.2: Create Dockerfiles

**File: `Dockerfile.backend`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=2)"

# Run application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

**File: `Dockerfile.frontend`**
```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
```

**File: `nginx.conf`**
```nginx
user nginx;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;
    gzip on;

    server {
        listen 80;
        server_name _;

        root /usr/share/nginx/html;
        index index.html;

        # SPA routing
        location / {
            try_files $uri $uri/ /index.html;
        }

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### Step 2.3: Create Cloud Build Configuration

**File: `cloudbuild.yaml`**
```yaml
steps:
  # Build backend image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/ap2-expense-backend:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/ap2-expense-backend:latest'
      - '-f'
      - 'Dockerfile.backend'
      - '.'

  # Build frontend image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/ap2-expense-frontend:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/ap2-expense-frontend:latest'
      - '-f'
      - 'Dockerfile.frontend'
      - '.'

  # Push backend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ap2-expense-backend:$COMMIT_SHA']

  # Push frontend image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ap2-expense-frontend:$COMMIT_SHA']

  # Deploy backend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'ap2-expense-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/ap2-expense-backend:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'ENVIRONMENT=production'

  # Deploy frontend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'ap2-expense-frontend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/ap2-expense-frontend:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/ap2-expense-backend:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/ap2-expense-backend:latest'
  - 'gcr.io/$PROJECT_ID/ap2-expense-frontend:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/ap2-expense-frontend:latest'
```

---

## Phase 3: Stripe Payment Integration (Week 5-6)

### Step 3.1: Install Stripe SDK

```bash
cd backend
pip install stripe
echo "stripe==11.1.0" >> requirements.txt
```

### Step 3.2: Create Stripe Integration Module

**File: `backend/src/payments/__init__.py`**
```python
from .stripe_processor import StripePaymentProcessor
from .webhook_handler import StripeWebhookHandler

__all__ = ['StripePaymentProcessor', 'StripeWebhookHandler']
```

**File: `backend/src/payments/stripe_processor.py`**
```python
"""
Stripe Payment Processor Integration
Processes AP2 payment mandates through Stripe
"""
import stripe
from typing import Dict, Optional
from datetime import datetime
from ..config import settings
from ..models import PaymentMandate

stripe.api_key = settings.stripe_secret_key

class StripePaymentProcessor:
    """Process payments using Stripe with AP2 mandates"""

    async def process_payment_mandate(
        self,
        payment_mandate: PaymentMandate,
        amount: float,
        currency: str = "usd",
        customer_id: Optional[str] = None
    ) -> Dict:
        """
        Process payment using AP2 mandate through Stripe

        Args:
            payment_mandate: AP2 Payment Mandate
            amount: Amount in dollars
            currency: Currency code
            customer_id: Stripe customer ID

        Returns:
            Payment result with transaction details
        """
        try:
            # Create PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                metadata={
                    "ap2_payment_mandate_id": payment_mandate.id,
                    "ap2_cart_mandate_id": payment_mandate.cart_mandate_id,
                    "mandate_timestamp": payment_mandate.timestamp.isoformat()
                },
                confirm=True,
                automatic_payment_methods={"enabled": True}
            )

            return {
                "success": True,
                "transaction_id": payment_intent.id,
                "status": payment_intent.status,
                "amount": amount,
                "currency": currency,
                "created": datetime.fromtimestamp(payment_intent.created)
            }

        except stripe.error.CardError as e:
            return {
                "success": False,
                "error": "card_error",
                "message": str(e.user_message)
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": "stripe_error",
                "message": str(e)
            }

    async def create_setup_intent(self, customer_id: str) -> Dict:
        """Create SetupIntent for saving payment methods"""
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=["card"]
        )

        return {
            "client_secret": setup_intent.client_secret,
            "id": setup_intent.id
        }

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[float] = None
    ) -> Dict:
        """Refund a payment"""
        try:
            refund_params = {"payment_intent": transaction_id}
            if amount:
                refund_params["amount"] = int(amount * 100)

            refund = stripe.Refund.create(**refund_params)

            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
```

### Step 3.3: Create Webhook Handler

**File: `backend/src/payments/webhook_handler.py`**
```python
"""
Stripe Webhook Handler
Processes Stripe webhook events for payment status updates
"""
import stripe
from fastapi import Request, HTTPException
from typing import Dict
from ..config import settings
from ..models import PaymentMandate
from sqlalchemy.orm import Session

class StripeWebhookHandler:
    """Handle Stripe webhook events"""

    def __init__(self, db: Session):
        self.db = db

    async def handle_webhook(self, request: Request) -> Dict:
        """
        Process incoming Stripe webhook

        Args:
            request: FastAPI request object

        Returns:
            Processing result
        """
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle event types
        if event.type == 'payment_intent.succeeded':
            await self._handle_payment_success(event.data.object)
        elif event.type == 'payment_intent.payment_failed':
            await self._handle_payment_failed(event.data.object)
        elif event.type == 'charge.refunded':
            await self._handle_refund(event.data.object)

        return {"status": "success", "event_type": event.type}

    async def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        mandate_id = payment_intent.metadata.get('ap2_payment_mandate_id')

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = 'completed'
                mandate.payment_processor_response = {
                    "stripe_payment_intent_id": payment_intent.id,
                    "status": payment_intent.status,
                    "amount": payment_intent.amount / 100
                }
                self.db.commit()

    async def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        mandate_id = payment_intent.metadata.get('ap2_payment_mandate_id')

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = 'failed'
                mandate.payment_processor_response = {
                    "stripe_payment_intent_id": payment_intent.id,
                    "error": payment_intent.last_payment_error
                }
                self.db.commit()

    async def _handle_refund(self, charge):
        """Handle refund"""
        # Find mandate by charge ID and update status
        pass
```

### Step 3.4: Add Webhook Route

**File: `backend/src/routes/webhooks.py`**
```python
"""
Webhook endpoints for payment processors
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..payments.webhook_handler import StripeWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    handler = StripeWebhookHandler(db)
    result = await handler.handle_webhook(request)
    return result
```

---

## Quick Start Commands

```bash
# 1. Clone AP2 SDK (DONE)
cd /c/Users/robot/Desktop
git clone https://github.com/google-agentic-commerce/AP2.git ap2-sdk

# 2. Install AP2 in your project
cd /c/Users/robot/Desktop/ap2-expense-agent/backend
pip install git+https://github.com/google-agentic-commerce/AP2.git@main

# 3. Create database migration
alembic revision -m "Add AP2 mandate tables"
# (copy content from Step 1.4 above)
alembic upgrade head

# 4. Install Stripe
pip install stripe

# 5. Set up environment variables
# Add to .env:
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# 6. Test locally
uvicorn src.api:app --reload

# 7. Run tests
pytest tests/ -v
```

---

## Next Immediate Steps

1. **This Week:**
   - Study AP2 SDK examples in `/c/Users/robot/Desktop/ap2-sdk/samples/python`
   - Create AP2 database migration (Step 1.4)
   - Update models.py with mandate classes (Step 1.5)

2. **Next Week:**
   - Create Dockerfiles (Step 2.2)
   - Set up GCP project (Step 2.1)
   - Install Stripe SDK (Step 3.1)

3. **Weeks 3-4:**
   - Deploy to Cloud Run
   - Integrate Stripe payments
   - Test end-to-end

---

## Resources

- **AP2 SDK:** `/c/Users/robot/Desktop/ap2-sdk`
- **AP2 Docs:** https://ap2-protocol.org
- **GCP Docs:** https://cloud.google.com/run/docs
- **Stripe Docs:** https://stripe.com/docs
- **Your Roadmap:** `GOOGLE_CLOUD_MARKETPLACE_ROADMAP.md`

---

**Status:** AP2 SDK cloned ✅ | Ready to begin integration
**Next Task:** Create database migration for AP2 mandates
