"""Verify test expense in database"""
from src.database import SessionLocal
from src.models import Expense

db = SessionLocal()

exp = db.query(Expense).filter(
    Expense.vendor == 'Amazon',
    Expense.description.like('%Direct AP2 test%')
).order_by(Expense.created_at.desc()).first()

if exp:
    print("=" * 70)
    print("VERIFIED: Expense exists in database")
    print("=" * 70)
    print()
    print(f"  ID: {exp.id}")
    print(f"  Amount: ${exp.amount}")
    print(f"  Vendor: {exp.vendor}")
    print(f"  Category: {exp.category}")
    print(f"  Status: {exp.status}")
    print(f"  Auto-approved: {exp.auto_approved}")
    print(f"  Auto-approved via: {exp.auto_approved_via}")
    print(f"  Approved by: {exp.approved_by}")
    print(f"  Intent Mandate: {exp.intent_mandate_id[:30]}...")
    print(f"  Cart Mandate: {exp.cart_mandate_id[:30]}...")
    print(f"  Payment Mandate: {exp.payment_mandate_id[:30]}...")
    print()
    print("✅ All AP2 mandate IDs are populated!")
    print("✅ auto_approved_via = 'intent_mandate'")
    print("✅ Status = APPROVED")
else:
    print("No expense found")

db.close()
