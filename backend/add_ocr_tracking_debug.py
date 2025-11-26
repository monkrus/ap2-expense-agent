#!/usr/bin/env python3
"""Add debug logging to OCR tracking"""

file_path = "src/routes/receipts.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add debug logging before the tracking code
old_code = """        # Track OCR usage for successful extractions
        if membership and successful_files:
            tracker = UsageTracker(db)
            tracker.track_usage(
                user_id=current_user.id,
                usage_type="ocr_scan",
                quantity=len(successful_files),
                organization_id=membership.organization_id
            )"""

new_code = """        # Track OCR usage for successful extractions
        print(f"[OCR DEBUG] membership={membership}, successful_files count={len(successful_files) if successful_files else 0}")
        if membership and successful_files:
            print(f"[OCR DEBUG] Tracking {len(successful_files)} OCR scans for user {current_user.id}")
            tracker = UsageTracker(db)
            record = tracker.track_usage(
                user_id=current_user.id,
                usage_type="ocr_scan",
                quantity=len(successful_files),
                organization_id=membership.organization_id
            )
            print(f"[OCR DEBUG] Created UsageRecord: {record.id}")
        else:
            print(f"[OCR DEBUG] NOT tracking - membership={membership is not None}, successful_files={len(successful_files) if successful_files else 0}")"""

content = content.replace(old_code, new_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added debug logging to OCR tracking")
