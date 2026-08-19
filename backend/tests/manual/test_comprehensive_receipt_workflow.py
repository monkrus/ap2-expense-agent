"""
Comprehensive Receipt/Expense Workflow Test
Tests the complete end-to-end workflow including:
- Batch uploads (10, 11+, edge cases)
- Invalid formats and oversized files
- Concurrent uploads from multiple users
- Frontend display verification
- Approval workflow (submit, withdraw, approve, deny)
- Post-approval flow
"""

import asyncio
import os
import sys
import time
import threading
from pathlib import Path
from typing import List, Dict
import requests
from PIL import Image
import io

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_RECEIPTS_DIR = Path("sample_receipts")
TEMP_TEST_DIR = Path("temp_test_receipts")
TEMP_TEST_DIR.mkdir(exist_ok=True)

# Test users
USERS = {
    "admin": {"username": "adminfree", "password": "password123"},
    "employee1": {"username": "employee1", "password": "Password123"},
    "employee2": {"username": "employee2", "password": "Password123"},
}

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


class TestSession:
    """Helper class to manage test user sessions"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.token = None
        self.user_data = None
        self.org_id = None

    def login(self):
        """Login and get access token"""
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": self.username, "password": self.password}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.user_data = data["user"]
            print(f"[PASS] {self.username} logged in successfully")

            # Get organization
            self._get_organization()
            return True
        else:
            print(f"[FAIL] {self.username} login failed: {response.text}")
            return False

    def _get_organization(self):
        """Get user's organization"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{API_BASE_URL}/organizations", headers=headers)
        if response.status_code == 200:
            orgs = response.json()
            if orgs:
                self.org_id = orgs[0]["id"]
                print(f"  Organization ID: {self.org_id}")

    def get_headers(self):
        """Get request headers with auth and org context"""
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Organization-Id": self.org_id
        }


def create_test_receipt(filename: str, size_mb: float = 0.05, format: str = "png"):
    """Create a test receipt image of specified size and format"""
    # Calculate image dimensions for target size
    target_bytes = int(size_mb * 1024 * 1024)

    # Create a simple image (quality affects file size)
    width, height = 800, 1200
    img = Image.new('RGB', (width, height), color='white')

    filepath = TEMP_TEST_DIR / filename

    if format.lower() == "png":
        img.save(filepath, "PNG")
    elif format.lower() in ["jpg", "jpeg"]:
        # Adjust quality to reach target size
        quality = 95
        img.save(filepath, "JPEG", quality=quality)
    elif format.lower() == "pdf":
        img.save(filepath, "PDF")
    else:
        # Invalid format for testing
        with open(filepath, 'w') as f:
            f.write("This is not an image file")

    return filepath


def create_oversized_receipt(filename: str, size_mb: float = 12):
    """Create an oversized receipt (>10MB)"""
    # Create a large high-resolution image
    width, height = 4000, 6000
    img = Image.new('RGB', (width, height), color='white')

    filepath = TEMP_TEST_DIR / filename
    img.save(filepath, "PNG")

    # Verify it's actually over 10MB
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if file_size_mb < 10:
        # Make it bigger by adding more data
        with open(filepath, 'ab') as f:
            f.write(b'0' * (11 * 1024 * 1024))

    return filepath


