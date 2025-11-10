"""
Admin endpoints for audit log management and verification
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import User, UserRole
from ..security.audit_chain import get_audit_chain_service

router = APIRouter(prefix="/api/admin/audit", tags=["admin-audit"])


def require_admin(current_user: User = Depends(get_current_user)):
    """Dependency that requires admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


@router.get("/chain/stats")
async def get_chain_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get audit log chain statistics

    Returns:
        Chain statistics including total entries, genesis hash, latest hash
    """
    audit_service = get_audit_chain_service(db)
    stats = audit_service.get_chain_stats()

    return {
        "success": True,
        "chain_stats": stats,
        "message": f"Chain contains {stats['total_entries']} entries",
    }


@router.post("/chain/verify")
async def verify_chain_integrity(
    start_sequence: int = 1,
    end_sequence: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Verify integrity of audit log chain

    Checks for:
    - Hash mismatches (tampering)
    - Chain breaks (deleted/modified entries)
    - Sequence gaps (missing entries)

    Args:
        start_sequence: Starting sequence number (default: 1)
        end_sequence: Ending sequence number (default: verify all)

    Returns:
        Verification result with list of issues if any
    """
    audit_service = get_audit_chain_service(db)

    # Verify chain
    is_valid, issues = audit_service.verify_chain_integrity(
        start_sequence=start_sequence, end_sequence=end_sequence
    )

    if is_valid:
        return {
            "success": True,
            "chain_valid": True,
            "issues": [],
            "message": "Audit log chain integrity verified. No tampering detected.",
            "verified_range": {
                "start": start_sequence,
                "end": end_sequence or "latest",
            },
        }
    else:
        # CRITICAL: Tampering detected
        return {
            "success": False,
            "chain_valid": False,
            "issues": issues,
            "message": f"⚠️ TAMPERING DETECTED: {len(issues)} integrity violations found",
            "verified_range": {
                "start": start_sequence,
                "end": end_sequence or "latest",
            },
            "severity": "CRITICAL",
            "action_required": (
                "Investigate immediately. Audit logs may have been modified. "
                "Check database access logs and notify security team."
            ),
        }


@router.post("/chain/verify-entry/{entry_id}")
async def verify_single_entry(
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Verify a single audit log entry

    Args:
        entry_id: Audit log entry ID

    Returns:
        Verification result for the specific entry
    """
    from ..models import AuditLog
    import hashlib
    import json

    # Get the entry
    entry = db.query(AuditLog).filter_by(id=entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry {entry_id} not found",
        )

    # Recalculate hash
    data = (
        f"{entry.id}|"
        f"{entry.user_id or ''}|"
        f"{entry.action}|"
        f"{entry.resource_type or ''}|"
        f"{entry.resource_id or ''}|"
        f"{entry.details or '{}'}|"
        f"{entry.previous_hash or ''}|"
        f"{entry.sequence_number}"
    )

    calculated_hash = hashlib.sha256(data.encode("utf-8")).hexdigest()

    is_valid = calculated_hash == entry.entry_hash

    return {
        "success": True,
        "entry_id": entry_id,
        "sequence_number": entry.sequence_number,
        "hash_valid": is_valid,
        "stored_hash": entry.entry_hash,
        "calculated_hash": calculated_hash,
        "message": (
            "Entry hash is valid"
            if is_valid
            else "⚠️ Entry hash mismatch - possible tampering"
        ),
        "entry_details": {
            "action": entry.action,
            "user_id": entry.user_id,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        },
    }


@router.get("/chain/health")
async def get_chain_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Get overall health status of audit log chain

    Performs quick verification and returns status

    Returns:
        Health status (healthy/degraded/critical)
    """
    audit_service = get_audit_chain_service(db)

    # Get stats
    stats = audit_service.get_chain_stats()

    if stats["total_entries"] == 0:
        return {"status": "healthy", "message": "No audit logs yet", "total_entries": 0}

    # Quick verification of last 100 entries
    latest_sequence = stats["latest_sequence"]
    start_sequence = max(1, latest_sequence - 100)

    is_valid, issues = audit_service.verify_chain_integrity(
        start_sequence=start_sequence, end_sequence=latest_sequence
    )

    if is_valid:
        return {
            "status": "healthy",
            "message": "Audit log chain is healthy",
            "total_entries": stats["total_entries"],
            "verified_entries": min(100, stats["total_entries"]),
            "latest_entry": stats["latest_entry_date"],
        }
    else:
        # Determine severity
        critical_issues = [i for i in issues if i.get("severity") == "CRITICAL"]

        if critical_issues:
            return {
                "status": "critical",
                "message": f"⚠️ {len(critical_issues)} critical integrity violations detected",
                "total_entries": stats["total_entries"],
                "issues": issues,
                "action_required": "Investigate immediately",
            }
        else:
            return {
                "status": "degraded",
                "message": f"⚠️ {len(issues)} integrity issues detected",
                "total_entries": stats["total_entries"],
                "issues": issues,
                "action_required": "Review and investigate",
            }
