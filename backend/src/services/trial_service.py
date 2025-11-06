"""
Trial Management Service

Handles trial expiration, conversion, and notifications
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict
import logging

from ..models_billing import OrganizationSubscription, BillingTier, BillingEvent
from ..models import Organization, User, OrganizationMember
import uuid

logger = logging.getLogger(__name__)


class TrialService:
    """Service for managing trial subscriptions"""

    def __init__(self, db: Session):
        self.db = db

    def get_expiring_trials(self, days_before_expiry: int = 3) -> List[OrganizationSubscription]:
        """
        Get trials that will expire within the specified number of days

        Args:
            days_before_expiry: How many days before expiry to check (default: 3)

        Returns:
            List of subscriptions with expiring trials
        """
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days_before_expiry)

            subscriptions = self.db.query(OrganizationSubscription).filter(
                and_(
                    OrganizationSubscription.is_trial == True,
                    OrganizationSubscription.status == "active",
                    OrganizationSubscription.trial_end <= cutoff_date,
                    OrganizationSubscription.trial_end > datetime.utcnow()
                )
            ).all()

            return subscriptions

        except Exception as e:
            logger.error(f"Error getting expiring trials: {e}")
            return []

    def get_expired_trials(self) -> List[OrganizationSubscription]:
        """
        Get trials that have already expired

        Returns:
            List of subscriptions with expired trials
        """
        try:
            subscriptions = self.db.query(OrganizationSubscription).filter(
                and_(
                    OrganizationSubscription.is_trial == True,
                    OrganizationSubscription.status == "active",
                    OrganizationSubscription.trial_end <= datetime.utcnow()
                )
            ).all()

            return subscriptions

        except Exception as e:
            logger.error(f"Error getting expired trials: {e}")
            return []

    def convert_trial_to_paid(self, subscription_id: str) -> Dict:
        """
        Convert a trial subscription to a paid subscription

        Requires that the organization has a valid payment method (Stripe customer ID)

        Args:
            subscription_id: OrganizationSubscription ID

        Returns:
            Result dict with success status and details
        """
        try:
            subscription = self.db.query(OrganizationSubscription).filter(
                OrganizationSubscription.id == subscription_id
            ).first()

            if not subscription:
                return {"success": False, "error": "Subscription not found"}

            if not subscription.is_trial:
                return {"success": False, "error": "Subscription is not a trial"}

            organization = self.db.query(Organization).filter(
                Organization.id == subscription.organization_id
            ).first()

            if not organization:
                return {"success": False, "error": "Organization not found"}

            # Check if organization has payment method
            if not organization.stripe_customer_id and not subscription.gcp_entitlement_id:
                return {
                    "success": False,
                    "error": "No payment method on file",
                    "requires_payment": True
                }

            # Convert to paid subscription
            subscription.is_trial = False
            subscription.trial_end = None
            subscription.billing_period_start = datetime.utcnow()

            # Log event
            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:12]}",
                organization_id=organization.id,
                event_type="trial_converted",
                event_data={
                    "subscription_id": subscription_id,
                    "tier": subscription.tier_id,
                    "conversion_date": datetime.utcnow().isoformat()
                },
                status="success"
            )
            self.db.add(event)

            self.db.commit()

            logger.info(f"Successfully converted trial to paid for org {organization.id}")

            return {
                "success": True,
                "subscription_id": subscription_id,
                "organization_id": organization.id
            }

        except Exception as e:
            logger.error(f"Error converting trial to paid: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def suspend_expired_trial(self, subscription_id: str) -> Dict:
        """
        Suspend an expired trial subscription

        Args:
            subscription_id: OrganizationSubscription ID

        Returns:
            Result dict with success status
        """
        try:
            subscription = self.db.query(OrganizationSubscription).filter(
                OrganizationSubscription.id == subscription_id
            ).first()

            if not subscription:
                return {"success": False, "error": "Subscription not found"}

            # Mark as suspended
            subscription.status = "suspended"

            # Log event
            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:12]}",
                organization_id=subscription.organization_id,
                event_type="trial_expired",
                event_data={
                    "subscription_id": subscription_id,
                    "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None
                },
                status="success"
            )
            self.db.add(event)

            self.db.commit()

            logger.info(f"Suspended expired trial for subscription {subscription_id}")

            return {
                "success": True,
                "subscription_id": subscription_id,
                "organization_id": subscription.organization_id
            }

        except Exception as e:
            logger.error(f"Error suspending expired trial: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def send_trial_expiry_warning(self, subscription: OrganizationSubscription, days_remaining: int):
        """
        Send email notification about expiring trial

        Args:
            subscription: OrganizationSubscription object
            days_remaining: Number of days until trial expires
        """
        try:
            organization = self.db.query(Organization).filter(
                Organization.id == subscription.organization_id
            ).first()

            if not organization:
                logger.warning(f"Organization not found for subscription {subscription.id}")
                return

            # Get organization admins/owners
            admins = self.db.query(User).join(OrganizationMember).filter(
                and_(
                    OrganizationMember.organization_id == organization.id,
                    OrganizationMember.role.in_(["owner", "admin"])
                )
            ).all()

            tier = self.db.query(BillingTier).filter(
                BillingTier.id == subscription.tier_id
            ).first()

            tier_name = tier.tier_display_name if tier else "Unknown"

            for admin in admins:
                # TODO: Integrate with email service
                logger.info(
                    f"[TRIAL WARNING] Would send email to {admin.email}: "
                    f"Trial for {tier_name} expires in {days_remaining} days"
                )

            # Log event
            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:12]}",
                organization_id=organization.id,
                event_type="trial_expiry_warning",
                event_data={
                    "subscription_id": subscription.id,
                    "days_remaining": days_remaining,
                    "admins_notified": len(admins)
                },
                status="success"
            )
            self.db.add(event)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error sending trial expiry warning: {e}")

    def process_expiring_trials(self) -> Dict:
        """
        Process all expiring trials (send warnings)

        Returns:
            Summary of processing results
        """
        try:
            # Check trials expiring in 7, 3, and 1 day
            warnings_sent = 0

            for days in [7, 3, 1]:
                expiring = self.get_expiring_trials(days_before_expiry=days)

                for subscription in expiring:
                    # Check if we already sent warning for this day
                    recent_warning = self.db.query(BillingEvent).filter(
                        and_(
                            BillingEvent.organization_id == subscription.organization_id,
                            BillingEvent.event_type == "trial_expiry_warning",
                            BillingEvent.event_data["days_remaining"].astext == str(days),
                            BillingEvent.created_at >= datetime.utcnow() - timedelta(hours=24)
                        )
                    ).first()

                    if not recent_warning:
                        self.send_trial_expiry_warning(subscription, days)
                        warnings_sent += 1

            return {
                "success": True,
                "warnings_sent": warnings_sent
            }

        except Exception as e:
            logger.error(f"Error processing expiring trials: {e}")
            return {"success": False, "error": str(e)}

    def process_expired_trials(self) -> Dict:
        """
        Process all expired trials (suspend or convert)

        Returns:
            Summary of processing results
        """
        try:
            expired = self.get_expired_trials()

            suspended_count = 0
            converted_count = 0
            errors = []

            for subscription in expired:
                organization = self.db.query(Organization).filter(
                    Organization.id == subscription.organization_id
                ).first()

                # Check if organization has payment method
                has_payment_method = (
                    organization and
                    (organization.stripe_customer_id or subscription.gcp_entitlement_id)
                )

                if has_payment_method:
                    # Try to convert to paid
                    result = self.convert_trial_to_paid(subscription.id)
                    if result["success"]:
                        converted_count += 1
                    else:
                        errors.append({
                            "subscription_id": subscription.id,
                            "error": result.get("error")
                        })
                else:
                    # Suspend the subscription
                    result = self.suspend_expired_trial(subscription.id)
                    if result["success"]:
                        suspended_count += 1
                    else:
                        errors.append({
                            "subscription_id": subscription.id,
                            "error": result.get("error")
                        })

            return {
                "success": True,
                "expired_trials_processed": len(expired),
                "converted": converted_count,
                "suspended": suspended_count,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error processing expired trials: {e}")
            return {"success": False, "error": str(e)}