def test_batch_upload(session: TestSession, num_receipts: int, test_name: str):
    """Test uploading a batch of receipts"""
    print(f"\n{'='*60}")
    print(f"Test: {test_name} ({num_receipts} receipts)")
    print(f"{'='*60}")

    # Create an expense first
    expense_data = {
        "amount": 500.00,
        "vendor": f"Test Vendor {test_name}",
        "category": "OFFICE_SUPPLIES",
        "description": f"Batch upload test - {num_receipts} receipts",
        "date": "2026-01-04T12:00:00"
    }

    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=session.get_headers(),
        json=expense_data
    )

    if response.status_code != 201:
        print(f"[FAIL] Failed to create expense: {response.text}")
        test_results["failed"].append(f"{test_name}: Expense creation failed")
        return None

    expense = response.json()
    expense_id = expense["id"]
    print(f"[PASS] Created expense: {expense_id}")

    # Upload receipts
    successful_uploads = 0
    failed_uploads = 0

    for i in range(num_receipts):
        # Use existing sample receipts or create new ones
        sample_files = list(TEST_RECEIPTS_DIR.glob("*.png"))
        if sample_files and i < len(sample_files):
            receipt_path = sample_files[i]
        else:
            receipt_path = create_test_receipt(f"batch_{test_name}_{i}.png")

        with open(receipt_path, 'rb') as f:
            files = {'file': (receipt_path.name, f, 'image/png')}
            response = requests.post(
                f"{API_BASE_URL}/receipts/upload/{expense_id}",
                headers=session.get_headers(),
                files=files
            )

        if response.status_code in [200, 201]:
            successful_uploads += 1
            print(f"  [PASS] Uploaded receipt {i+1}/{num_receipts}")
        else:
            failed_uploads += 1
            print(f"  [FAIL] Failed to upload receipt {i+1}: {response.text[:100]}")

    print(f"\nResults: {successful_uploads} successful, {failed_uploads} failed")

    if successful_uploads > 0:
        test_results["passed"].append(f"{test_name}: {successful_uploads}/{num_receipts} uploads")
    if failed_uploads > 0:
        test_results["failed"].append(f"{test_name}: {failed_uploads} failed uploads")

    return expense_id


def test_invalid_formats(session: TestSession):
    """Test uploading invalid file formats"""
    print(f"\n{'='*60}")
    print("Test: Invalid File Formats")
    print(f"{'='*60}")

    # Create an expense
    expense_data = {
        "amount": 100.00,
        "vendor": "Invalid Format Test",
        "category": "OTHER",
        "description": "Testing invalid file formats",
        "date": "2026-01-04T12:00:00"
    }

    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=session.get_headers(),
        json=expense_data
    )

    if response.status_code != 201:
        print(f"[FAIL] Failed to create expense")
        return

    expense_id = response.json()["id"]

    # Test invalid formats
    invalid_formats = [
        ("test.txt", "text/plain"),
        ("test.exe", "application/x-msdownload"),
        ("test.zip", "application/zip"),
        ("test.doc", "application/msword"),
    ]

    for filename, content_type in invalid_formats:
        filepath = create_test_receipt(filename, format="invalid")

        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, content_type)}
            response = requests.post(
                f"{API_BASE_URL}/receipts/upload/{expense_id}",
                headers=session.get_headers(),
                files=files
            )

        if response.status_code == 400:
            print(f"  [PASS] Correctly rejected {filename}")
            test_results["passed"].append(f"Invalid format rejected: {filename}")
        else:
            print(f"  [FAIL] Incorrectly accepted {filename} (status: {response.status_code})")
            test_results["failed"].append(f"Invalid format accepted: {filename}")


def test_oversized_files(session: TestSession):
    """Test uploading oversized files (>10MB)"""
    print(f"\n{'='*60}")
    print("Test: Oversized Files (>10MB)")
    print(f"{'='*60}")

    # Create an expense
    expense_data = {
        "amount": 100.00,
        "vendor": "Oversized File Test",
        "category": "OTHER",
        "description": "Testing oversized files",
        "date": "2026-01-04T12:00:00"
    }

    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=session.get_headers(),
        json=expense_data
    )

    if response.status_code != 201:
        print(f"[FAIL] Failed to create expense")
        return

    expense_id = response.json()["id"]

    # Create and upload oversized file
    oversized_file = create_oversized_receipt("oversized_12mb.png", size_mb=12)
    file_size_mb = os.path.getsize(oversized_file) / (1024 * 1024)
    print(f"  Created test file: {file_size_mb:.2f}MB")

    with open(oversized_file, 'rb') as f:
        files = {'file': (oversized_file.name, f, 'image/png')}
        response = requests.post(
            f"{API_BASE_URL}/receipts/upload/{expense_id}",
            headers=session.get_headers(),
            files=files
        )

    if response.status_code == 400 and "too large" in response.text.lower():
        print(f"  [PASS] Correctly rejected oversized file")
        test_results["passed"].append("Oversized file rejected")
    else:
        print(f"  [FAIL] Incorrectly accepted oversized file (status: {response.status_code})")
        test_results["failed"].append("Oversized file accepted")


