"""Receipt upload and management routes"""

import asyncio
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..billing.usage_tracker import UsageTracker
from ..database import get_db
from ..models import Expense, OrganizationMember, Receipt, User
from ..services.receipt_ai_service import get_receipt_ai_service
from ..tenant_context import verify_organization_access

router = APIRouter(prefix="/api/v1/receipts", tags=["Receipts"])

logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads/receipts")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check content type
    allowed_content_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        "application/pdf",
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400, detail=f"Content type not allowed: {file.content_type}"
        )


@router.post("/upload/{expense_id}")
async def upload_receipt(
    expense_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload a receipt for an expense"""

    # Validate file
    validate_file(file)

    # Check if expense exists and user owns it
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if not verify_organization_access(current_user.id, expense.organization_id, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access receipts for this organization",
        )

    if expense.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only upload receipts for your own expenses"
        )

    # Check file size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # Reset file pointer
    await file.seek(0)

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create receipt record
    receipt = Receipt(
        id=str(uuid.uuid4()),
        expense_id=expense_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        content_type=file.content_type,
    )

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return {
        "success": True,
        "receipt": {
            "id": receipt.id,
            "filename": receipt.original_filename,
            "file_size": receipt.file_size,
            "content_type": receipt.content_type,
            "uploaded_at": receipt.uploaded_at.isoformat(),
        },
    }


@router.post("/batch-upload")
async def batch_upload_receipts(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload multiple receipts and extract data using AI"""

    logger.warning(
        f"[OCR DEBUG] batch-upload called with {len(files)} files for user {current_user.username}"
    )

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    # Get user's organization
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .filter(OrganizationMember.is_active == True)
        .first()
    )

    results = []
    temp_files = []

    try:
        # Process each file
        for file in files:
            # Validate file
            validate_file(file)

            # Check file size
            file_content = await file.read()
            file_size = len(file_content)

            if file_size > MAX_FILE_SIZE:
                results.append(
                    {
                        "filename": file.filename,
                        "success": False,
                        "error": f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
                    }
                )
                continue

            # Reset file pointer
            await file.seek(0)

            # Generate unique filename and save temporarily
            file_ext = Path(file.filename).suffix.lower()
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename

            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                temp_files.append(file_path)

                results.append(
                    {
                        "filename": file.filename,
                        "temp_filename": unique_filename,
                        "file_path": str(file_path),
                        "file_size": file_size,
                        "content_type": file.content_type,
                        "success": True,
                    }
                )

            except Exception as e:
                results.append(
                    {
                        "filename": file.filename,
                        "success": False,
                        "error": f"Failed to save file: {str(e)}",
                    }
                )

        # Extract data from all successful uploads using AI
        ai_service = get_receipt_ai_service()
        successful_files = [r for r in results if r.get("success")]

        if successful_files:
            file_paths = [r["file_path"] for r in successful_files]

            # Run extraction
            extractions = await ai_service.batch_extract_receipts(file_paths)

            # Merge extraction data with file info
            for idx, result in enumerate(successful_files):
                if idx < len(extractions):
                    result["extracted_data"] = extractions[idx]

        # Track OCR usage for successful extractions
        logger.warning(
            f"[OCR DEBUG] membership={membership}, successful_files count={len(successful_files) if successful_files else 0}"
        )
        if membership and successful_files:
            logger.warning(
                f"[OCR DEBUG] Tracking {len(successful_files)} OCR scans for user {current_user.id}"
            )
            tracker = UsageTracker(db)
            record = tracker.track_usage(
                user_id=current_user.id,
                usage_type="ocr_scan",
                quantity=len(successful_files),
                organization_id=membership.organization_id,
            )
            logger.warning(f"[OCR DEBUG] Created UsageMetric: {record.id}")
        else:
            logger.warning(
                f"[OCR DEBUG] NOT tracking - membership={membership is not None}, successful_files={len(successful_files) if successful_files else 0}"
            )

        for result in results:
            result.pop("file_path", None)

        return {"success": True, "total_files": len(files), "results": results}

    except Exception as e:
        # Clean up temp files on error
        for temp_file in temp_files:
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            except:
                pass

        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.post("/create-from-extraction")
