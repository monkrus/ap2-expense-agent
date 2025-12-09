# RBAC Testing Framework - Quick Start Guide

## Overview

This guide helps you run and understand the comprehensive Role-Based Access Control (RBAC) testing framework for the AP2 Expense Management system.

---

## Quick Start

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Test users already created (see Test Users section below)
3. Python 3.x with `requests` library installed

### Running Tests

```bash
# Run the complete test suite
python test_rbac_framework.py

# The framework will:
# 1. Authenticate all 5 test users
# 2. Run 27+ tests across all roles
# 3. Generate detailed console output
# 4. Exit with code 0 (pass) or 1 (fail)
```

### Test Users

The framework requires these pre-configured users:

| Username | Password | Role | Purpose |
|----------|----------|------|---------|
| `emptest` | `Emptest123!` | EMPLOYEE | Basic expense submission |
| `emptest2` | `Emptest2123!` | EMPLOYEE | Multi-employee tests |
| `testuser` | `TestUser123!` | MANAGER | Approval workflows |
| `employee2` | `Employee2123!` | ACCOUNTANT | Audit & reporting |
| `admintest` | `AdminTest123!` | ADMIN | System administration |

**Note:** All users must be members of the same organization for cross-role tests.

---

## Test Structure

### Test Categories

The framework organizes tests into 6 categories:

1. **Typical Workflows** (11 tests)
   - Daily operations each role performs
   - Example: Employee submits expense, Manager approves

2. **Standard Scenarios** (2 tests)
   - Common use cases with variations
   - Example: Submit expense with receipt

3. **Atypical Scenarios** (2 tests)
   - Unusual but valid operations
   - Example: Zero-amount expense, future-dated expense

4. **Cross-Role Interactions** (1 test)
   - Multi-user workflows
   - Example: Employee→Manager→Accountant approval chain

5. **Permission Boundaries** (5 tests)
   - Security and access control
   - Example: Employee cannot approve expenses

6. **Edge Cases** (6 tests)
   - Input validation and security
   - Example: SQL injection, negative amounts

### Test Classes

```python
EmployeeTests       # 11 tests - Basic user operations
ManagerTests        # 6 tests  - Team oversight & approvals
AccountantTests     # 4 tests  - Financial auditing
AdminTests          # 3 tests  - System administration
CrossRoleTests      # 1 test   - Multi-user workflows
EdgeCaseTests       # 9 tests  - Validation & security
```

---

## Understanding Test Output

### Console Output Format

```
[PASS] | category     | ROLE         | Test Name: Success message
[FAIL] | category     | ROLE         | Test Name: Failure message
```

Example:
```
[PASS] | typical      | EMPLOYEE     | Submit Expense: Submitted $45.50 expense
[FAIL] | permission   | ACCOUNTANT   | Prevent Expense Deletion: WARNING: Deleted expense
```

### Color Coding
- 🟢 **Green** - Test passed
- 🔴 **Red** - Test failed
- 🔵 **Blue** - Informational message
- 🟡 **Yellow** - Warning

### Test Report Sections

1. **Overall Summary** - Total tests, pass rate, duration
2. **Results by Category** - Performance per test type
3. **Results by Role** - Performance per user role
4. **Failed Tests** - Detailed failure analysis
5. **Final Verdict** - EXCELLENT / GOOD / FAIR / POOR

---

## Common Test Scenarios

### Employee Role Tests

✅ **Should Pass:**
- Submit new expense
- View own expenses
- Update own pending expense
- Submit expense with future date

❌ **Should Fail:**
- Approve any expense (403 Forbidden)
- Delete other user's expense (403 Forbidden)
- View other user's expenses (403 Forbidden)

### Manager Role Tests

✅ **Should Pass:**
- View team expenses
- Approve employee expenses
- Submit own expense
- Create reimbursement for employee

❌ **Should Fail:**
- Approve own expense (403 Forbidden)
- Delete organization (403 Forbidden)

### Accountant Role Tests

✅ **Should Pass:**
- View all expenses
- Export expenses to CSV
- Request receipts for expenses
- View financial reports

❌ **Should Fail:**
- Approve expenses (403 Forbidden - review only)
- Delete expenses (403 Forbidden - audit trail)

### Admin Role Tests

✅ **Should Pass:**
- View all expenses (admin endpoints)
- Invite organization members
- Create new organizations
- Manage user roles

---

## Interpreting Results

### Pass Rate Guide

| Pass Rate | Verdict | Meaning |
|-----------|---------|---------|
| 95-100% | EXCELLENT | Production ready |
| 85-94% | GOOD | Minor issues to address |
| 70-84% | FAIR | Improvements needed |
| Below 70% | POOR | Critical issues found |

### Common Failure Reasons

1. **422 Unprocessable Entity**
   - Schema validation failure
   - Missing required fields
   - Invalid data format

2. **404 Not Found**
   - Endpoint doesn't exist
   - Resource deleted
   - Wrong URL path

3. **403 Forbidden**
   - Permission denied (expected for security tests)
   - Role lacks required privilege
   - Multi-tenant isolation working

4. **402 Payment Required**
   - Subscription tier limit reached
   - Need to upgrade plan
   - Resource quota exceeded

5. **401 Unauthorized**
   - Invalid/expired token
   - Authentication failed

---

## Customizing Tests

### Adding New Test Cases

