"""
GCP Usage Reporter
Aggregates and reports usage metrics to Google Cloud Marketplace
Runs hourly via Cloud Scheduler
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models import OrganizationMember, User
from ..models_billing import BillingEvent, MarketplaceEntitlement, UsageMetric
from .marketplace_client import get_gcp_marketplace_client
from .retry_logic import RetryableError, with_usage_report_retry


class GCPUsageReporter:
    """
    Aggregates usage metrics and reports to GCP Marketplace

    This service:
    1. Runs every hour (triggered by Cloud Scheduler)
    2. Aggregates usage for all active GCP subscriptions
    3. Reports to GCP Marketplace API for billing
    4. Logs results for audit trail
    """

    def __init__(self, db: Session):
        self.db = db
        self.gcp_client = get_gcp_marketplace_client()

    @with_usage_report_retry
    async def report_usage_with_retry(
        self, entitlement_id: str, metrics: Dict, timestamp: str
    ) -> Dict:
        """
        Report usage to GCP with automatic retry logic

        This method is wrapped with retry decorator for exponential backoff.

        Args:
            entitlement_id: GCP entitlement ID
            metrics: Usage metrics dict
            timestamp: ISO timestamp

        Returns:
            API response dict

        Raises:
            RetryableError: If all retries fail
        """
        response = await self.gcp_client.report_usage(
            entitlement_id=entitlement_id,
            metrics=metrics,
            timestamp=timestamp,
        )

        # Check if response indicates failure
        if response.get("status") == "error":
            raise RetryableError(f"Usage reporting failed: {response.get('error')}")

        return response

    async def report_all_organizations(self) -> Dict:
        """
        Report usage for all organizations with GCP entitlements

        This is the main entry point called by the cron job.

        Returns:
            Summary of reporting results
        """
        print(f"[{datetime.utcnow()}] Starting GCP usage reporting...")

        # Get all active entitlements
        entitlements = (
            self.db.query(MarketplaceEntitlement)
            .filter(MarketplaceEntitlement.state == "ACTIVE")
            .all()
        )

        print(f"Found {len(entitlements)} active GCP entitlements")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_entitlements": len(entitlements),
            "successful": [],
            "failed": [],
            "skipped": [],
        }

        for entitlement in entitlements:
            try:
                result = await self.report_organization_usage(entitlement)

                if result["status"] == "success":
                    results["successful"].append(
                        {
                            "organization_id": entitlement.organization_id,
                            "entitlement_id": entitlement.entitlement_id,
                            "metrics_reported": result.get("metrics_reported", 0),
                        }
                    )
                elif result["status"] == "skipped":
                    results["skipped"].append(
                        {
                            "organization_id": entitlement.organization_id,
                            "reason": result.get("reason"),
                        }
                    )
                else:
                    results["failed"].append(
                        {
                            "organization_id": entitlement.organization_id,
                            "error": result.get("error"),
                        }
                    )

            except Exception as e:
                print(f"Error reporting for org {entitlement.organization_id}: {e}")
                results["failed"].append(
                    {"organization_id": entitlement.organization_id, "error": str(e)}
                )

        print(
            f"Reporting complete: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed, {len(results['skipped'])} skipped"
        )

        return results

    async def report_organization_usage(
        self, entitlement: MarketplaceEntitlement
    ) -> Dict:
        """
        Report usage for a single organization

        Args:
            subscription: OrganizationSubscription instance

        Returns:
            Dict with status and details
        """
        organization_id = entitlement.organization_id
        entitlement_id = entitlement.entitlement_id

        # Define time window (last hour)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        # Aggregate usage metrics for this organization in the last hour
        usage_data = self.aggregate_usage(organization_id, start_time, end_time)

        # Check if there's any usage to report
        if not usage_data or all(v == 0 for v in usage_data.values()):
            return {
                "status": "skipped",
                "reason": "no_usage_in_period",
                "organization_id": organization_id,
            }

        # Use retry-enabled method with exponential backoff
        try:
            response = await self.report_usage_with_retry(
                entitlement_id=entitlement_id,
                metrics=usage_data,
                timestamp=end_time.isoformat() + "Z",
            )

            # Log the reporting event
            self.log_usage_report(
                organization_id,
                entitlement_id,
                usage_data,
                response,
                start_time,
                end_time,
            )

            return {
                "status": response.get("status", "success"),
                "organization_id": organization_id,
                "entitlement_id": entitlement_id,
                "metrics_reported": len(usage_data),
                "usage_data": usage_data,
            }

        except Exception as e:
            # Log error after all retries exhausted
            error_message = str(e)
            self.log_usage_report_error(
                organization_id, entitlement_id, error_message, start_time, end_time
            )

            return {
                "status": "error",
                "organization_id": organization_id,
                "error": error_message,
            }

    def aggregate_usage(
        self, organization_id: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, int]:
        """
        Aggregate usage metrics for an organization in a time period

        Args:
            organization_id: Organization ID
            start_time: Start of period
            end_time: End of period

        Returns:
            Dict of metric_name -> count
        """
        # Query usage metrics for this organization in the time window
        usage_records = (
            self.db.query(UsageMetric)
            .filter(
                UsageMetric.organization_id == organization_id,
                UsageMetric.period_start >= start_time,
                UsageMetric.period_end <= end_time,
            )
            .all()
        )

        # Aggregate by metric type
        aggregated = {}
        for record in usage_records:
            metric_type = record.metric_type
            if metric_type not in aggregated:
                aggregated[metric_type] = 0
            aggregated[metric_type] += int(record.metric_value)

        # Add active users count (special case - count unique users)
        active_users_count = self.count_active_users(
            organization_id, start_time, end_time
        )
        aggregated["active_users"] = active_users_count

        return aggregated

    def count_active_users(
        self, organization_id: str, start_time: datetime, end_time: datetime
    ) -> int:
        """
        Count active users in an organization during a time period

        Active = users who performed any action (submitted expense, etc.)

        Args:
            organization_id: Organization ID
            start_time: Start of period
            end_time: End of period

        Returns:
            Count of active users
        """
        # This is a simplified version - in production, you might track
        # user activity more granularly (last_activity timestamps, etc.)

        # For now, count all active members
        active_members = (
            self.db.query(func.count(OrganizationMember.id))
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_active == True,
            )
            .scalar()
        )

        return active_members or 0

    def log_usage_report(
        self,
        organization_id: str,
        entitlement_id: str,
        usage_data: Dict,
        api_response: Dict,
        start_time: datetime,
        end_time: datetime,
    ):
        """Log successful usage report to billing_events"""
        event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            event_type="gcp_usage_reported",
            event_data={
                "entitlement_id": entitlement_id,
                "usage_data": usage_data,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "api_response": api_response,
            },
            status="success",
            occurred_at=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()

    def log_usage_report_error(
        self,
        organization_id: str,
        entitlement_id: str,
        error_message: str,
        start_time: datetime,
        end_time: datetime,
    ):
        """Log failed usage report to billing_events"""
        event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            event_type="gcp_usage_report_failed",
            event_data={
                "entitlement_id": entitlement_id,
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
            },
            status="failed",
            error_message=error_message,
            occurred_at=datetime.utcnow(),
        )
        self.db.add(event)
        self.db.commit()


# Convenience function for the cron job endpoint
async def run_hourly_usage_reporting(db: Session) -> Dict:
    """
    Main entry point for hourly cron job

    This is called by Cloud Scheduler via HTTP POST

    Args:
        db: Database session

    Returns:
        Summary of reporting results
    """
    reporter = GCPUsageReporter(db)
    results = await reporter.report_all_organizations()
    return results
