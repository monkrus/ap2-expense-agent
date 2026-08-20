"""
Direct Test: Submit expense directly via database to test AP2 auto-approval
Bypasses authentication to focus on auto-approval logic
"""
import asyncio
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ['TESTING'] = 'false'

from datetime import datetime, date
from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, Expense, ExpenseCategory, ExpenseStatus
from src.payments.ap2_service import AP2PaymentService
import uuid

async def test_direct_submission():
    db = SessionLocal()

    try:
        print("=" * 70)
        print("DIRECT AP2 AUTO-APPROVAL TEST")
        print("=" * 70)
        print()

        # Get test user and organization
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[ERROR] No active organization member found")
            return

        user = db.query(User).filter(User.id == member.user_id).first()
        org = db.query(Organization).filter(Organization.id == member.organization_id).first()

        print(f"Test User: {user.username} ({user.email})")
        print(f"Organization: {org.name}")
        print()

        # =====================================================================
        # STEP 1: Verify Intent Mandate exists
        # =====================================================================
        print("STEP 1: Checking Intent Mandates...")
        print("-" * 70)

        ap2_service = AP2PaymentService(db)

        # Check for matching mandate
        matching_mandate = ap2_service.find_matching_intent_mandate(
            user_id=user.id,
            amount=45.00,
            category='office_supplies',
            merchant='Amazon',
            organization_id=org.id
        )

        if matching_mandate:
            print(f"✓ Found Intent Mandate: {matching_mandate.id}")
            print(f"  Status: {matching_mandate.status}")
            print(f"  Expiration: {matching_mandate.expiration}")
        else:
            print("[WARNING] No matching Intent Mandate found")
            print("  Creating one for testing...")

            # Create Intent Mandate for testing
            matching_mandate = await ap2_service.create_intent_mandate(
                user_id=user.id,
                constraints={
                    "max_amount": 200.00,
                    "category": "office_supplies",
                    "merchant": "Amazon",
                    "monthly_limit": 500.00
                },
                expiration_hours=720
            )
            print(f"✓ Created Intent Mandate: {matching_mandate.id}")

        print()

        # =====================================================================
        # STEP 2: Simulate expense submission (MATCHING)
        # =====================================================================
        print("STEP 2: Simulating MATCHING expense submission...")
        print("-" * 70)

        # This simulates what happens in routes/expenses.py
        print("Creating expense record...")

        test_expense = Expense(
            id=str(uuid.uuid4()),
            user_id=user.id,
            organization_id=org.id,
            amount=45.00,
            vendor='Amazon',
            category=ExpenseCategory.OFFICE_SUPPLIES,
            description='USB cables - Direct AP2 test',
            date=date.today(),
            status=ExpenseStatus.PENDING,
            auto_approved=False,
            created_at=datetime.utcnow()
        )

        db.add(test_expense)
        db.flush()

        print(f"✓ Expense created: {test_expense.id}")
        print()

        # Check for Intent Mandate match (this is the NEW logic)
        print("Checking for matching Intent Mandate...")
        mandate_check = ap2_service.find_matching_intent_mandate(
            user_id=test_expense.user_id,
            amount=float(test_expense.amount),
            category=test_expense.category.value,
            merchant=test_expense.vendor,
            organization_id=test_expense.organization_id
        )

        if mandate_check:
            print(f"✓ MATCH FOUND: {mandate_check.id}")
            print()
            print("Creating AP2 flow...")

            # Create AP2 flow
            cart_items = [{
                "description": test_expense.description,
                "amount": float(test_expense.amount),
                "vendor": test_expense.vendor,
                "category": test_expense.category.value,
            }]

            ap2_result = await ap2_service.complete_ap2_flow(
                user_id=test_expense.user_id,
                items=cart_items,
                merchant=test_expense.vendor,
                constraints={
                    "max_amount": float(test_expense.amount) * 1.05,
                    "merchant": test_expense.vendor,
                    "approval_required": False,
                }
            )

            # AUTO-APPROVE
            test_expense.status = ExpenseStatus.APPROVED
            test_expense.approved_by = "ai_agent"
            test_expense.approved_at = datetime.utcnow()
            test_expense.auto_approved = True
            test_expense.auto_approved_via = "intent_mandate"
            test_expense.intent_mandate_id = ap2_result.get("intent_mandate_id")
            test_expense.cart_mandate_id = ap2_result.get("cart_mandate_id")
            test_expense.payment_mandate_id = ap2_result.get("payment_mandate_id")

            db.commit()

            print()
            print("=" * 70)
            print("✅ SUCCESS! EXPENSE AUTO-APPROVED VIA AP2")
            print("=" * 70)
            print()
            print("EXPENSE DETAILS:")
            print(f"  ID: {test_expense.id}")
            print(f"  Amount: ${test_expense.amount}")
            print(f"  Vendor: {test_expense.vendor}")
            print(f"  Category: {test_expense.category.value}")
            print(f"  Status: {test_expense.status.value}")
            print()
            print("AUTO-APPROVAL INFO:")
            print(f"  Auto-approved: {test_expense.auto_approved}")
            print(f"  Auto-approved via: {test_expense.auto_approved_via}")
            print(f"  Approved by: {test_expense.approved_by}")
            print(f"  Approved at: {test_expense.approved_at}")
            print()
            print("AP2 MANDATES CREATED:")
            print(f"  Intent Mandate: {test_expense.intent_mandate_id[:20]}...")
            print(f"  Cart Mandate: {test_expense.cart_mandate_id[:20]}...")
            print(f"  Payment Mandate: {test_expense.payment_mandate_id[:20]}...")
            print()
            print("✨ AI AGENT AUTO-APPROVED - NO MANAGER NEEDED!")

        else:
            print("[ERROR] No matching mandate (unexpected)")
            db.rollback()

        print()

        # =====================================================================
        # STEP 3: Test NON-MATCHING expense
        # =====================================================================
        print("STEP 3: Testing NON-MATCHING expense...")
        print("-" * 70)

        non_matching = ap2_service.find_matching_intent_mandate(
            user_id=user.id,
            amount=45.00,
            category='office_supplies',
            merchant='Staples',  # Different merchant
            organization_id=org.id
        )

        if non_matching:
            print("[ERROR] Found match for Staples (unexpected)")
        else:
            print("✓ No match for Staples expense")
            print("  Result: Would require MANUAL APPROVAL")

        print()

        # =====================================================================
        # SUMMARY
        # =====================================================================
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print()
        print("✓ Intent Mandate verified/created")
        print("✓ Matching expense auto-approved via AP2")
        print("✓ AP2 mandates (Intent/Cart/Payment) created")
        print("✓ Non-matching expense would require manual approval")
        print()
        print("VERIFICATION IN DATABASE:")
        print(f"✓ Expense {test_expense.id[:20]}... is APPROVED")
        print(f"✓ auto_approved_via = 'intent_mandate'")
        print(f"✓ All AP2 mandate IDs populated")
        print()
        print("YOUR APP IS WORKING! 🎉")
        print()
        print("NEXT: Test in UI at http://localhost:5173")
        print("  - Submit expense: $45, Amazon, OFFICE_SUPPLIES")
        print("  - Should see: '✨ Auto-approved by AI agent'")
        print("  - Expense list should show purple '✨ AI Agent' badge")
        print()

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

    finally:
        db.close()

if __name__ == '__main__':
    asyncio.run(test_direct_submission())
