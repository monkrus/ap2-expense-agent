#!/usr/bin/env python3
"""
Final test to verify OCR usage tracking is working
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import requests
import io
from src.database import SessionLocal
from src.models import UsageRecord

BASE = 'http://localhost:8000'

def test_ocr_tracking():
    # Step 1: Check initial OCR usage count
    db = SessionLocal()
    initial_count = db.query(UsageRecord).filter(UsageRecord.usage_type == 'ocr_scan').count()
    print(f'Initial OCR usage records: {initial_count}')
    db.close()

    # Step 2: Login
    print('\nLogging in as freetest2...')
    login_resp = requests.post(f'{BASE}/api/v1/auth/login', json={
        'username': 'freetest2',
        'password': 'Test123!'
    })

    if login_resp.status_code != 200:
        print(f'Login failed: {login_resp.status_code} - {login_resp.text[:200]}')
        return False

    token = login_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # Step 3: Upload 2 receipts
    print('Uploading 2 receipts...')
    files = []
    for i in range(2):
        # Create a tiny valid JPEG
        mock_jpeg = io.BytesIO(
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
            b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
            b'\x1c $.\\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00'
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
        files.append(('files', (f'finaltest{i+1}.jpg', mock_jpeg, 'image/jpeg')))

    batch_resp = requests.post(f'{BASE}/api/v1/receipts/batch-upload', files=files, headers=headers)
    print(f'Upload response: {batch_resp.status_code}')

    if batch_resp.status_code != 200:
        print(f'Upload failed: {batch_resp.text[:300]}')
        return False

    print('Upload successful!')

    # Step 4: Check OCR usage count AFTER upload
    print('\nChecking database for new UsageRecords...')
    db = SessionLocal()
    final_count = db.query(UsageRecord).filter(UsageRecord.usage_type == 'ocr_scan').count()
    print(f'Final OCR usage records: {final_count}')

    # Show the difference
    new_records = final_count - initial_count
    print(f'\n{"="*70}')
    print('RESULT')
    print("="*70)

    if new_records > 0:
        print(f'✓ SUCCESS! {new_records} new OCR usage record(s) created')
        print('✓ OCR usage tracking is WORKING!')

        # Show the latest records
        latest = db.query(UsageRecord).filter(
            UsageRecord.usage_type == 'ocr_scan'
        ).order_by(UsageRecord.created_at.desc()).limit(3).all()

        print(f'\nLatest OCR usage records:')
        for r in latest:
            print(f'  - ID: {r.id[:8]}... Quantity: {r.quantity}, User: {r.user_id[:8]}..., Created: {r.created_at}')

        db.close()
        return True
    else:
        print(f'✗ FAILED: No new records created')
        print('✗ OCR usage tracking is NOT working')
        db.close()
        return False

if __name__ == '__main__':
    try:
        success = test_ocr_tracking()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'\nERROR: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
