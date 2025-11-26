#!/usr/bin/env python3
"""
Fix OCR usage tracking bug in receipts.py
Adds missing UsageTracker call after successful OCR extraction
"""

import re

file_path = "src/routes/receipts.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add UsageTracker import
import_section = """from ..auth import get_current_active_user
from ..database import get_db
from ..models import Expense, Receipt, User, OrganizationMember
from ..services.receipt_ai_service import get_receipt_ai_service
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError"""

new_import_section = """from ..auth import get_current_active_user
from ..database import get_db
from ..models import Expense, Receipt, User, OrganizationMember
from ..services.receipt_ai_service import get_receipt_ai_service
from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..billing.usage_tracker import UsageTracker"""

content = content.replace(import_section, new_import_section)

# Fix 2: Add usage tracking after successful OCR extraction
# Find the section after extraction where we return results
old_code = """            # Merge extraction data with file info
            for idx, result in enumerate(successful_files):
                if idx < len(extractions):
                    result["extracted_data"] = extractions[idx]

        return {"success": True, "total_files": len(files), "results": results}"""

new_code = """            # Merge extraction data with file info
            for idx, result in enumerate(successful_files):
                if idx < len(extractions):
                    result["extracted_data"] = extractions[idx]

        # Track OCR usage for successful extractions
        if membership and successful_files:
            tracker = UsageTracker(db)
            tracker.track_usage(
                user_id=current_user.id,
                usage_type="ocr_scan",
                quantity=len(successful_files),
                organization_id=membership.organization_id
            )

        return {"success": True, "total_files": len(files), "results": results}"""

content = content.replace(old_code, new_code)

# Write the file back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE: Fixed OCR usage tracking in receipts.py")
print("   - Added UsageTracker import")
print("   - Added usage tracking call after successful OCR extraction")
