# Development Guide

## Long-Term Error Prevention Solutions

This document explains the architectural improvements implemented to prevent recurring errors in the codebase.

---

## Table of Contents

1. [Overview](#overview)
2. [Problems Solved](#problems-solved)
3. [Solutions Implemented](#solutions-implemented)
4. [Usage Examples](#usage-examples)
5. [Testing](#testing)
6. [Maintenance](#maintenance)

---

## Overview

This project has implemented comprehensive error prevention measures to address common issues that arose during development:

- **Frontend-Backend Contract Mismatches** - Inconsistent API response structures
- **Missing Environment Variables** - Undefined constants causing runtime errors
- **Incomplete Implementations** - Missing required headers/validation
- **Platform-Specific Issues** - Encoding errors on Windows
- **Lack of Type Safety** - No compile-time error checking

---

## Problems Solved

### 1. Frontend-Backend Data Structure Mismatch ❌ → ✅

**Problem:**
```javascript
// Backend returns nested structure:
{ "success": true, "user": { "username": "john" } }

// Frontend expected flat structure:
data.username  // ← undefined!
```

**Solution:**
- Standardized response schemas using Pydantic (`backend/src/schemas/responses.py`)
- TypeScript type definitions (`frontend/src/types/api.ts`)
- Helper functions to safely extract data (`frontend/src/services/apiHelpers.js`)

**Example:**
```javascript
// Instead of:
success(`User ${data.username} created`);  // ❌ Breaks if structure changes

// Use helper:
import { extractUserData } from '../services/apiHelpers';
const user = extractUserData(data);
success(`User ${user.username} created`);  // ✅ Works with both structures
```

---

### 2. Missing Environment Variables ❌ → ✅

**Problem:**
```javascript
// UserManagementDashboard.jsx used API_BASE_URL without defining it
const response = await fetch(`${API_BASE_URL}/api/...`);  // ❌ ReferenceError
```

**Solution:**
- Centralized configuration (`frontend/src/config/constants.js`)
- Single source of truth for all constants
- All files import from shared location

**Example:**
```javascript
// Before (multiple definitions):
// adminAPI.js:  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
// UserDash.jsx: const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

// After (single source):
// config/constants.js
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// All files:
import { API_BASE_URL } from '../config/constants';
```

---

### 3. Missing Required Headers ❌ → ✅

**Problem:**
```python
# Backend accepted missing X-Organization-Id header
org_id = request.headers.get("X-Organization-Id")
if org_id:  # Silently skipped if missing!
    add_user_to_org(...)
```

**Solution:**
- Header validator utility (`backend/src/utils/validators.py`)
- Explicit validation with clear error messages
- Standardized error responses

**Example:**
```python
# Before:
org_id = request.headers.get("X-Organization-Id")  # Optional, silent failure

# After:
from src.utils.validators import HeaderValidator

org_id = HeaderValidator.require_organization_id(request)  # Required, fails with 400
```

**Error Response:**
```json
{
  "success": false,
  "error": "MISSING_REQUIRED_HEADER",
  "message": "Required header not provided",
  "detail": "X-Organization-Id header is required for this operation",
  "required_header": "X-Organization-Id"
}
```

---

## Solutions Implemented

### 1. Shared Configuration (`frontend/src/config/constants.js`)

**Purpose:** Single source of truth for all configuration values

**Contents:**
- API endpoints and URLs
- Feature flags
- Tier limits
- HTTP status codes
- Validation constants
- Required header names

**Usage:**
```javascript
import { API_BASE_URL, FREE_TIER_LIMITS, HTTP_STATUS } from '../config/constants';

// Check limits
if (userCount >= FREE_TIER_LIMITS.MAX_USERS) {
  alert('User limit reached');
}

// Check status codes
if (response.status === HTTP_STATUS.PAYMENT_REQUIRED) {
  showUpgradePrompt();
}
```

---

### 2. Standardized Response Schemas (`backend/src/schemas/responses.py`)

**Purpose:** Consistent API response structures

**Key Models:**
- `SuccessResponse<T>` - Generic success wrapper
- `ErrorResponse` - Standardized error format
- `UserCreatedResponse` - User creation response with nested user data
- `ValidationErrorResponse` - Validation errors with field details
- `MissingHeaderError` - Missing required header errors

**Example:**
```python
from src.schemas.responses import UserCreatedResponse, success_response

@router.post("/users/create")
async def create_user(...) -> UserCreatedResponse:
    # ...create user...

    return {
        "success": True,
        "message": "User created successfully",
        "user": {  # ← Always nested!
            "id": new_user.id,
            "username": new_user.username,
            # ...
        }
    }
```

---

### 3. Request Validators (`backend/src/utils/validators.py`)

**Purpose:** Validate headers and input data

**Classes:**
- `HeaderValidator` - Validates required headers
- `InputValidator` - Validates user input (username, password, email)

**Example:**
```python
from src.utils.validators import HeaderValidator, InputValidator

@router.post("/users/create")
async def create_user(request: Request, user_data: CreateUserRequest, ...):
    # Validate required header (fails with 400 if missing)
    org_id = HeaderValidator.require_organization_id(request)

    # Validate input
    InputValidator.validate_username(user_data.username)
    InputValidator.validate_password(user_data.password)

    # ...proceed with user creation...
```

---

### 4. TypeScript Type Definitions (`frontend/src/types/api.ts`)

**Purpose:** Type safety for API responses

**Contents:**
- Interface definitions matching backend Pydantic models
- Type guards for runtime type checking
- Helper functions for data extraction

**Example:**
```typescript
import { UserCreatedResponse, extractUserData } from '../types/api';

// Type-safe API call
const response: UserCreatedResponse = await apiCall(...);

// TypeScript knows 'user' exists
console.log(response.user.username);  // ✅ Type-safe

// Helper function handles both nested and flat structures
const user = extractUserData(response);
console.log(user.username);  // ✅ Always works
```

---

### 5. API Helper Functions (`frontend/src/services/apiHelpers.js`)

**Purpose:** Centralized error handling and response processing

**Functions:**
- `extractUserData(response)` - Safely extract user from nested/flat structure
- `extractErrorMessage(error)` - Get user-friendly error message
- `isMissingHeaderError(error)` - Check for specific error types
- `apiRequest(endpoint, options)` - Standardized API calls with error handling

**Example:**
```javascript
import { apiRequest, extractErrorMessage } from '../services/apiHelpers';

try {
  const data = await apiRequest('/api/v1/users/create', {
    method: 'POST',
    body: JSON.stringify(userData),
  });

  const user = extractUserData(data);
  success(`User ${user.username} created!`);
} catch (error) {
  const message = extractErrorMessage(error);
  showError(message);  // User-friendly message
}
```

---

### 6. Linting & Type Checking

**ESLint** (`frontend/.eslintrc.cjs`):
- Catches undefined variables (like `API_BASE_URL`)
- Enforces code quality standards
- Prevents common React mistakes

**Python Linting** (`backend/pyproject.toml`):
- Black for formatting
- isort for import sorting
- mypy for type checking
- pylint for code quality

**Run linting:**
```bash
# Frontend
cd frontend && npm run lint

# Backend
cd backend && python -m pylint src/
cd backend && python -m mypy src/
```

---

### 7. Integration Tests (`backend/tests/integration/test_expense_workflow.py`)

**Purpose:** Test complete user workflows end-to-end

**Tests:**
- Complete expense approval workflow
- Missing header error handling
- User deletion cleanup
- Response structure validation

**Run tests:**
```bash
cd backend && pytest tests/integration/ -v
```

**Key Test:**
```python
def test_missing_organization_header_error(client, admin_auth):
    """Verify missing header returns proper error"""
    response = client.post(
        "/api/v1/admin/users/create",
        headers={"Authorization": f"Bearer {admin_auth['token']}"},
        # Missing X-Organization-Id header
        json={"username": "test", "password": "Test123!", ...},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "MISSING_REQUIRED_HEADER"
    assert data["detail"]["required_header"] == "X-Organization-Id"
```

---

### 8. Pre-commit Hooks (`.pre-commit-config.yaml`)

**Purpose:** Automatically check code before commits

**Hooks:**
- Trailing whitespace removal
- JSON/YAML validation
- Black formatting (Python)
- ESLint (JavaScript/React)
- Security scanning (Bandit)

**Setup:**
```bash
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Usage Examples

### Creating a New API Endpoint

**Backend:**
```python
# routes/my_route.py
from fastapi import APIRouter, Request, Depends
from src.schemas.responses import SuccessResponse, created_response
from src.utils.validators import HeaderValidator

router = APIRouter()

@router.post("/my-endpoint")
async def my_endpoint(request: Request, ...):
    # Validate required headers
    org_id = HeaderValidator.require_organization_id(request)

    # Your logic here
    result = do_something(org_id)

    # Return standardized response
    return {
        "success": True,
        "message": "Operation successful",
        "data": result,  # Or nested like "user": result
    }
```

**Frontend:**
```javascript
// In your component
import { apiRequest, extractErrorMessage } from '../services/apiHelpers';
import { API_URL } from '../config/constants';

async function callMyEndpoint(orgId) {
  try {
    const data = await apiRequest('/my-endpoint', {
      method: 'POST',
      headers: {
        'X-Organization-Id': orgId,
      },
      body: JSON.stringify({ /* data */ }),
    });

    console.log('Success:', data);
  } catch (error) {
    console.error('Error:', extractErrorMessage(error));
  }
}
```

---

## Testing

### Run All Tests
```bash
# Backend integration tests
cd backend && pytest tests/integration/ -v

# Frontend tests (if configured)
cd frontend && npm test

# Manual workflow test
python test_expense_approval_flow.py
```

### Test Coverage
```bash
cd backend && pytest --cov=src --cov-report=html
# Open backend/htmlcov/index.html
```

---

## Maintenance

### Keeping Types in Sync

**When adding a new backend response:**

1. Update `backend/src/schemas/responses.py`
2. Update `frontend/src/types/api.ts`
3. Update helper functions if needed
4. Add integration test

**Checklist:**
- [ ] Backend Pydantic model created
- [ ] Frontend TypeScript interface created
- [ ] Helper function added (if needed)
- [ ] Integration test added
- [ ] Documentation updated

### Code Quality Checks

**Before committing:**
```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run linters
cd frontend && npm run lint
cd backend && python -m pylint src/

# Run tests
cd backend && pytest
```

---

## Common Pitfalls to Avoid

### ❌ Don't
```javascript
// Don't access nested properties directly
const username = response.username;  // May be undefined!

// Don't duplicate constants
const API_URL = "http://localhost:8000";  // Use shared config

// Don't skip header validation
const orgId = request.headers.get("X-Org-Id");  // Optional, silent failure
```

### ✅ Do
```javascript
// Use helper functions
const user = extractUserData(response);
const username = user.username;  // Always works

// Import shared constants
import { API_URL } from '../config/constants';

// Validate required headers
const orgId = HeaderValidator.require_organization_id(request);  // Fails explicitly
```

---

## Summary

This codebase now has:

✅ **Shared configuration** - No more duplicate constants
✅ **Standardized responses** - Consistent API contracts
✅ **Type safety** - TypeScript definitions + Pydantic models
✅ **Input validation** - Required header checks
✅ **Error handling** - User-friendly error messages
✅ **Linting** - Code quality enforcement
✅ **Integration tests** - End-to-end workflow verification
✅ **Pre-commit hooks** - Automated quality checks
✅ **Documentation** - Clear developer guide

**Result:** Prevents the recurring errors that plagued early development!

---

## Questions?

See also:
- `CLAUDE.md` - Project-specific development guide
- `README.md` - General project overview
- `backend/src/schemas/responses.py` - Response schema reference
- `frontend/src/types/api.ts` - TypeScript type reference
