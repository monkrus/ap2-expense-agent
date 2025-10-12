# Automated Testing Guide

Comprehensive guide for running and writing automated tests for the AP2 Expense Management Agent.

## Quick Start

```bash
cd backend

# Install test dependencies
pip install pytest pytest-cov

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Test Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_expenses.py         # NEW: Expense CRUD and workflow tests
├── test_audit_service.py    # NEW: AP2 audit trail service tests
├── test_auth.py            # Authentication tests
├── test_admin.py           # Admin operations tests
├── test_users.py           # User management tests
├── test_ap2_protocol.py    # AP2 protocol tests
├── test_compliance.py      # Compliance and security tests
├── test_cache.py           # Caching tests
├── test_tenant_isolation.py # Multi-tenancy tests
└── performance/            # Performance tests
```

## New Test Files

### test_expenses.py

Tests for the expense management features:

**Test Classes:**
- `TestExpenseOperations` - CRUD operations
- `TestExpenseApproval` - Approval workflow
- `TestAuditTrail` - AP2 audit trail retrieval
- `TestAdminExpenses` - Admin expense management
- `TestExpenseValidation` - Input validation

**Key Tests:**
```bash
# Test expense submission
pytest tests/test_expenses.py::TestExpenseOperations::test_submit_expense -v

# Test expense editing
pytest tests/test_expenses.py::TestExpenseOperations::test_update_pending_expense -v

# Test approval workflow
pytest tests/test_expenses.py::TestExpenseApproval::test_admin_can_approve_expense -v

# Test audit trail
pytest tests/test_expenses.py::TestAuditTrail::test_get_audit_trail -v
```

### test_audit_service.py

Tests for the AP2 audit service:

**Test Classes:**
- `TestAuditServiceMandateCreation` - Mandate creation
- `TestAuditServiceRetrieval` - Audit trail retrieval
- `TestAuditServiceConstraints` - Mandate constraints
- `TestAuditServiceVerification` - Signature and timestamp verification

**Key Tests:**
```bash
# Test complete audit trail creation
pytest tests/test_audit_service.py::TestAuditServiceMandateCreation::test_create_complete_audit_trail -v

# Test audit trail retrieval
pytest tests/test_audit_service.py::TestAuditServiceRetrieval::test_get_complete_audit_trail -v
```

## Running Tests

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run Specific Test File

```bash
python -m pytest tests/test_expenses.py -v
python -m pytest tests/test_audit_service.py -v
```

### Run Specific Test Class

```bash
python -m pytest tests/test_expenses.py::TestExpenseApproval -v
```

### Run Specific Test

```bash
python -m pytest tests/test_expenses.py::TestExpenseApproval::test_admin_can_approve_expense -v
```

### Run with Different Verbosity

```bash
# Minimal output
python -m pytest tests/

# Verbose
python -m pytest tests/ -v

# Very verbose (show individual assertions)
python -m pytest tests/ -vv
```

### Show Print Statements

```bash
python -m pytest tests/ -s
```

### Stop on First Failure

```bash
python -m pytest tests/ -x
```

### Run Last Failed Tests

```bash
python -m pytest tests/ --lf
```

## Code Coverage

### Generate Coverage Report

```bash
# HTML report
python -m pytest tests/ --cov=src --cov-report=html

# Terminal report
python -m pytest tests/ --cov=src --cov-report=term

# XML report (for CI/CD)
python -m pytest tests/ --cov=src --cov-report=xml
```

### View HTML Coverage Report

```bash
# On Windows
start htmlcov/index.html

# On Mac/Linux
open htmlcov/index.html
```

### Coverage Goals

- **Overall**: > 80%
- **Critical paths**: > 95%
  - Authentication
  - Expense approval workflow
  - AP2 mandate creation
  - Authorization checks

## Test Fixtures

### Authentication Fixtures

```python
def test_with_employee(client, employee_headers):
    """Use employee authentication"""
    response = client.get("/api/v1/expenses/report", headers=employee_headers)
    assert response.status_code == 200

def test_with_admin(client, admin_headers):
    """Use admin authentication"""
    response = client.get("/api/v1/admin/expenses", headers=admin_headers)
    assert response.status_code == 200
```

### Factory Fixtures

```python
def test_with_custom_user(sample_user):
    """Create user with specific attributes"""
    user = sample_user(
        email="custom@test.com",
        role=UserRole.MANAGER,
        full_name="Custom User"
    )
    assert user.role == UserRole.MANAGER

def test_with_custom_expense(sample_expense):
    """Create expense with specific attributes"""
    expense = sample_expense(
        amount=500.00,
        vendor="Custom Vendor",
        status=ExpenseStatus.APPROVED
    )
    assert expense.amount == 500.00
```

## Writing New Tests

### Test Template

