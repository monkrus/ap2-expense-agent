#!/usr/bin/env python3
"""
Usage reporting script for Google Cloud Marketplace billing

This script runs as a Kubernetes CronJob to report accumulated usage
metrics to Google Cloud Commerce API for billing purposes.
"""
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.services.billing_service import BillingService
from src.models_billing import OrganizationSubscription

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def report_usage():
    """Report usage for all organizations with active subscriptions"""
    try:
        logger.info("Starting usage reporting job...")

        # Create database session
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            # Get all active subscriptions
            subscriptions = db.query(OrganizationSubscription).filter(
                OrganizationSubscription.status.in_(['active', 'trial'])
            ).all()

            logger.info(f"Found {len(subscriptions)} active subscriptions")

            # Report usage for each organization
            success_count = 0
            error_count = 0

            for subscription in subscriptions:
                try:
                    organization_id = subscription.organization_id

                    # Report usage for the last hour
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)

                    logger.info(f"Reporting usage for organization {organization_id}")
                    logger.info(f"Period: {start_time} to {end_time}")

                    billing_service = BillingService(db)
                    result = billing_service.report_usage_to_gcp(
                        organization_id=organization_id,
                        period_start=start_time,
                        period_end=end_time
                    )

                    if result["success"]:
                        success_count += 1
                        metrics_count = result.get("metrics_reported", 0)
                        logger.info(f"✓ Successfully reported {metrics_count} metrics for {organization_id}")
                    else:
                        error_count += 1
                        error_msg = result.get("error", "Unknown error")
                        logger.error(f"✗ Failed to report usage for {organization_id}: {error_msg}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ Error processing organization {subscription.organization_id}: {e}")

            logger.info("=" * 60)
            logger.info(f"Usage reporting completed:")
            logger.info(f"  Total subscriptions: {len(subscriptions)}")
            logger.info(f"  Successful reports: {success_count}")
            logger.info(f"  Failed reports: {error_count}")
            logger.info("=" * 60)

            # Exit with error code if any reports failed
            if error_count > 0:
                logger.warning(f"Some reports failed. {error_count} errors occurred.")
                sys.exit(1)
            else:
                logger.info("All usage reports completed successfully!")
                sys.exit(0)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Fatal error in usage reporting: {e}")
        sys.exit(1)


if __name__ == "__main__":
    report_usage()
