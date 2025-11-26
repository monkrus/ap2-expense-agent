#!/usr/bin/env python3
"""
Replace print() debug statements with logger statements so we can see them in logs
"""

file_path = "src/routes/receipts.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add logger import at the top (after other imports)
if 'import logging' not in content:
    # Find the import section and add logging
    old_imports = """from ..auth import get_current_active_user
from ..database import get_db"""

    new_imports = """import logging

from ..auth import get_current_active_user
from ..database import get_db"""

    content = content.replace(old_imports, new_imports)

# Add logger creation after imports
if 'logger = logging.getLogger(__name__)' not in content:
    old_router = """router = APIRouter(prefix="/api/v1/receipts", tags=["Receipts"])"""
    new_router = """router = APIRouter(prefix="/api/v1/receipts", tags=["Receipts"])

logger = logging.getLogger(__name__)"""

    content = content.replace(old_router, new_router)

# Replace print statements with logger.warning (so they show up clearly)
content = content.replace('print(f"[OCR DEBUG]', 'logger.warning(f"[OCR DEBUG]')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE: Replaced print() with logger.warning() for OCR debug statements")
print("  - Added logging import")
print("  - Added logger instance")
print("  - Converted all [OCR DEBUG] print() calls to logger.warning()")