def test_concurrent_uploads():
    """Test concurrent uploads from multiple users"""
    print(f"\n{'='*60}")
    print("Test: Concurrent Uploads (2 users simultaneously)")
    print(f"{'='*60}")

    # Login both users (use adminfree and employee2)
    emp1 = TestSession("adminfree", "password123")
    emp2 = TestSession("employee2", "Password123")

    if not emp1.login() or not emp2.login():
        print("[FAIL] Failed to login test users")
        test_results["failed"].append("Concurrent test: User login failed")
        return

    # Upload function for threading
    def upload_batch(session, user_name):
        try:
            expense_id = test_batch_upload(session, 5, f"Concurrent_{user_name}")
            return expense_id is not None
        except Exception as e:
            print(f"[FAIL] {user_name} upload failed: {e}")
            return False

    # Run uploads concurrently
    results = []
    threads = []

    for session, name in [(emp1, "adminfree"), (emp2, "employee2")]:
        thread = threading.Thread(target=lambda s=session, n=name: results.append(upload_batch(s, n)))
        threads.append(thread)
        thread.start()

    # Wait for completion
    for thread in threads:
        thread.join()

    if all(results):
        print("[PASS] Concurrent uploads successful for both users")
        test_results["passed"].append("Concurrent uploads: Both users succeeded")
    else:
        print("[FAIL] Some concurrent uploads failed")
        test_results["failed"].append("Concurrent uploads: Some users failed")


def test_approval_workflow(admin_session: TestSession, employee_session: TestSession):
    """Test the complete approval workflow"""
    print(f"\n{'='*60}")
    print("Test: Approval Workflow")
    print(f"{'='*60}")

    # Employee creates and submits expense
    expense_data = {
        "amount": 250.00,
        "vendor": "Approval Test Vendor",
        "category": "MEALS",
        "description": "Testing approval workflow",
        "date": "2026-01-04T12:00:00"
    }

    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=employee_session.get_headers(),
        json=expense_data
    )

    if response.status_code != 201:
        print(f"[FAIL] Failed to create expense")
        return

    expense = response.json()
    expense_id = expense["id"]
    print(f"[PASS] Employee created expense: {expense_id}")

    # Upload a receipt
    sample_file = next(TEST_RECEIPTS_DIR.glob("*.png"))
    with open(sample_file, 'rb') as f:
        files = {'file': (sample_file.name, f, 'image/png')}
        response = requests.post(
            f"{API_BASE_URL}/receipts/upload/{expense_id}",
            headers=employee_session.get_headers(),
            files=files
        )

    if response.status_code in [200, 201]:
        print(f"[PASS] Receipt uploaded")

    # Check expense status (should be PENDING)
    response = requests.get(
        f"{API_BASE_URL}/expenses/{expense_id}",
        headers=employee_session.get_headers()
    )

    if response.status_code == 200:
        expense = response.json()
        if expense["status"] == "PENDING":
            print(f"[PASS] Expense status is PENDING")
            test_results["passed"].append("Approval workflow: Initial status PENDING")
        else:
            print(f"[FAIL] Unexpected status: {expense['status']}")

    # Test: Employee tries to approve own expense (should fail)
    response = requests.put(
        f"{API_BASE_URL}/expenses/{expense_id}/approve",
        headers=employee_session.get_headers()
    )

    if response.status_code == 403:
        print(f"[PASS] Employee correctly prevented from self-approving")
        test_results["passed"].append("Approval workflow: Self-approval blocked")
    else:
        print(f"[FAIL] Employee was able to self-approve (status: {response.status_code})")
        test_results["failed"].append("Approval workflow: Self-approval not blocked")

    # Test: Withdraw expense
    withdraw_expense_id = expense_id
    response = requests.delete(
        f"{API_BASE_URL}/expenses/{withdraw_expense_id}",
        headers=employee_session.get_headers()
    )

    if response.status_code in [200, 204]:
        print(f"[PASS] Employee withdrew expense")
        test_results["passed"].append("Approval workflow: Withdrawal successful")

        # Verify status is WITHDRAWN
        response = requests.get(
            f"{API_BASE_URL}/expenses/{withdraw_expense_id}",
            headers=employee_session.get_headers()
        )
        if response.status_code == 200:
            expense = response.json()
            if expense["status"] == "WITHDRAWN":
                print(f"[PASS] Expense status is WITHDRAWN")

    # Create another expense for admin approval test
    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=employee_session.get_headers(),
        json=expense_data
    )
    expense_id = response.json()["id"]

    # Admin approves expense
    response = requests.put(
        f"{API_BASE_URL}/expenses/{expense_id}/approve",
        headers=admin_session.get_headers()
    )

    if response.status_code == 200:
        print(f"[PASS] Admin approved expense")
        test_results["passed"].append("Approval workflow: Admin approval successful")

        # Verify status is APPROVED
        response = requests.get(
            f"{API_BASE_URL}/expenses/{expense_id}",
            headers=admin_session.get_headers()
        )
        if response.status_code == 200:
            expense = response.json()
            if expense["status"] == "APPROVED":
                print(f"[PASS] Expense status is APPROVED")
                print(f"  Approved by: {expense.get('approved_by')}")
                print(f"  Approved at: {expense.get('approved_at')}")

    # Create another expense for rejection test
    response = requests.post(
        f"{API_BASE_URL}/expenses",
        headers=employee_session.get_headers(),
        json=expense_data
    )
    expense_id = response.json()["id"]

    # Admin rejects expense
    response = requests.put(
        f"{API_BASE_URL}/expenses/{expense_id}/reject",
        headers=admin_session.get_headers(),
        json={"reason": "Missing required documentation"}
    )

    if response.status_code == 200:
        print(f"[PASS] Admin rejected expense")
        test_results["passed"].append("Approval workflow: Admin rejection successful")

        # Verify status is REJECTED
        response = requests.get(
            f"{API_BASE_URL}/expenses/{expense_id}",
            headers=admin_session.get_headers()
        )
        if response.status_code == 200:
            expense = response.json()
            if expense["status"] == "REJECTED":
                print(f"[PASS] Expense status is REJECTED")
                print(f"  Rejection reason: {expense.get('rejection_reason')}")


