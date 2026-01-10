"""
Show test expenses that should be visible in frontend UI
"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from src.database import SessionLocal
from src.models import Expense, User
from datetime import datetime, timedelta

db = SessionLocal()

print("=" * 70)
print("EXPENSES THAT SHOULD BE VISIBLE IN FRONTEND UI")
print("=" * 70)
print()

# Get recent expenses (last 7 days)
week_ago = datetime.utcnow() - timedelta(days=7)
expenses = db.query(Expense).filter(
    Expense.created_at >= week_ago
).order_by(Expense.created_at.desc()).limit(10).all()

if not expenses:
    print("No recent expenses found (last 7 days)")
    print()
    print("Run these commands to create test data:")
    print("  cd backend")
    print("  python test_direct_ap2_submission.py")
else:
    print(f"Found {len(expenses)} recent expenses:")
    print()

    for i, exp in enumerate(expenses, 1):
        # Get user info
        user = db.query(User).filter(User.id == exp.user_id).first()

        print(f"{i}. Expense: {exp.id[:20]}...")
        print(f"   User: {user.username if user else 'Unknown'}")
        print(f"   Amount: ${exp.amount}")
        print(f"   Vendor: {exp.vendor}")
        print(f"   Category: {exp.category.value if hasattr(exp.category, 'value') else exp.category}")
        print(f"   Status: {exp.status.value if hasattr(exp.status, 'value') else exp.status}")
        print(f"   Auto-approved: {exp.auto_approved}")

        if exp.auto_approved:
            print(f"   Auto-approved via: {exp.auto_approved_via}")
            print(f"   Approved by: {exp.approved_by}")

            # Determine badge color
            if exp.auto_approved_via == 'intent_mandate':
                print("   UI Badge: [APPROVED] [AI Agent] (purple)")
            elif exp.auto_approved_via == 'approval_policy':
                print("   UI Badge: [APPROVED] [Policy] (blue)")
        else:
            status_str = exp.status.value if hasattr(exp.status, 'value') else str(exp.status)
            print(f"   UI Badge: [{status_str.upper()}] (no auto-approval badge)")

        print(f"   Created: {exp.created_at}")
        print()

print("-" * 70)
print("HOW TO TEST IN UI:")
print("-" * 70)
print()
print("1. Start frontend: cd frontend && npm run dev")
print("2. Open browser: http://localhost:5173")
print("3. Login as: adminfree (or user shown above)")
print("4. Go to Employee Dashboard")
print("5. Look for expenses listed above")
print()
print("EXPECTED BADGES:")
print("  - Intent Mandate auto-approval: Purple 'AI Agent' badge")
print("  - Approval Policy auto-approval: Blue 'Policy' badge")
print("  - Manual/Pending: No auto-approval badge")
print()

# Show Intent Mandate info
from src.models import IntentMandate

active_mandates = db.query(IntentMandate).filter(
    IntentMandate.status == 'active'
).all()

if active_mandates:
    print("-" * 70)
    print(f"ACTIVE INTENT MANDATES: {len(active_mandates)}")
    print("-" * 70)
    print()

    for mandate in active_mandates[:3]:
        import json
        constraints = json.loads(mandate.constraints) if isinstance(mandate.constraints, str) else mandate.constraints

        print(f"Mandate: {mandate.id[:20]}...")
        print(f"  User: {mandate.user_id}")
        print(f"  Constraints:")
        if 'merchant' in constraints:
            print(f"    - Merchant: {constraints['merchant']}")
        if 'category' in constraints:
            print(f"    - Category: {constraints['category']}")
        if 'max_amount' in constraints:
            print(f"    - Max Amount: ${constraints['max_amount']}")
        if 'monthly_limit' in constraints:
            print(f"    - Monthly Limit: ${constraints['monthly_limit']}")
        print(f"  Expires: {mandate.expiration}")
        print()

    print("To trigger auto-approval, submit expense matching above constraints!")
else:
    print("-" * 70)
    print("NO ACTIVE INTENT MANDATES")
    print("-" * 70)
    print()
    print("Create one with:")
    print("  cd backend")
    print("  python test_intent_mandate_autoapproval.py")

db.close()
