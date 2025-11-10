"""
Tamper-Proof Audit Log Service with Hash Chaining
Implements blockchain-like integrity verification for audit trails
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models import AuditLog


class AuditChainService:
    """
    Service for creating and verifying tamper-proof audit logs

    Uses hash chaining (similar to blockchain) where each entry contains:
    1. Hash of the previous entry (previous_hash)
    2. Hash of current entry data (entry_hash)
    3. Monotonically increasing sequence number

    Any modification to any entry breaks the chain and is detectable.
    """

    def __init__(self, db: Session):
        """Initialize audit chain service"""
        self.db = db

    def create_audit_entry(
        self,
        user_id: str,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create a new tamper-proof audit log entry

        The entry is linked to the previous entry via hash chain.

        Args:
            user_id: User performing the action
            action: Action performed (e.g., "expense_approved", "mandate_revoked")
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details (will be JSON encoded)
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog entry with hash chain
        """
        # Get the last audit log entry to link to
        previous_entry = (
            self.db.query(AuditLog).order_by(desc(AuditLog.sequence_number)).first()
        )

        # Determine sequence number and previous hash
        if previous_entry:
            sequence_number = previous_entry.sequence_number + 1
            previous_hash = previous_entry.entry_hash
        else:
            # Genesis entry (first log)
            sequence_number = 1
            previous_hash = "0" * 64  # Genesis hash

        # Create new entry
        entry_id = str(uuid.uuid4())
        details_json = json.dumps(details, sort_keys=True) if details else "{}"

        # Calculate entry hash
        entry_hash = self._calculate_entry_hash(
            entry_id=entry_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type or "",
            resource_id=resource_id or "",
            details=details_json,
            previous_hash=previous_hash,
            sequence_number=sequence_number,
        )

        # Create audit log entry
        audit_entry = AuditLog(
            id=entry_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
            sequence_number=sequence_number,
            created_at=datetime.utcnow(),
        )

        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)

        return audit_entry

    def verify_chain_integrity(
        self, start_sequence: int = 1, end_sequence: Optional[int] = None
    ) -> Tuple[bool, List[Dict]]:
        """
        Verify the integrity of the audit log chain

        Checks:
        1. Each entry's hash matches its calculated hash
        2. Each entry's previous_hash matches the actual previous entry's entry_hash
        3. Sequence numbers are continuous

        Args:
            start_sequence: Starting sequence number to verify
            end_sequence: Ending sequence number (None = verify all)

        Returns:
            Tuple of (is_valid, list_of_issues)
            - is_valid: True if chain is intact
            - list_of_issues: List of detected integrity violations

        Example:
            is_valid, issues = service.verify_chain_integrity()
            if not is_valid:
                print(f"TAMPERING DETECTED: {len(issues)} violations")
                for issue in issues:
                    print(f"  - {issue['description']}")
        """
        # Build query
        query = self.db.query(AuditLog).filter(
            AuditLog.sequence_number >= start_sequence
        )

        if end_sequence:
            query = query.filter(AuditLog.sequence_number <= end_sequence)

        # Get entries in sequence order
        entries = query.order_by(AuditLog.sequence_number).all()

        if not entries:
            return True, []  # Empty chain is valid

        issues = []
        previous_entry = None

        for entry in entries:
            # Check 1: Verify entry hash
            calculated_hash = self._calculate_entry_hash(
                entry_id=entry.id,
                user_id=entry.user_id or "",
                action=entry.action,
                resource_type=entry.resource_type or "",
                resource_id=entry.resource_id or "",
                details=entry.details or "{}",
                previous_hash=entry.previous_hash or "",
                sequence_number=entry.sequence_number,
            )

            if calculated_hash != entry.entry_hash:
                issues.append(
                    {
                        "sequence": entry.sequence_number,
                        "entry_id": entry.id,
                        "type": "hash_mismatch",
                        "description": (
                            f"Entry hash mismatch at sequence {entry.sequence_number}. "
                            f"Expected: {calculated_hash}, Got: {entry.entry_hash}"
                        ),
                        "severity": "CRITICAL",
                    }
                )

            # Check 2: Verify chain linkage
            if previous_entry:
                if entry.previous_hash != previous_entry.entry_hash:
                    issues.append(
                        {
                            "sequence": entry.sequence_number,
                            "entry_id": entry.id,
                            "type": "chain_break",
                            "description": (
                                f"Chain break at sequence {entry.sequence_number}. "
                                f"Previous hash doesn't match: "
                                f"Expected: {previous_entry.entry_hash}, Got: {entry.previous_hash}"
                            ),
                            "severity": "CRITICAL",
                        }
                    )

                # Check 3: Verify sequence continuity
                if entry.sequence_number != previous_entry.sequence_number + 1:
                    issues.append(
                        {
                            "sequence": entry.sequence_number,
                            "entry_id": entry.id,
                            "type": "sequence_gap",
                            "description": (
                                f"Sequence gap detected: "
                                f"Previous: {previous_entry.sequence_number}, "
                                f"Current: {entry.sequence_number}"
                            ),
                            "severity": "HIGH",
                        }
                    )

            # Check genesis entry
            elif entry.sequence_number == 1:
                expected_genesis = "0" * 64
                if entry.previous_hash != expected_genesis:
                    issues.append(
                        {
                            "sequence": 1,
                            "entry_id": entry.id,
                            "type": "invalid_genesis",
                            "description": (
                                f"Invalid genesis hash. "
                                f"Expected: {expected_genesis}, Got: {entry.previous_hash}"
                            ),
                            "severity": "CRITICAL",
                        }
                    )

            previous_entry = entry

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_chain_stats(self) -> Dict:
        """
        Get statistics about the audit log chain

        Returns:
            Dictionary with chain statistics
        """
        total_entries = self.db.query(AuditLog).count()

        if total_entries == 0:
            return {
                "total_entries": 0,
                "chain_length": 0,
                "genesis_hash": None,
                "latest_hash": None,
            }

        first_entry = self.db.query(AuditLog).order_by(AuditLog.sequence_number).first()

        latest_entry = (
            self.db.query(AuditLog).order_by(desc(AuditLog.sequence_number)).first()
        )

        return {
            "total_entries": total_entries,
            "chain_length": latest_entry.sequence_number if latest_entry else 0,
            "genesis_hash": first_entry.previous_hash if first_entry else None,
            "latest_hash": latest_entry.entry_hash if latest_entry else None,
            "latest_sequence": latest_entry.sequence_number if latest_entry else 0,
            "first_entry_date": (
                first_entry.created_at.isoformat() if first_entry else None
            ),
            "latest_entry_date": (
                latest_entry.created_at.isoformat() if latest_entry else None
            ),
        }

    def _calculate_entry_hash(
        self,
        entry_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: str,
        previous_hash: str,
        sequence_number: int,
    ) -> str:
        """
        Calculate SHA-256 hash of audit log entry

        The hash includes all critical fields to detect any tampering.

        Args:
            All audit log fields

        Returns:
            64-character hex SHA-256 hash
        """
        # Create canonical representation
        data = (
            f"{entry_id}|"
            f"{user_id}|"
            f"{action}|"
            f"{resource_type}|"
            f"{resource_id}|"
            f"{details}|"
            f"{previous_hash}|"
            f"{sequence_number}"
        )

        # Calculate SHA-256
        hash_obj = hashlib.sha256(data.encode("utf-8"))
        return hash_obj.hexdigest()


# Singleton instance
_audit_chain_service: Optional[AuditChainService] = None


def get_audit_chain_service(db: Session) -> AuditChainService:
    """
    Get or create audit chain service instance

    Args:
        db: Database session

    Returns:
        AuditChainService instance
    """
    global _audit_chain_service
    if _audit_chain_service is None:
        _audit_chain_service = AuditChainService(db)
    return _audit_chain_service