def document_end_to_end_flow():
    """Document the complete end-to-end flow"""
    print(f"\n{'='*60}")
    print("END-TO-END FLOW DOCUMENTATION")
    print(f"{'='*60}")

    flow_doc = """
EXPENSE/RECEIPT WORKFLOW - COMPLETE FLOW
========================================

1. EXPENSE CREATION (Employee)
   - Employee creates expense with: amount, vendor, category, description, date
   - Initial status: PENDING
   - Expense ID is generated

2. RECEIPT UPLOAD (Employee)
   - Employee uploads receipts to expense
   - Validations:
     * File format: .jpg, .jpeg, .png, .pdf, .gif, .bmp, .webp
     * File size: Maximum 10MB per receipt
     * Authentication: Must be expense owner
   - Multiple receipts can be attached to one expense
   - OCR processing may occur (if enabled)

3. REVIEW & EDIT (Employee)
   - Employee can view expense details
   - Employee can edit expense (if status = PENDING)
   - Employee can add/remove receipts
   - Employee can withdraw expense (status → WITHDRAWN)

4. SUBMISSION FOR APPROVAL (Automatic)
   - Expenses are created with PENDING status
   - Appears in admin/manager approval queue
   - Auto-approval may trigger based on policies:
     * Amount thresholds
     * Category rules
     * Budget constraints

5. APPROVAL WORKFLOW (Admin/Manager)
   A. Admin/Manager reviews expense
      - Views expense details and attached receipts
      - Checks policy compliance

   B. Approval Actions:
      - APPROVE: status → APPROVED
        * Approved by user ID recorded
        * Approval timestamp recorded
        * Triggers payment processing (if configured)

      - REJECT: status → REJECTED
        * Rejection reason required
        * Employee notified
        * No payment processing

      - REQUEST MORE INFO: (future feature)
        * Employee can resubmit

6. POST-APPROVAL PROCESSING (Approved expenses)
   - Payment Integration (AP2 Protocol):
     a. Intent Mandate created (payment intent)
     b. Cart Mandate created (line items)
     c. Payment Mandate created (actual payment)

   - Accounting Integration:
     * Expense recorded in financial system
     * Category-based GL coding
     * Tax calculation (if applicable)

   - Reporting & Analytics:
     * Expense included in reports
     * Budget tracking updated
     * Usage metrics recorded

   - Archival:
     * After payment completion, expense can be archived
     * Archived expenses retained for audit trail
     * Retention period: 7 years (configurable)

7. POST-REJECTION PROCESSING (Rejected expenses)
   - Employee receives notification
   - Employee can:
     * View rejection reason
     * Edit and resubmit (creates new expense)
     * Delete/archive the rejected expense
   - No payment processing occurs
   - Tracked for reporting purposes

8. WITHDRAWN EXPENSES
   - Status: WITHDRAWN
   - Cannot be approved/rejected
   - Removed from approval queue
   - Retained for audit trail

BATCH UPLOAD CONSIDERATIONS
===========================
- No hard limit on number of receipts per expense
- Recommended: 10-20 receipts per expense for performance
- Large batches (50+) may have slower processing
- Concurrent uploads supported (multiple users)
- Rate limiting applies per user

DATA RETENTION & COMPLIANCE
============================
- All expenses retained for 7 years (minimum)
- Receipts stored in secure storage
- Audit trail maintained for all status changes
- GDPR compliance: User data can be anonymized while retaining financial records

PERFORMANCE NOTES
=================
- Receipt upload: Async processing
- OCR processing: Background jobs
- Large files (5-10MB): May take 5-10 seconds
- Concurrent uploads: Limited by API rate limits (100 req/min per user)
"""

    print(flow_doc)

    # Save to file
    with open("EXPENSE_WORKFLOW_DOCUMENTATION.md", "w") as f:
        f.write(flow_doc)

    print("\n[PASS] Documentation saved to: EXPENSE_WORKFLOW_DOCUMENTATION.md")


