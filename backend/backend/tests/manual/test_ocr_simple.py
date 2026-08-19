#!/usr/bin/env python3
"""Simple OCR tracking test with existing user"""

import requests
import io

BASE = 'http://localhost:8000'

print("="*60)
print("OCR TRACKING TEST")
print("="*60)

# Login
print("\n1. Logging in as freetest2...")
login_resp = requests.post(f'{BASE}/api/v1/auth/login', json={
    'username': 'freetest2',
    'password': 'Test123!'
})

if login_resp.status_code != 200:
    print(f"   FAILED: {login_resp.status_code}")
    exit(1)

token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("   SUCCESS")

# Check initial usage
print("\n2. Checking initial OCR usage...")
usage_resp = requests.get(f'{BASE}/api/billing/usage/summary', headers=headers)
if usage_resp.status_code == 200:
    ocr_usage = usage_resp.json().get('usage', {}).get('ocr_scans', {})
    initial = ocr_usage.get('current', 0)
    limit = ocr_usage.get('limit', 5)
    print(f"   Initial: {initial}/{limit}")
else:
    print(f"   FAILED to get usage")
    initial = 0

# Upload receipts
print("\n3. Uploading 2 receipts...")
files = []
for i in range(2):
    # Minimal valid JPEG
    mock_jpeg = io.BytesIO(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')
    files.append(('files', (f'test{i+1}.jpg', mock_jpeg, 'image/jpeg')))

batch_resp = requests.post(f'{BASE}/api/v1/receipts/batch-upload', files=files, headers=headers)
print(f"   Upload status: {batch_resp.status_code}")

if batch_resp.status_code != 200:
    print(f"   ERROR: {batch_resp.text[:200]}")
    exit(1)

print("   SUCCESS")

# Check final usage
print("\n4. Checking final OCR usage...")
usage_resp = requests.get(f'{BASE}/api/billing/usage/summary', headers=headers)
if usage_resp.status_code == 200:
    ocr_usage = usage_resp.json().get('usage', {}).get('ocr_scans', {})
    final = ocr_usage.get('current', 0)
    limit = ocr_usage.get('limit', 5)
    print(f"   Final: {final}/{limit}")
else:
    print(f"   FAILED to get usage")
    final = initial

# Result
print("\n" + "="*60)
print("RESULT")
print("="*60)

if final > initial:
    print(f"SUCCESS! OCR tracking is WORKING!")
    print(f"  - Initial: {initial}")
    print(f"  - Final: {final}")
    print(f"  - Increase: +{final - initial}")
else:
    print(f"FAILED! OCR tracking is NOT working")
    print(f"  - Expected increase from {initial} to {initial+2}")
    print(f"  - Actual: stayed at {final}")

print("="*60)
