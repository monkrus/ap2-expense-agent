#!/usr/bin/env python3
"""
Cleanup utility to remove soft-deleted organizations from the database.

This script hard-deletes organizations that have been soft-deleted for more than 30 days,
freeing up slugs and preventing UNIQUE constraint violations.

Run this script periodically (e.g., via cron job) to maintain database health.

Usage:
    python cleanup_soft_deleted_orgs.py [--dry-run] [--days=30]
"""

import argparse
import sys
from datetime import datetime, timedelta

# Add src to path so we can import models
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import SessionLocal
from models import Organization, OrganizationMember


def cleanup_soft_deleted_orgs(dry_run=True, days_threshold=30):
    """
    Remove soft-deleted organizations older than specified days.

    Args:
        dry_run: If True, only show what would be deleted without actually deleting
        days_threshold: Number of days after which soft-deleted orgs are permanently removed

    Returns:
        Number of organizations that were (or would be) deleted
    """
    db = SessionLocal()

    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        print(f"\n{'='*80}")
        print(f"SOFT-DELETED ORGANIZATION CLEANUP")
        print(f"{'='*80}")
        print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (will delete records)'}")
        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} ({days_threshold} days ago)")
        print(f"{'='*80}\n")

        # Find soft-deleted organizations older than threshold
        soft_deleted_orgs = (
            db.query(Organization)
            .filter(Organization.is_active == False)
            .filter(Organization.updated_at < cutoff_date)
            .all()
        )

        if not soft_deleted_orgs:
            print("✓ No soft-deleted organizations found older than threshold.")
            print("  Database is clean!")
            return 0

        print(f"Found {len(soft_deleted_orgs)} soft-deleted organization(s) to clean up:\n")

        # Display organizations that will be deleted
        for org in soft_deleted_orgs:
            deleted_age = (datetime.utcnow() - org.updated_at).days
            print(f"  • {org.name} (slug: {org.slug})")
            print(f"    ID: {org.id}")
            print(f"    Deleted: {org.updated_at.strftime('%Y-%m-%d')} ({deleted_age} days ago)")

            # Count associated members
            member_count = (
                db.query(OrganizationMember)
                .filter(OrganizationMember.organization_id == org.id)
                .count()
            )
            print(f"    Associated members: {member_count}")
            print()

        if dry_run:
            print(f"\n{'='*80}")
            print(f"DRY RUN COMPLETE")
            print(f"{'='*80}")
            print(f"Would delete {len(soft_deleted_orgs)} organization(s).")
            print(f"Run with --live to actually delete these records.")
            print(f"{'='*80}\n")
            return len(soft_deleted_orgs)

        # Confirm deletion in live mode
        print(f"\n{'='*80}")
        print(f"WARNING: This will PERMANENTLY delete {len(soft_deleted_orgs)} organization(s)")
        print(f"{'='*80}")
        response = input("Are you sure you want to proceed? (yes/no): ")

        if response.lower() != 'yes':
            print("\nCancelled by user. No changes made.")
            return 0

        # Perform deletion
        deleted_count = 0
        for org in soft_deleted_orgs:
            try:
                # Delete associated members first (foreign key constraint)
                members_deleted = (
                    db.query(OrganizationMember)
                    .filter(OrganizationMember.organization_id == org.id)
                    .delete()
                )

                # Delete organization
                db.delete(org)
                db.commit()

                deleted_count += 1
                print(f"✓ Deleted: {org.name} (and {members_deleted} member records)")

            except Exception as e:
                print(f"✗ Failed to delete {org.name}: {e}")
                db.rollback()

        print(f"\n{'='*80}")
        print(f"CLEANUP COMPLETE")
        print(f"{'='*80}")
        print(f"Successfully deleted {deleted_count}/{len(soft_deleted_orgs)} organization(s).")
        print(f"{'='*80}\n")

        return deleted_count

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cleanup soft-deleted organizations from the database"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually delete records (default is dry-run mode)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete organizations soft-deleted more than N days ago (default: 30)"
    )

    args = parser.parse_args()

    # Run cleanup
    try:
        deleted = cleanup_soft_deleted_orgs(
            dry_run=not args.live,
            days_threshold=args.days
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
