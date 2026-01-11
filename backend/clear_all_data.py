"""
Clear all data from the database - complete reset

This will delete:
- All users
- All organizations
- All expenses
- All receipts
- All mandates
- All sessions
- All tokens
- All audit logs
- Everything else (cascading deletes)
"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import (
    User, Organization, OrganizationMember, OrganizationInvitation,
    Expense, Receipt, ExpenseComment,
    IntentMandate, CartMandate, PaymentMandate,
    RefreshToken, PasswordResetToken, Session as UserSession,
    AuditLog, ApprovalPolicy, Budget, BudgetAlert,
    RecurringExpenseTemplate, ScheduledExpense, ExpenseNotification,
    Notification
)

db = SessionLocal()

print("=" * 70)
print("CLEARING ALL DATA FROM DATABASE")
print("=" * 70)
print()

try:
    # Count everything before deletion
    print("Current database state:")
    print("-" * 70)

    counts = {
        "Users": db.query(User).count(),
        "Organizations": db.query(Organization).count(),
        "Organization Members": db.query(OrganizationMember).count(),
        "Expenses": db.query(Expense).count(),
        "Receipts": db.query(Receipt).count(),
        "Intent Mandates": db.query(IntentMandate).count(),
        "Cart Mandates": db.query(CartMandate).count(),
        "Payment Mandates": db.query(PaymentMandate).count(),
        "Approval Policies": db.query(ApprovalPolicy).count(),
        "Budgets": db.query(Budget).count(),
        "Refresh Tokens": db.query(RefreshToken).count(),
        "Sessions": db.query(UserSession).count(),
        "Audit Logs": db.query(AuditLog).count(),
        "Notifications": db.query(Notification).count(),
    }

    for item, count in counts.items():
        print(f"  {item}: {count}")

    total_records = sum(counts.values())
    print("-" * 70)
    print(f"Total records: {total_records}")
    print()

    if total_records == 0:
        print("✅ Database is already empty - nothing to delete")
        db.close()
        exit(0)

    # Delete in proper order to avoid foreign key issues
    print("Deleting data...")
    print("-" * 70)

    # Delete child records first
    deleted = {
        "Notifications": db.query(Notification).delete(),
        "Expense Notifications": db.query(ExpenseNotification).delete(),
        "Scheduled Expenses": db.query(ScheduledExpense).delete(),
        "Recurring Templates": db.query(RecurringExpenseTemplate).delete(),
        "Budget Alerts": db.query(BudgetAlert).delete(),
        "Budgets": db.query(Budget).delete(),
        "Expense Comments": db.query(ExpenseComment).delete(),
        "Receipts": db.query(Receipt).delete(),
        "Expenses": db.query(Expense).delete(),
        "Payment Mandates": db.query(PaymentMandate).delete(),
        "Cart Mandates": db.query(CartMandate).delete(),
        "Intent Mandates": db.query(IntentMandate).delete(),
        "Approval Policies": db.query(ApprovalPolicy).delete(),
        "Organization Invitations": db.query(OrganizationInvitation).delete(),
        "Organization Members": db.query(OrganizationMember).delete(),
        "Organizations": db.query(Organization).delete(),
        "Sessions": db.query(UserSession).delete(),
        "Password Reset Tokens": db.query(PasswordResetToken).delete(),
        "Refresh Tokens": db.query(RefreshToken).delete(),
        "Audit Logs": db.query(AuditLog).delete(),
        "Users": db.query(User).delete(),
    }

    for item, count in deleted.items():
        if count > 0:
            print(f"  ✅ Deleted {count} {item}")

    # Commit all deletions
    db.commit()

    print("-" * 70)
    print()

    # Verify deletion
    print("Verifying deletion...")
    print("-" * 70)

    verification = {
        "Users": db.query(User).count(),
        "Organizations": db.query(Organization).count(),
        "Expenses": db.query(Expense).count(),
        "Receipts": db.query(Receipt).count(),
        "Sessions": db.query(UserSession).count(),
        "Audit Logs": db.query(AuditLog).count(),
    }

    all_zero = all(count == 0 for count in verification.values())

    for item, count in verification.items():
        status = "✅" if count == 0 else "❌"
        print(f"  {status} {item}: {count}")

    print("-" * 70)
    print()

    if all_zero:
        print("=" * 70)
        print("✅ SUCCESS - ALL DATA CLEARED")
        print("=" * 70)
        print()
        print("Database is now completely empty.")
        print("All counters should show 0.")
        print()
        print("You can now:")
        print("  1. Check the UI to verify all numbers show 0")
        print("  2. Create fresh test users when ready")
        print()
    else:
        print("=" * 70)
        print("⚠️  WARNING - Some records may remain")
        print("=" * 70)

except Exception as e:
    db.rollback()
    print()
    print("=" * 70)
    print(f"❌ ERROR: {str(e)}")
    print("=" * 70)
    raise
finally:
    db.close()
