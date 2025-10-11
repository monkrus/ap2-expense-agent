"""
Billing service for usage tracking and Google Cloud Marketplace integration
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
import json
import requests
from ..models_billing import UsageMetric, BillingTier, OrganizationSubscription, BillingEvent
from ..models import Organization, Expense, User
import logging

logger = logging.getLogger(__name__)


class BillingService:
    """Service for managing billing, usage tracking, and marketplace integration"""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Usage Tracking
    # ========================================================================

    def track_api_call(self, organization_id: str, endpoint: str, method: str) -> None:
        """Track an API call for billing purposes"""
        try:
            # This is typically called from middleware
            # For now, we'll increment a counter in the current period
            period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

            # Try to find existing metric for today
            metric = self.db.query(UsageMetric).filter(
                and_(
                    UsageMetric.organization_id == organization_id,
                    UsageMetric.metric_type == "api_calls",
                    UsageMetric.period_start == period_start
                )
            ).first()

            if metric:
                metric.metric_value += 1
                metric.metadata = metric.metadata or {}
                metric.metadata[endpoint] = metric.metadata.get(endpoint, 0) + 1
            else:
                metric = UsageMetric(
                    id=f"metric_{uuid.uuid4().hex[:12]}",
                    organization_id=organization_id,
                    metric_type="api_calls",
                    metric_value=1,
                    unit="calls",
                    period_start=period_start,
                    period_end=period_end,
                    reported_to_gcp=False,
                    metadata={endpoint: 1}
                )
                self.db.add(metric)

            self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking API call: {e}")
            self.db.rollback()

    def track_storage_usage(self, organization_id: str, storage_bytes: int) -> None:
        """Track storage usage (e.g., receipt uploads)"""
        try:
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = period_start + timedelta(days=32)
            period_end = next_month.replace(day=1)

            storage_gb = storage_bytes / (1024 ** 3)

            metric = self.db.query(UsageMetric).filter(
                and_(
                    UsageMetric.organization_id == organization_id,
                    UsageMetric.metric_type == "storage_gb",
                    UsageMetric.period_start == period_start
                )
            ).first()

            if metric:
                metric.metric_value = storage_gb  # Current value, not cumulative
            else:
                metric = UsageMetric(
                    id=f"metric_{uuid.uuid4().hex[:12]}",
                    organization_id=organization_id,
                    metric_type="storage_gb",
                    metric_value=storage_gb,
                    unit="gb",
                    period_start=period_start,
                    period_end=period_end,
                    reported_to_gcp=False
                )
                self.db.add(metric)

            self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking storage usage: {e}")
            self.db.rollback()

    def track_active_users(self, organization_id: str) -> None:
        """Track active users for the current month"""
        try:
            period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = period_start + timedelta(days=32)
            period_end = next_month.replace(day=1)

            # Count active users in this organization
            from ..models import OrganizationMember
            active_count = self.db.query(func.count(OrganizationMember.id)).filter(
                OrganizationMember.organization_id == organization_id
            ).scalar()

            metric = self.db.query(UsageMetric).filter(
                and_(
                    UsageMetric.organization_id == organization_id,
                    UsageMetric.metric_type == "active_users",
                    UsageMetric.period_start == period_start
                )
            ).first()

            if metric:
                metric.metric_value = active_count
            else:
                metric = UsageMetric(
                    id=f"metric_{uuid.uuid4().hex[:12]}",
                    organization_id=organization_id,
                    metric_type="active_users",
                    metric_value=active_count,
                    unit="users",
                    period_start=period_start,
                    period_end=period_end,
                    reported_to_gcp=False
                )
                self.db.add(metric)

            self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking active users: {e}")
            self.db.rollback()

    def get_usage_summary(self, organization_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get usage summary for a date range"""
        metrics = self.db.query(UsageMetric).filter(
            and_(
                UsageMetric.organization_id == organization_id,
                UsageMetric.period_start >= start_date,
                UsageMetric.period_end <= end_date
            )
        ).all()

        summary = {
            "organization_id": organization_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "metrics": {}
        }

        for metric in metrics:
            metric_type = metric.metric_type
            if metric_type not in summary["metrics"]:
                summary["metrics"][metric_type] = {
                    "total": 0,
                    "unit": metric.unit,
                    "details": []
                }

            summary["metrics"][metric_type]["total"] += metric.metric_value
            summary["metrics"][metric_type]["details"].append({
                "period_start": metric.period_start.isoformat(),
                "period_end": metric.period_end.isoformat(),
                "value": metric.metric_value,
                "reported": metric.reported_to_gcp
            })

        return summary

    # ========================================================================
    # Billing Tiers
    # ========================================================================

    def create_billing_tiers(self) -> None:
        """Initialize default billing tiers"""
        tiers = [
            {
                "id": "tier_free",
                "tier_name": "free",
                "display_name": "Free Plan",
                "description": "Perfect for trying out the system",
                "base_price_monthly": 0.0,
                "limits": {
                    "api_calls": 1000,
                    "storage_gb": 1,
                    "active_users": 3,
                    "expenses_per_month": 50
                },
                "features": [
                    "Basic expense tracking",
                    "Email support",
                    "1GB storage",
                    "Up to 3 users"
                ]
            },
            {
                "id": "tier_starter",
                "tier_name": "starter",
                "display_name": "Starter Plan",
                "description": "For small teams getting started",
                "base_price_monthly": 29.0,
                "limits": {
                    "api_calls": 10000,
                    "storage_gb": 10,
                    "active_users": 10,
                    "expenses_per_month": 500
                },
                "overage_pricing": {
                    "api_calls": 0.01,  # $0.01 per 100 calls
                    "storage_gb": 0.50,
                    "active_users": 5.00
                },
                "features": [
                    "Everything in Free",
                    "AP2 protocol compliance",
                    "Complete audit trails",
                    "Priority email support",
                    "10GB storage",
                    "Up to 10 users"
                ]
            },
            {
                "id": "tier_professional",
                "tier_name": "professional",
                "display_name": "Professional Plan",
                "description": "For growing businesses",
                "base_price_monthly": 99.0,
                "limits": {
                    "api_calls": 50000,
                    "storage_gb": 50,
                    "active_users": 50,
                    "expenses_per_month": 5000
                },
                "overage_pricing": {
                    "api_calls": 0.008,
                    "storage_gb": 0.40,
                    "active_users": 4.00
                },
                "features": [
                    "Everything in Starter",
                    "Advanced reporting",
                    "Custom categories",
                    "API access",
                    "Phone support",
                    "50GB storage",
                    "Up to 50 users",
                    "SSO integration"
                ]
            },
            {
                "id": "tier_enterprise",
                "tier_name": "enterprise",
                "display_name": "Enterprise Plan",
                "description": "For large organizations",
                "base_price_monthly": 299.0,
                "limits": {
                    "api_calls": 1000000,
                    "storage_gb": 500,
                    "active_users": 1000,
                    "expenses_per_month": 100000
                },
                "features": [
                    "Everything in Professional",
                    "Unlimited expenses",
                    "Dedicated support",
                    "SLA guarantee",
                    "Custom integrations",
                    "500GB storage",
                    "Unlimited users",
                    "White-label option",
                    "Custom contract"
                ]
            }
        ]

        for tier_data in tiers:
            existing = self.db.query(BillingTier).filter(
                BillingTier.tier_name == tier_data["tier_name"]
            ).first()

            if not existing:
                tier = BillingTier(**tier_data)
                self.db.add(tier)

        self.db.commit()

    def get_billing_tiers(self, public_only: bool = True) -> List[Dict]:
        """Get available billing tiers"""
        query = self.db.query(BillingTier).filter(BillingTier.is_active == True)

        if public_only:
            query = query.filter(BillingTier.is_public == True)

        tiers = query.all()

        return [{
            "id": tier.id,
            "tier_name": tier.tier_name,
            "display_name": tier.display_name,
            "description": tier.description,
            "base_price_monthly": tier.base_price_monthly,
            "currency": tier.currency,
            "limits": tier.limits,
            "overage_pricing": tier.overage_pricing,
            "features": tier.features
        } for tier in tiers]

    # ========================================================================
    # Subscriptions
    # ========================================================================

    def create_subscription(
        self,
        organization_id: str,
        tier_name: str,
        gcp_account_id: Optional[str] = None,
        is_trial: bool = False
    ) -> Dict:
        """Create a subscription for an organization"""
        tier = self.db.query(BillingTier).filter(
            BillingTier.tier_name == tier_name
        ).first()

        if not tier:
            raise ValueError(f"Billing tier '{tier_name}' not found")

        # Check if subscription already exists
        existing = self.db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == organization_id
        ).first()

        if existing:
            raise ValueError(f"Subscription already exists for organization {organization_id}")

        now = datetime.utcnow()
        subscription = OrganizationSubscription(
            id=f"sub_{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            tier_id=tier.id,
            tier_name=tier.tier_name,
            gcp_account_id=gcp_account_id,
            status="active" if not is_trial else "trial",
            billing_period_start=now,
            billing_period_end=now + timedelta(days=30),
            next_billing_date=now + timedelta(days=30),
            is_trial=is_trial,
            trial_start=now if is_trial else None,
            trial_end=now + timedelta(days=14) if is_trial else None,
            current_period_usage={}
        )

        self.db.add(subscription)

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            event_type="subscription_created",
            event_data={
                "subscription_id": subscription.id,
                "tier_name": tier_name,
                "is_trial": is_trial
            },
            status="success"
        )
        self.db.add(event)

        self.db.commit()

        return {
            "subscription_id": subscription.id,
            "organization_id": organization_id,
            "tier_name": tier_name,
            "status": subscription.status,
            "billing_period_end": subscription.billing_period_end.isoformat(),
            "is_trial": is_trial
        }

    def get_subscription(self, organization_id: str) -> Optional[Dict]:
        """Get subscription for an organization"""
        subscription = self.db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == organization_id
        ).first()

        if not subscription:
            return None

        tier = self.db.query(BillingTier).filter(
            BillingTier.id == subscription.tier_id
        ).first()

        return {
            "subscription_id": subscription.id,
            "organization_id": organization_id,
            "tier": {
                "id": tier.id,
                "name": tier.tier_name,
                "display_name": tier.display_name,
                "base_price": tier.base_price_monthly,
                "limits": tier.limits
            },
            "status": subscription.status,
            "is_trial": subscription.is_trial,
            "billing_period_start": subscription.billing_period_start.isoformat() if subscription.billing_period_start else None,
            "billing_period_end": subscription.billing_period_end.isoformat() if subscription.billing_period_end else None,
            "current_period_usage": subscription.current_period_usage or {}
        }

    def check_usage_limits(self, organization_id: str, metric_type: str) -> Tuple[bool, Dict]:
        """Check if organization has exceeded usage limits"""
        subscription = self.get_subscription(organization_id)

        if not subscription:
            return False, {"error": "No subscription found"}

        if subscription["status"] not in ["active", "trial"]:
            return False, {"error": f"Subscription status is {subscription['status']}"}

        limits = subscription["tier"]["limits"]

        if metric_type not in limits:
            return True, {"allowed": True, "reason": "No limit for this metric"}

        limit = limits[metric_type]

        # Get current period usage
        period_start = subscription["billing_period_start"]
        current_usage = self.db.query(func.sum(UsageMetric.metric_value)).filter(
            and_(
                UsageMetric.organization_id == organization_id,
                UsageMetric.metric_type == metric_type,
                UsageMetric.period_start >= datetime.fromisoformat(period_start)
            )
        ).scalar() or 0

        allowed = current_usage < limit

        return allowed, {
            "allowed": allowed,
            "current_usage": current_usage,
            "limit": limit,
            "percentage_used": (current_usage / limit * 100) if limit > 0 else 0
        }

    # ========================================================================
    # Google Cloud Marketplace Integration
    # ========================================================================

    def report_usage_to_gcp(self, organization_id: str, period_start: datetime, period_end: datetime) -> Dict:
        """Report usage to Google Cloud Marketplace"""
        try:
            subscription = self.get_subscription(organization_id)

            if not subscription or not subscription.get("gcp_account_id"):
                logger.warning(f"No GCP account ID for organization {organization_id}")
                return {"success": False, "error": "No GCP account ID"}

            # Get metrics for the period
            metrics = self.db.query(UsageMetric).filter(
                and_(
                    UsageMetric.organization_id == organization_id,
                    UsageMetric.period_start >= period_start,
                    UsageMetric.period_end <= period_end,
                    UsageMetric.reported_to_gcp == False
                )
            ).all()

            if not metrics:
                return {"success": True, "message": "No unreported metrics"}

            # Format usage report for GCP
            usage_report = {
                "name": f"operations/report-{uuid.uuid4().hex[:12]}",
                "operationId": f"report-{organization_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "consumerId": subscription["gcp_account_id"],
                "usageReportingId": organization_id,
                "startTime": period_start.isoformat() + "Z",
                "endTime": period_end.isoformat() + "Z",
                "metricValueSets": []
            }

            # Aggregate metrics by type
            metric_values = {}
            for metric in metrics:
                if metric.metric_type not in metric_values:
                    metric_values[metric.metric_type] = 0
                metric_values[metric.metric_type] += metric.metric_value

            # Add to report
            for metric_type, value in metric_values.items():
                usage_report["metricValueSets"].append({
                    "metricName": f"compute.googleapis.com/{metric_type}",
                    "metricValues": [{
                        "int64Value": str(int(value))
                    }]
                })

            # TODO: Actually send to GCP API
            # For now, just mark as reported
            for metric in metrics:
                metric.reported_to_gcp = True
                metric.reported_at = datetime.utcnow()
                metric.report_response = usage_report

            # Log event
            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                event_type="usage_reported",
                event_data={
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "metrics_count": len(metrics),
                    "report": usage_report
                },
                status="success"
            )
            self.db.add(event)

            self.db.commit()

            return {
                "success": True,
                "metrics_reported": len(metrics),
                "report": usage_report
            }

        except Exception as e:
            logger.error(f"Error reporting usage to GCP: {e}")
            self.db.rollback()

            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                event_type="usage_reported",
                event_data={
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat()
                },
                status="failed",
                error_message=str(e)
            )
            self.db.add(event)
            self.db.commit()

            return {"success": False, "error": str(e)}
