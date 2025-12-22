"""
Webhook endpoints for payment processors
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..payments.webhook_handler import StripeWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events

    This endpoint receives events from Stripe for:
    - Payment success/failure
    - Refunds
    """
    handler = StripeWebhookHandler(db)
    result = await handler.handle_webhook(request)
    return result


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint"""
    return {"status": "ok", "service": "webhooks"}