```python
class EmployeeTests:
    def test_my_new_scenario(self):
        """Add custom test"""
        Logger.info("\nTesting: My custom scenario")

        # Make API request
        response = self.client.post("/expenses", self.user.token, {
            "amount": 100.00,
            "vendor": "Test Vendor",
            # ... other fields
        })

        # Record result
        self.fw.add_result(TestResult(
            test_name="My Custom Test",
            category=TestCategory.TYPICAL,
            role="EMPLOYEE",
            passed=response.status_code == 201,
            message="Test description",
            expected_status=201,
            actual_status=response.status_code
        ))
```

### Modifying Test Users

Edit the `TEST_USERS` dictionary at the top of `test_rbac_framework.py`:

```python
TEST_USERS = {
    "employee1": {
        "username": "your_username",
        "password": "your_password",
        "role": "EMPLOYEE"
    },
    # ... add more users
}
```

---

## Troubleshooting

### Issue: Rate Limit Errors (429)

**Symptom:** `rate_limit_exceeded` during login

**Solution:**
```bash
# Wait 60 seconds between test runs
# The framework includes automatic retry logic

# Or use Python sleep:
python -c "import time; time.sleep(65)" && python test_rbac_framework.py
```

### Issue: Organization Not Found

**Symptom:** `No organization found for admin user`

**Solution:**
1. Ensure admin user has at least one organization
2. Check organization membership for all test users
3. Run organization setup script

### Issue: All Tests Fail with 401

**Symptom:** All requests return 401 Unauthorized

**Solution:**
1. Verify backend is running on http://localhost:8000
2. Check test user credentials are correct
3. Ensure JWT authentication is working

### Issue: Tests Pass Locally But Fail in CI

**Symptom:** Different results in CI environment

**Solution:**
1. Ensure test database is seeded correctly
2. Check environment variables
3. Verify test user passwords match
4. Confirm organization context is set

---

## Best Practices

### Running Tests

1. **Always run with fresh data**
   - Tests may create/modify expenses
   - Consider database reset between runs

2. **Check backend logs**
   - Backend logs show detailed error information
   - Helps diagnose 500 errors

3. **Run tests sequentially**
   - Avoid concurrent test runs
   - May cause race conditions

4. **Monitor rate limits**
   - Login endpoint has rate limiting
   - Space out test runs by 60+ seconds

### Maintaining Tests

1. **Keep test users stable**
   - Don't delete test users
   - Maintain same passwords

2. **Update tests when API changes**
   - Schema changes require test updates
   - New endpoints need new tests

3. **Review failed tests**
   - Not all failures are bugs
   - May indicate expected behavior

4. **Document new test scenarios**
   - Add comments for complex tests
   - Explain expected vs actual behavior

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: RBAC Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install requests

      - name: Start backend
        run: |
          cd backend
          python -m uvicorn src.api:app &
          sleep 5

      - name: Run RBAC tests
        run: python test_rbac_framework.py

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: rbac-test-report
          path: RBAC_TEST_REPORT.md
```

---

## Test Data Management

### Shared Test Data

The framework stores shared data in `self.fw.test_data`:

```python
# Store expense ID for later use
self.fw.test_data["employee1_expense_id"] = expense_id

# Retrieve in another test
expense_id = self.fw.test_data.get("employee1_expense_id")
```

### Organization Context

All tests use the same organization:

```python
# Automatically set for all requests
self.client.set_default_org(self.org_id)

# Override for specific request
response = self.client.get("/expenses", token, org_id="custom-org-id")
```

---

## Performance Benchmarks

### Expected Performance

- **Setup Time:** 2-3 seconds (authentication)
- **Test Execution:** 0.3-0.5 seconds (27 tests)
- **Total Duration:** < 5 seconds
- **Throughput:** ~50-80 tests/second

### Slow Test Indicators

If tests take > 10 seconds:
1. Check database performance
2. Review backend query optimization
3. Check network latency
4. Look for timeout issues

---

## Frequently Asked Questions

### Q: Can I run specific test classes only?

**A:** Modify `run_all_tests()` method:

```python
def run_all_tests(self):
    # Run only employee tests
    EmployeeTests(self).run()
    # Comment out others
    # ManagerTests(self).run()
    # ...
```

### Q: How do I change the base URL?

**A:** Edit the `BASE_URL` constant:

```python
BASE_URL = "https://your-api-server.com"
```

### Q: Can I export results to JSON?

**A:** Add JSON export to the framework:

```python
import json

def export_to_json(self):
    data = {
        "total": len(self.results),
        "passed": sum(1 for r in self.results if r.passed),
        "tests": [vars(r) for r in self.results]
    }
    with open("test_results.json", "w") as f:
        json.dump(data, f, indent=2)
```

### Q: What if my roles have different names?

**A:** Update the `UserRole` enum mapping in the framework to match your schema.

---

## Support & Contributing

### Getting Help

1. Check the detailed test report: `RBAC_TEST_REPORT.md`
2. Review backend logs for error details
3. Verify test user configuration
4. Check API endpoint documentation

### Contributing New Tests

1. Follow existing test patterns
2. Use descriptive test names
3. Add appropriate category
4. Document expected behavior
5. Test both success and failure cases

---

## Changelog

### Version 1.0 (2025-12-08)
- Initial release
- 27 tests across 4 roles
- 6 test categories
- Comprehensive reporting
- Rate limit handling
- Color-coded output

---

**Last Updated:** 2025-12-08
**Framework Version:** 1.0
**Maintained By:** Development Team