```python
"""
Tests for [feature name]
"""
import pytest
from fastapi.testclient import TestClient

class Test[FeatureName]:
    """Test [feature description]"""

    def test_[scenario](self, client: TestClient, [fixtures]):
        """Test that [expected behavior]"""
        # Arrange
        # ... setup test data ...

        # Act
        response = client.post("/api/v1/endpoint", json=data, headers=headers)

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True
```

### Best Practices

1. **Descriptive Names**: Use clear, descriptive test names
2. **One Purpose**: Each test should test one thing
3. **Arrange-Act-Assert**: Follow the AAA pattern
4. **Use Fixtures**: Reuse test data via fixtures
5. **Clean State**: Tests should not depend on each other
6. **Meaningful Assertions**: Assert specific expected values

### Example Test

```python
def test_admin_can_approve_expense(self, client, admin_headers, sample_expense):
    """Test admin user can approve a pending expense"""
    # Arrange - Create pending expense
    expense = sample_expense(status=ExpenseStatus.PENDING)

    # Act - Approve the expense
    response = client.post(
        "/api/v1/expenses/approve",
        json={
            "expense_id": expense.id,
            "approver_id": "admin-user-id"
        },
        headers=admin_headers
    )

    # Assert - Verify approval succeeded
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"]["status"] == "approved"

    # Assert - Verify AP2 mandates created
    assert "mandates" in data["result"]
    assert "intent" in data["result"]["mandates"]
    assert "cart" in data["result"]["mandates"]
    assert "payment" in data["result"]["mandates"]
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests with coverage
      run: |
        cd backend
        pytest tests/ --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: unittests
        name: codecov-umbrella
```

## Debugging Tests

### Use pytest debugger

```bash
# Drop into debugger on failure
python -m pytest tests/ --pdb

# Drop into debugger on first failure
python -m pytest tests/ --pdb -x
```

### Add breakpoints in code

```python
def test_something():
    # Your test code
    import pdb; pdb.set_trace()  # Debugger will stop here
    # More test code
```

### View detailed error messages

```bash
# Show local variables on failure
python -m pytest tests/ -l

# Show full diff for assertions
python -m pytest tests/ -vv
```

## Performance Testing

Run performance tests separately:

```bash
python -m pytest tests/performance/ -v
```

## Testing Checklist

Before committing code, ensure:

- [ ] All tests pass
- [ ] New features have tests
- [ ] Edge cases are tested
- [ ] Error cases are tested
- [ ] Authorization is tested
- [ ] Coverage is maintained (>80%)
- [ ] No test warnings

## Common Test Scenarios

### Testing API Endpoints

```python
def test_endpoint_success(client, auth_headers):
    response = client.get("/api/v1/endpoint", headers=auth_headers)
    assert response.status_code == 200

def test_endpoint_unauthorized(client):
    response = client.get("/api/v1/endpoint")
    assert response.status_code == 401

def test_endpoint_forbidden(client, employee_headers):
    response = client.get("/api/v1/admin/endpoint", headers=employee_headers)
    assert response.status_code == 403

def test_endpoint_not_found(client, auth_headers):
    response = client.get("/api/v1/nonexistent", headers=auth_headers)
    assert response.status_code == 404

def test_endpoint_validation(client, auth_headers):
    response = client.post(
        "/api/v1/endpoint",
        json={"invalid": "data"},
        headers=auth_headers
    )
    assert response.status_code == 422
```

### Testing Database Operations

```python
def test_create_record(db_session):
    record = Model(field="value")
    db_session.add(record)
    db_session.commit()

    assert record.id is not None

def test_read_record(db_session, sample_record):
    record = db_session.query(Model).filter(Model.id == sample_record.id).first()
    assert record is not None
    assert record.field == "value"

def test_update_record(db_session, sample_record):
    sample_record.field = "new_value"
    db_session.commit()

    updated = db_session.query(Model).get(sample_record.id)
    assert updated.field == "new_value"

def test_delete_record(db_session, sample_record):
    record_id = sample_record.id
    db_session.delete(sample_record)
    db_session.commit()

    deleted = db_session.query(Model).get(record_id)
    assert deleted is None
```

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the backend directory
cd backend

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Issues

Tests use in-memory SQLite - no external database needed. Each test gets a fresh database.

### Redis Connection Errors

Cache is optional in tests. The `cleanup_cache` fixture handles cleanup if Redis is available.

### Authentication Failures

Ensure fixtures create users with correct passwords:

```python
hashed_password=AuthService.hash_password("TestPass123!")
```

## Test Metrics

Track these metrics:

- **Total tests**: Should increase with features
- **Coverage**: Should stay > 80%
- **Test duration**: Should stay < 2 minutes
- **Flaky tests**: Should be 0

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
