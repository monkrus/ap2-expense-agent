"""Receipt upload and management routes"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid
import os
import shutil
from pathlib import Path

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Receipt, Expense

router = APIRouter(
    prefix="/api/v1/receipts",
    tags=["Receipts"]
)

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
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    allowed_content_types = {
        "image/jpeg", "image/jpg", "image/png", "image/gif",
        "image/bmp", "image/webp", "application/pdf"
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Content type not allowed: {file.content_type}"
        )


@router.post("/upload/{expense_id}")
async def upload_receipt(
    expense_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a receipt for an expense"""

    # Validate file
    validate_file(file)

    # Check if expense exists and user owns it
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only upload receipts for your own expenses"
        )

    # Check file size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
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
        content_type=file.content_type
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
            "uploaded_at": receipt.uploaded_at.isoformat()
        }
    }


@router.get("/{expense_id}")
async def get_receipts(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all receipts for an expense"""

    # Check if expense exists
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Check access - user must own the expense or be admin/manager
    from ..models import UserRole
    if expense.user_id != current_user.id and current_user.role not in [
        UserRole.ADMIN, UserRole.MANAGER
    ]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view these receipts"
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
                "uploaded_at": r.uploaded_at.isoformat()
            }
            for r in receipts
        ]
    }


@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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

    # Check ownership
    if expense.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete receipts for your own expenses"
        )

    # Only allow deletion if expense is still pending
    from ..models import ExpenseStatus
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete receipts from non-pending expenses"
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

    return {
        "success": True,
        "message": "Receipt deleted successfully"
    }


@router.get("/download/{receipt_id}")
async def download_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
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

    # Check access
    from ..models import UserRole
    if expense.user_id != current_user.id and current_user.role not in [
        UserRole.ADMIN, UserRole.MANAGER
    ]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to download this receipt"
        )

    # Check if file exists
    file_path = Path(receipt.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Receipt file not found")

    return FileResponse(
        path=file_path,
        filename=receipt.original_filename,
        media_type=receipt.content_type
    )
