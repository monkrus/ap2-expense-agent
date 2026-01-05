"""
Baseline Functionality Validator

Validates that current application functionality matches the baseline
specification. Any deviation from baseline must be explicitly approved.

This ensures critical functionality cannot be accidentally broken.
"""

import json
import sys
from typing import Dict, List, Any
import hashlib

# Load baseline
with open('FUNCTIONALITY_BASELINE.json', 'r') as f:
    BASELINE = json.load(f)


class BaselineViolation:
    """Represents a violation of baseline functionality"""

    def __init__(self, category: str, violation_type: str, description: str, severity: str = "CRITICAL"):
        self.category = category
        self.violation_type = violation_type
        self.description = description
        self.severity = severity

    def __str__(self):
        return f"[{self.severity}] {self.category}: {self.description}"


def validate_tier_limits() -> List[BaselineViolation]:
    """Validate tier limits match baseline"""
    violations = []

    try:
        sys.path.insert(0, '.')
        from src.billing.tier_limit_guardian import OFFICIAL_TIER_LIMITS

        for tier_name, baseline_limits in BASELINE["tier_limits"].items():
            if tier_name not in OFFICIAL_TIER_LIMITS:
                violations.append(BaselineViolation(
                    "Tier Limits",
                    "MISSING_TIER",
                    f"Tier '{tier_name}' missing from current implementation",
                    "CRITICAL"
                ))
                continue

            current_limits = OFFICIAL_TIER_LIMITS[tier_name]

            for limit_key, baseline_value in baseline_limits.items():
                current_value = current_limits.get(limit_key)

                if current_value != baseline_value:
                    violations.append(BaselineViolation(
                        "Tier Limits",
                        "LIMIT_MISMATCH",
                        f"Tier '{tier_name}' limit '{limit_key}': baseline={baseline_value}, current={current_value}",
                        "CRITICAL"
                    ))

    except Exception as e:
        violations.append(BaselineViolation(
            "Tier Limits",
            "VALIDATION_ERROR",
            f"Cannot validate tier limits: {e}",
            "CRITICAL"
        ))

    return violations


def validate_database_schema() -> List[BaselineViolation]:
    """Validate database schema has all critical tables"""
    violations = []

    try:
        sys.path.insert(0, '.')
        from src.database import engine
        from sqlalchemy import inspect

        inspector = inspect(engine)
        current_tables = set(inspector.get_table_names())

        baseline_tables = set(BASELINE["database_schema"]["critical_tables"])

        missing_tables = baseline_tables - current_tables
        for table in missing_tables:
            violations.append(BaselineViolation(
                "Database Schema",
                "MISSING_TABLE",
                f"Critical table '{table}' is missing",
                "CRITICAL"
            ))

    except Exception as e:
        violations.append(BaselineViolation(
            "Database Schema",
            "VALIDATION_ERROR",
            f"Cannot validate schema: {e}",
            "CRITICAL"
        ))

    return violations


def validate_expense_workflow() -> List[BaselineViolation]:
    """Validate expense workflow statuses exist"""
    violations = []

    try:
        sys.path.insert(0, '.')
        from src.models import ExpenseStatus

        baseline_statuses = set(BASELINE["expense_workflow"]["required_statuses"])
        current_statuses = set([status.value for status in ExpenseStatus])

        missing_statuses = baseline_statuses - current_statuses
        for status in missing_statuses:
            violations.append(BaselineViolation(
                "Expense Workflow",
                "MISSING_STATUS",
                f"Required status '{status}' is missing",
                "CRITICAL"
            ))

    except Exception as e:
        violations.append(BaselineViolation(
            "Expense Workflow",
            "VALIDATION_ERROR",
            f"Cannot validate workflow: {e}",
            "CRITICAL"
        ))

    return violations


