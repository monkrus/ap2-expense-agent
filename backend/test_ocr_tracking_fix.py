#!/usr/bin/env python3
"""
Test OCR usage tracking fix
Verifies that OCR scans are now properly tracked
"""

import requests
import json

BASE = 'http://localhost:8000'

print("="*70)
print("OCR USAGE TRACKING FIX - VERIFICATION TEST")
print("="*70)

# Step 1: Register a new user for clean testing
print("\nStep 1: Register new Free tier user")
reg_resp = requests.post(f'{BASE}/api/v1/auth/register', json={
    'username': 'ocrtest',
    'email': 'ocrtest@test.com',
    'password': 'Test123!'
})

if reg_resp.status_code != 201:
    print(f"Registration failed: {reg_resp.status_code} - {reg_resp.text}")
    exit(1)

print("  User registered")

# Step 2: Login
login_resp = requests.post(f'{BASE}/api/v1/auth/login', json={
    'username': 'ocrtest',
    'password': 'Test123!'
})

if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.text}")
    exit(1)

token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("  Logged in")

# Step 3: Create an organization
print("\nStep 2: Create organization")
org_resp = requests.post(f'{BASE}/api/v1/organizations',
    json={'name': 'OCR Test Org', 'description': 'Testing OCR tracking', 'slug': 'ocrtest'},
    headers=headers
)

if org_resp.status_code not in [200, 201]:
    print(f"Organization creation failed: {org_resp.status_code} - {org_resp.text}")
    exit(1)

org_id = org_resp.json()['organization']['id']
print(f"  Organization created: {org_id}")

# Step 4: Check initial OCR usage (should be 0/5)
print("\nStep 3: Check initial OCR usage")
usage_resp = requests.get(f'{BASE}/api/billing/usage/summary', headers=headers)
if usage_resp.status_code == 200:
    usage_data = usage_resp.json()
    ocr_usage = usage_data.get('usage', {}).get('ocr_scans', {})
    print(f"  Initial OCR usage: {ocr_usage.get('current', 0)}/{ocr_usage.get('limit', 5)}")
    initial_ocr_count = ocr_usage.get('current', 0)
else:
    print(f"  Failed to get usage: {usage_resp.text}")
    initial_ocr_count = 0

# Step 5: Simulate OCR batch upload (create mock image files)
print("\nStep 4: Simulate batch OCR upload (2 receipts)")
print("  Note: This will use mock/empty files since we're testing tracking, not actual OCR")

# Create mock image data
import io

# Create 2 mock receipt files
files = []
for i in range(2):
    # Create a tiny valid JPEG (1x1 pixel)
    mock_jpeg = io.BytesIO(
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
        b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
        b'\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01'
        b'\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07'
        b'\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05'
        b'\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07'
        b'"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18'
        b'\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86'
        b'\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6'
        b'\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6'
        b'\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5'
        b'\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00'
        b'\x08\x01\x01\x00\x00?\x00\xfe\xfe(\xff\xd9'
    )
    mock_jpeg.name = f'receipt{i+1}.jpg'
    files.append(('files', (f'receipt{i+1}.jpg', mock_jpeg, 'image/jpeg')))

# Upload batch
batch_resp = requests.post(f'{BASE}/api/v1/receipts/batch-upload',
    files=files,
    headers=headers
)

if batch_resp.status_code == 200:
    batch_data = batch_resp.json()
    print(f"  Batch upload successful: {batch_data.get('total_files', 0)} files processed")
elif batch_resp.status_code == 402:
    print(f"  Payment required (limit exceeded): {batch_resp.json()}")
else:
    print(f"  Batch upload failed: {batch_resp.status_code} - {batch_resp.text[:200]}")

# Step 6: Check OCR usage AFTER upload (should be 2/5 if tracking works)
print("\nStep 5: Check OCR usage AFTER batch upload")
usage_resp = requests.get(f'{BASE}/api/billing/usage/summary', headers=headers)

if usage_resp.status_code == 200:
    usage_data = usage_resp.json()
    ocr_usage = usage_data.get('usage', {}).get('ocr_scans', {})
    final_ocr_count = ocr_usage.get('current', 0)
    ocr_limit = ocr_usage.get('limit', 5)

    print(f"  Final OCR usage: {final_ocr_count}/{ocr_limit}")

    # Verify the fix
    print("\n" + "="*70)
    print("VERIFICATION RESULT")
    print("="*70)

    expected_count = initial_ocr_count + 2

    if final_ocr_count == expected_count:
        print(f"PASS: OCR usage tracking is working correctly!")
        print(f"  - Initial usage: {initial_ocr_count}")
        print(f"  - Files uploaded: 2")
        print(f"  - Final usage: {final_ocr_count}")
        print(f"  - Increment: {final_ocr_count - initial_ocr_count}")
    else:
        print(f"FAIL: OCR usage tracking is NOT working!")
        print(f"  - Expected: {expected_count}")
        print(f"  - Actual: {final_ocr_count}")
        print(f"  - The bug still exists - usage not being tracked")
else:
    print(f"  Failed to get usage: {usage_resp.text}")
    print("\nFAIL: Could not verify usage tracking")

print("\n" + "="*70)