async def create_expense_from_extraction(
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create an expense from extracted receipt data"""

    try:
        # Get required fields
        vendor = data.get("vendor")
        amount = data.get("amount")
        category = data.get("category", "Other")
        description = data.get("description", "")
        temp_filename = data.get("temp_filename")
        original_filename = data.get("original_filename")

        if not vendor or not amount or not temp_filename:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: vendor, amount, temp_filename",
            )

        # Verify temp file exists
        file_path = UPLOAD_DIR / temp_filename
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail="Temporary file not found. Please re-upload."
            )

        # Get user's organization
        from ..models import OrganizationMember

        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.is_active == True,
            )
            .first()
        )

        if not member:
            raise HTTPException(
                status_code=400, detail="User is not a member of any organization"
            )

        # Create expense
        expense = Expense(
            id=str(uuid.uuid4()),
            organization_id=member.organization_id,
            user_id=current_user.id,
            vendor=vendor,
            amount=float(amount),
            category=category,
            description=description,
            status="pending",
        )

        db.add(expense)
        db.flush()

        # Get file info
        file_stat = file_path.stat()

        # Create receipt record
        receipt = Receipt(
            id=str(uuid.uuid4()),
            expense_id=expense.id,
            filename=temp_filename,
            original_filename=original_filename or temp_filename,
            file_path=str(file_path),
            file_size=file_stat.st_size,
            content_type=data.get("content_type", "image/jpeg"),
        )

        db.add(receipt)
        db.commit()
        db.refresh(expense)
        db.refresh(receipt)

        return {
            "success": True,
            "expense": {
                "id": expense.id,
                "vendor": expense.vendor,
                "amount": float(expense.amount),
                "category": expense.category,
                "description": expense.description,
                "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else (expense.status.lower() if isinstance(expense.status, str) else expense.status)),
                "created_at": expense.created_at.isoformat(),
            },
            "receipt": {
                "id": receipt.id,
                "filename": receipt.original_filename,
                "uploaded_at": receipt.uploaded_at.isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create expense: {str(e)}"
        )


@router.get("/{expense_id}")
async def get_receipts(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all receipts for an expense"""

    # Check if expense exists
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if not verify_organization_access(current_user.id, expense.organization_id, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access receipts for this organization",
        )

    # Check access - user must own the expense or be admin/manager
    from ..models import UserRole

    if expense.user_id != current_user.id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.MANAGER,
    ]:
        raise HTTPException(
            status_code=403, detail="Not authorized to view these receipts"
        )

    # Get receipts
    receipts = db.query(Receipt).filter(Receipt.expense_id == expense_id).all()

    return {
        "expense_id": expense_id,
        "receipts": [
            {
                "id": r.id,
                "filename": r.original_filename,
                "file_size": r.file_size,
                "content_type": r.content_type,
                "uploaded_at": r.uploaded_at.isoformat(),
            }
            for r in receipts
        ],
    }


@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a receipt"""

    # Get receipt
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Get expense
    expense = db.query(Expense).filter(Expense.id == receipt.expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if not verify_organization_access(current_user.id, expense.organization_id, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access receipts for this organization",
        )

    # Check ownership
    if expense.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete receipts for your own expenses"
        )

    # Only allow deletion if expense is still pending
    from ..models import ExpenseStatus

    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=400, detail="Cannot delete receipts from non-pending expenses"
        )

    # Delete physical file
    try:
        file_path = Path(receipt.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Warning: Failed to delete physical file: {e}")

    # Delete database record
    db.delete(receipt)
    db.commit()

    return {"success": True, "message": "Receipt deleted successfully"}


@router.get("/download/{receipt_id}")
async def download_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download a receipt file"""
    from fastapi.responses import FileResponse

    # Get receipt
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Get expense
    expense = db.query(Expense).filter(Expense.id == receipt.expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if not verify_organization_access(current_user.id, expense.organization_id, db):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access receipts for this organization",
        )

    # Check access
    from ..models import UserRole

    if expense.user_id != current_user.id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.MANAGER,
    ]:
        raise HTTPException(
            status_code=403, detail="Not authorized to download this receipt"
        )

    # Check if file exists
    file_path = Path(receipt.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Receipt file not found")

    return FileResponse(
        path=file_path,
        filename=receipt.original_filename,
        media_type=receipt.content_type,
    )

