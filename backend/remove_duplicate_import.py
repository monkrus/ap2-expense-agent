#!/usr/bin/env python3
"""Remove duplicate UsageTracker import"""

file_path = "src/routes/receipts.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove duplicate import
old_import = """from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..billing.usage_tracker import UsageTracker
from ..billing.usage_tracker import UsageTracker"""

new_import = """from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
from ..billing.usage_tracker import UsageTracker"""

content = content.replace(old_import, new_import)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE: Removed duplicate import")
