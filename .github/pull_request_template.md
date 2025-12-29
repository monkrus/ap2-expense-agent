# Pull Request

## Description

<!-- Describe your changes in detail -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

<!-- Link to related issues: Fixes #123, Closes #456 -->

---

## Pre-Submission Checklist

### Code Quality

- [ ] My code follows the project's code style guidelines
- [ ] I have run linters and fixed all errors (`npm run lint` / `pylint src/`)
- [ ] I have run type checking (`mypy src/` for backend)
- [ ] Pre-commit hooks pass successfully
- [ ] No console.log statements left in code

### Testing

- [ ] I have added tests that prove my fix/feature works
- [ ] All new and existing tests pass (`pytest` / `npm test`)
- [ ] I have tested this change manually
- [ ] Integration tests pass for affected workflows

### API Changes (if applicable)

- [ ] **CRITICAL:** Response structure is standardized (follows `backend/src/schemas/responses.py`)
- [ ] **CRITICAL:** TypeScript types updated (`frontend/src/types/api.ts`)
- [ ] **CRITICAL:** Helper functions handle response correctly (`extractUserData`, etc.)
- [ ] Required headers are validated with `HeaderValidator`
- [ ] OpenAPI documentation updated (`python backend/generate_api_docs.py`)
- [ ] API changes are backward compatible OR breaking changes are documented

### Error Handling

- [ ] All error cases return standardized error responses
- [ ] User-friendly error messages provided
- [ ] Errors are logged with appropriate context
- [ ] Missing required fields trigger proper validation errors

### Database Changes (if applicable)

- [ ] Database migrations created (`alembic revision --autogenerate`)
- [ ] Migrations tested locally
- [ ] Soft deletes used instead of hard deletes (where appropriate)
- [ ] Multi-tenancy filters applied (`organization_id`, `is_active`)

### Documentation

- [ ] Code is self-documenting or includes necessary comments
- [ ] README updated (if needed)
- [ ] `DEVELOPMENT.md` updated (if adding new patterns)
- [ ] API documentation generated (`python backend/generate_api_docs.py`)

### Security

- [ ] No sensitive data exposed in logs or error messages
- [ ] Authentication/authorization checks in place
- [ ] Input validation performed
- [ ] SQL injection prevented (using SQLAlchemy ORM)
- [ ] XSS prevented (React auto-escapes)
- [ ] No hardcoded secrets or credentials

---

## Preventing Recurring Errors

### ✅ Response Structure Validation

**For any API endpoint changes, confirm:**

- [ ] Backend returns data nested in specific key (e.g., `user`, `expense`, `organization`)
- [ ] Frontend uses helper function to extract data safely
- [ ] TypeScript interface matches backend Pydantic model

**Example:**
```python
# Backend (CORRECT)
return {
    "success": True,
    "message": "User created successfully",
    "user": {  # ← Nested!
        "id": user.id,
        "username": user.username,
        ...
    }
}
```

```javascript
// Frontend (CORRECT)
const user = extractUserData(response);  // ← Use helper
success(`User ${user.username} created!`);
```

### ✅ Required Headers Validation

**For endpoints requiring organization context:**

- [ ] Used `HeaderValidator.require_organization_id(request)` to enforce header
- [ ] Returns 400 with standardized error if header missing
- [ ] Frontend sends `X-Organization-Id` header in request

**Example:**
```python
# Backend (CORRECT)
from src.utils.validators import HeaderValidator

@router.post("/endpoint")
async def endpoint(request: Request, ...):
    org_id = HeaderValidator.require_organization_id(request)  # ← Enforced!
    ...
```

### ✅ Shared Constants

**For any configuration values:**

- [ ] Added to `frontend/src/config/constants.js` (not duplicated)
- [ ] Imported from shared location
- [ ] No hardcoded URLs or magic numbers

---

## Testing Evidence

<!-- Provide evidence that your changes work -->

### Manual Testing

- [ ] Tested in development environment
- [ ] Tested with different user roles
- [ ] Tested error scenarios
- [ ] Tested on multiple browsers (if frontend change)

### Automated Testing

```bash
# Backend tests
cd backend && pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration tests
cd backend && pytest tests/integration/ -v
```

### Test Results

<!-- Paste test output or screenshots here -->

```
# Paste test results here
```

---

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

---

## Deployment Notes

<!-- Any special steps needed for deployment? -->

- [ ] No special deployment steps required
- [ ] Requires database migration
- [ ] Requires environment variable changes
- [ ] Requires frontend rebuild
- [ ] Requires backend restart

---

## Reviewer Notes

<!-- Add any notes for reviewers -->

---

## Post-Merge Checklist

- [ ] Monitor error logs for new issues
- [ ] Verify integration tests pass in CI/CD
- [ ] Update changelog (if significant change)
- [ ] Close related issues

---

## Additional Context

<!-- Add any other context about the PR here -->
