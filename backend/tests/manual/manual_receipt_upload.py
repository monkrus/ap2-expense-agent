"""
Test script to upload sample receipts to expenses
"""

import requests
import os
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"
SAMPLES_DIR = "sample_receipts"


def login(username, password):
    """Login and get token"""
    response = requests.post(
        f"{BASE_URL}/auth/login", json={"username": username, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Login failed: {response.json()}")


def get_organization_id(token):
    """Get user's organization ID"""
    response = requests.get(
        f"{BASE_URL}/organizations", headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        orgs = response.json()
        return orgs[0]["id"] if orgs else None
    return None


def create_expense(token, org_id, vendor, amount, category, description, date):
    """Create a new expense"""
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    data = {
        "vendor": vendor,
        "amount": amount,
        "category": category,
        "description": description,
        "date": date,
    }

    response = requests.post(f"{BASE_URL}/expenses", headers=headers, json=data)

    if response.status_code == 201:
        return response.json()["id"]
    else:
        raise Exception(f"Failed to create expense: {response.json()}")


def upload_receipt(token, org_id, expense_id, receipt_path):
    """Upload a receipt to an expense"""
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    with open(receipt_path, "rb") as f:
        files = {"file": (os.path.basename(receipt_path), f, "image/png")}

        response = requests.post(
            f"{BASE_URL}/receipts/upload/{expense_id}", headers=headers, files=files
        )

    if response.status_code == 200:
        result = response.json()
        return result
    else:
        raise Exception(f"Failed to upload receipt: {response.json()}")


# Sample expenses with corresponding receipts
SAMPLE_EXPENSES = [
    {
        "vendor": "Office Depot",
        "amount": 161.98,
        "category": "OFFICE_SUPPLIES",
        "description": "Office supplies for Q1 - pens, paper, folders",
        "date": "2026-01-01",
        "receipt": "office_supplies_receipt.png",
    },
    {
        "vendor": "The Business Lunch Cafe",
        "amount": 124.20,
        "category": "MEALS",
        "description": "Client lunch meeting - Project discussion",
        "date": "2026-01-01",
        "receipt": "business_lunch_receipt.png",
    },
    {
        "vendor": "Shell Gas Station",
        "amount": 77.76,
        "category": "TRAVEL",
        "description": "Gas for client visit",
        "date": "2025-12-30",
        "receipt": "gas_station_receipt.png",
    },
    {
        "vendor": "Marriott Hotel",
        "amount": 394.20,
        "category": "TRAVEL",
        "description": "Conference accommodation - 2 nights",
        "date": "2025-12-25",
        "receipt": "hotel_receipt.png",
    },
    {
        "vendor": "Best Buy",
        "amount": 361.79,
        "category": "OTHER",
        "description": "Computer accessories for home office",
        "date": "2025-12-22",
        "receipt": "equipment_receipt.png",
    },
    {
        "vendor": "Premium Steakhouse",
        "amount": 333.72,
        "category": "MEALS",
        "description": "Client entertainment - Contract celebration",
        "date": "2025-12-29",
        "receipt": "client_dinner_receipt.png",
    },
]

if __name__ == "__main__":
    print("=== Receipt Upload Test ===\n")

    # Login
    print("1. Logging in as employee1...")
    try:
        token = login("employee1", "TestPass123!")
        print("   [OK] Logged in successfully\n")
    except Exception as e:
        print(f"   [ERROR] {e}")
        exit(1)

    # Get organization
    print("2. Getting organization ID...")
    org_id = get_organization_id(token)
    if not org_id:
        print("   [ERROR] No organization found")
        exit(1)
    print(f"   [OK] Organization ID: {org_id}\n")

    # Check if sample receipts exist
    if not os.path.exists(SAMPLES_DIR):
        print(f"[ERROR] Sample receipts directory '{SAMPLES_DIR}' not found!")
        print(
            "Run 'python generate_sample_receipts.py' first to create sample receipts."
        )
        exit(1)

    # Create expenses and upload receipts
    print("3. Creating expenses with receipts...\n")
    created_count = 0

    for i, expense_data in enumerate(SAMPLE_EXPENSES, 1):
        receipt_path = os.path.join(SAMPLES_DIR, expense_data["receipt"])

        if not os.path.exists(receipt_path):
            print(f"   [{i}] [SKIP] Receipt not found: {expense_data['receipt']}")
            continue

        try:
            # Create expense
            print(
                f"   [{i}] Creating expense: {expense_data['vendor']} (${expense_data['amount']})"
            )
            expense_id = create_expense(
                token,
                org_id,
                vendor=expense_data["vendor"],
                amount=expense_data["amount"],
                category=expense_data["category"],
                description=expense_data["description"],
                date=expense_data["date"],
            )
            print(f"       Expense ID: {expense_id[:8]}...")

            # Upload receipt
            print(f"       Uploading receipt: {expense_data['receipt']}")
            result = upload_receipt(token, org_id, expense_id, receipt_path)

            uploaded_count = result.get("receipts_uploaded", 0)
            print(f"       [OK] {uploaded_count} receipt(s) uploaded successfully\n")
            created_count += 1

        except Exception as e:
            print(f"       [ERROR] {e}\n")

    print(f"=== Summary ===")
    print(f"Created {created_count} expenses with receipts")
    print(f"\nYou can now view these expenses in the app:")
    print(f"  - Login as: employee1 / TestPass123!")
    print(f"  - Go to: 'My Expenses' tab")
    print(f"  - Each expense should have a receipt attached")