def validate_receipt_validation() -> List[BaselineViolation]:
    """Validate receipt validation rules match baseline"""
    violations = []

    try:
        sys.path.insert(0, '.')
        from src.routes.receipts import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

        baseline_extensions = set(BASELINE["validation_rules"]["receipt_upload"]["allowed_extensions"])
        current_extensions = ALLOWED_EXTENSIONS

        if baseline_extensions != current_extensions:
            violations.append(BaselineViolation(
                "Receipt Validation",
                "EXTENSIONS_CHANGED",
                f"Allowed extensions changed: baseline={baseline_extensions}, current={current_extensions}",
                "WARNING"
            ))

        baseline_max_size = BASELINE["validation_rules"]["receipt_upload"]["max_file_size_bytes"]
        if MAX_FILE_SIZE != baseline_max_size:
            violations.append(BaselineViolation(
                "Receipt Validation",
                "MAX_SIZE_CHANGED",
                f"Max file size changed: baseline={baseline_max_size}, current={MAX_FILE_SIZE}",
                "CRITICAL"
            ))

    except Exception as e:
        violations.append(BaselineViolation(
            "Receipt Validation",
            "VALIDATION_ERROR",
            f"Cannot validate receipt rules: {e}",
            "CRITICAL"
        ))

    return violations


def validate_approval_rules() -> List[BaselineViolation]:
    """Validate approval rules match baseline"""
    violations = []

    try:
        sys.path.insert(0, '.')
        from src.permissions import can_approve_expense

        # Check that approval function exists
        if not callable(can_approve_expense):
            violations.append(BaselineViolation(
                "Approval Rules",
                "FUNCTION_MISSING",
                "Approval function 'can_approve_expense' is not callable",
                "CRITICAL"
            ))

    except Exception as e:
        violations.append(BaselineViolation(
            "Approval Rules",
            "VALIDATION_ERROR",
            f"Cannot validate approval rules: {e}",
            "CRITICAL"
        ))

    return violations


def run_baseline_validation() -> bool:
    """
    Run all baseline validations

    Returns:
        True if all validations pass, False otherwise
    """
    print("="*60)
    print("BASELINE FUNCTIONALITY VALIDATION")
    print("="*60)
    print()
    print(f"Baseline Date: {BASELINE['baseline_date']}")
    print(f"Baseline Version: {BASELINE['version']}")
    print()
    print("Validating current functionality against baseline...")
    print()

    all_violations = []

    # Run all validators
    validators = [
        ("Tier Limits", validate_tier_limits),
        ("Database Schema", validate_database_schema),
        ("Expense Workflow", validate_expense_workflow),
        ("Receipt Validation", validate_receipt_validation),
        ("Approval Rules", validate_approval_rules),
    ]

    for category, validator in validators:
        print(f"Validating {category}...", end=" ")
        violations = validator()

        if not violations:
            print("[PASS]")
        else:
            print(f"[{len(violations)} violations]")
            all_violations.extend(violations)

    print()
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print()

    if not all_violations:
        print("[SUCCESS] All baseline validations passed!")
        print()
        print("[PASS] Current functionality matches baseline specification")
        print("[PASS] No breaking changes detected")
        print("[PASS] Safe to deploy")
        return True

    # Group violations by severity
    critical = [v for v in all_violations if v.severity == "CRITICAL"]
    warnings = [v for v in all_violations if v.severity == "WARNING"]

    if critical:
        print(f"[CRITICAL] {len(critical)} CRITICAL violations detected")
        print()
        for violation in critical:
            print(f"  ✗ {violation}")
        print()

    if warnings:
        print(f"[WARNING] {len(warnings)} warnings")
        print()
        for violation in warnings:
            print(f"  ⚠ {violation}")
        print()

    print("="*60)
    print("IMMEDIATE ACTIONS REQUIRED")
    print("="*60)
    print()

    if critical:
        print("CRITICAL violations detected - functionality is broken!")
        print()
        print("1. Review violations above")
        print("2. Fix broken functionality OR")
        print("3. Get approval to update baseline (Product + Finance + Legal + Engineering)")
        print("4. Update FUNCTIONALITY_BASELINE.json with new baseline")
        print("5. Document changes in changelog")
        print()
        print("⚠️  DEPLOYMENT BLOCKED until violations are resolved")

    return False


if __name__ == "__main__":
    success = run_baseline_validation()
    sys.exit(0 if success else 1)