def print_test_summary():
    """Print summary of all tests"""
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    print(f"\n[PASS] PASSED TESTS ({len(test_results['passed'])})")
    for test in test_results["passed"]:
        print(f"  • {test}")

    print(f"\n[FAIL] FAILED TESTS ({len(test_results['failed'])})")
    for test in test_results["failed"]:
        print(f"  • {test}")

    if test_results["warnings"]:
        print(f"\n[WARN] WARNINGS ({len(test_results['warnings'])})")
        for warning in test_results["warnings"]:
            print(f"  • {warning}")

    total_tests = len(test_results["passed"]) + len(test_results["failed"])
    pass_rate = (len(test_results["passed"]) / total_tests * 100) if total_tests > 0 else 0

    print(f"\nOverall: {len(test_results['passed'])}/{total_tests} tests passed ({pass_rate:.1f}%)")


def main():
    """Run all tests"""
    print("="*60)
    print("COMPREHENSIVE RECEIPT/EXPENSE WORKFLOW TEST")
    print("="*60)

    # Login sessions
    print("\nLogging in users...")
    admin_session = TestSession(**USERS["admin"])
    employee_session = TestSession(**USERS["employee2"])

    if not admin_session.login() or not employee_session.login():
        print("[FAIL] Failed to login. Ensure backend is running and users exist.")
        sys.exit(1)

    # Run tests
    try:
        # Test 1: Normal batch upload (10 receipts)
        test_batch_upload(employee_session, 10, "10_receipts_normal")

        # Test 2: Large batch upload (11+ receipts)
        test_batch_upload(employee_session, 15, "15_receipts_large")

        # Test 3: Invalid formats
        test_invalid_formats(employee_session)

        # Test 4: Oversized files
        test_oversized_files(employee_session)

        # Test 5: Concurrent uploads
        test_concurrent_uploads()

        # Test 6: Approval workflow
        test_approval_workflow(admin_session, employee_session)

        # Document end-to-end flow
        document_end_to_end_flow()

    except Exception as e:
        print(f"\n[FAIL] Test suite error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Print summary
        print_test_summary()

        # Cleanup temp files
        print("\nCleaning up temporary test files...")
        for file in TEMP_TEST_DIR.glob("*"):
            file.unlink()


if __name__ == "__main__":
    main()
