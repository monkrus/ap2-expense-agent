# 422 Validation Error Parsing Debug & Fix

## Problem Summary

When users create an organization with invalid data (e.g., slug too short), they receive a 422 error but see the generic message "An error occurred" instead of the specific validation error details.

## Root Cause Analysis

### Backend Response Format

The backend returns 422 validation errors in this structure (see `backend/src/error_handlers.py:255-261`):

```json
{
  "error": {
    "message": "Request validation failed",
    "code": "VALIDATION_ERROR",
    "status": 422,
    "details": {
      "errors": [
        {
          "field": "body.slug",
          "message": "String should have at least 3 characters",
          "type": "string_too_short"
        }
      ]
    }
  }
}
```

### Frontend Parsing Issue

The frontend `apiErrorHandler.js` was only looking for `errorData.detail` (legacy format) but not `errorData.error` (new format). This caused it to fall back to the generic "An error occurred" message.

**Old code (lines 26-58):**
```javascript
if (errorData.detail) {
  // Parse errorData.detail...
} else if (errorData.message) {
  // ...
} else if (errorData.error) {
  // This was LAST - too late!
  message = typeof errorData.error === "string" ? errorData.error : message;
}
```

## Fix Applied

Updated `frontend/src/utils/apiErrorHandler.js` to:

1. **Check for new format FIRST** (`errorData.error` object)
2. **Parse validation errors array** from `errorData.error.details.errors`
3. **Extract field names** correctly (remove "body." prefix)
4. **Format user-friendly messages** ("slug: must be at least 3 characters long")
5. **Add debug logging** to troubleshoot in browser console
6. **Maintain backward compatibility** with legacy `detail` format

**New code (lines 30-56):**
```javascript
// PRIORITY 1: Check for new backend error format with "error" object
if (errorData.error && typeof errorData.error === "object") {
  // Check for validation errors in details.errors array (422 errors)
  if (errorData.error.details && Array.isArray(errorData.error.details.errors)) {
    const errors = errorData.error.details.errors.map(err => {
      const field = err.field ? err.field.split('.').pop() : 'field'; // Extract "slug" from "body.slug"
      let msg = err.message || 'Validation error';

      // Make validation messages more user-friendly
      if (msg.includes('at least 3 characters')) {
        msg = 'must be at least 3 characters long';
      }
      // ... more transformations

      return `${field}: ${msg}`;
    });
    message = errors.join(', ');
  } else if (errorData.error.message) {
    message = errorData.error.message;
  }
}
// PRIORITY 2: Legacy format with "detail" (for compatibility)
else if (errorData.detail) {
  // ... existing logic
}
```

## Testing the Fix

### Manual Test Steps

1. **Open browser console** (F12) to see debug logs
2. **Navigate to Organizations page** (http://localhost:5173/organizations)
3. **Click "New Organization"**
4. **Fill form with invalid data:**
   - Name: "Test Org"
   - Slug: "ab" (too short - minimum 3 characters)
5. **Click "Create Organization"**
6. **Expected Results:**
   - Browser console shows:
     ```
     [apiErrorHandler] Raw error data: {...}
     [apiErrorHandler] Response status: 422
     [apiErrorHandler] Found error object format
     [apiErrorHandler] Found validation errors array: [...]
     [apiErrorHandler] Formatted validation message: slug: must be at least 3 characters long
     [apiErrorHandler] Final message: slug: must be at least 3 characters long
     ```
   - UI shows error message: **"slug: must be at least 3 characters long"**
   - NOT the generic "An error occurred"

### Additional Test Cases

Test different validation errors:

1. **Empty slug:**
   - Expected: "slug: String should have at least 3 characters"

2. **Invalid slug format (uppercase):**
   - Slug: "TEST"
   - Expected: "slug: can only contain lowercase letters, numbers, and hyphens"

3. **Multiple validation errors:**
   - Should show comma-separated: "slug: must be..., name: cannot be empty"

### Backend Logs Verification

Check `C:\Users\robot\AppData\Local\Temp\claude\C--Users-robot-Desktop-ap2-expense-agent\tasks\b5890d6.output`:

```
2025-12-24 22:23:18,129 - src.error_handlers - WARNING - Validation Error: 1 field(s) failed validation
2025-12-24 22:23:18,132 - http.access - INFO - POST /api/v1/organizations - 422
```

## Files Modified

1. **`frontend/src/utils/apiErrorHandler.js`**
   - Lines 22-92: Added new error format parsing with debug logs
   - Lines 160-179: Updated `extractTierLimitInfo` for new format

## Debug Console Logs Added

All `createAPIError` calls now log:
- `[apiErrorHandler] Raw error data:` - Full JSON response
- `[apiErrorHandler] Response status:` - HTTP status code
- `[apiErrorHandler] Found error object format` - Which branch was taken
- `[apiErrorHandler] Found validation errors array:` - Validation errors detected
- `[apiErrorHandler] Formatted validation message:` - Final user-facing message
- `[apiErrorHandler] Final message:` - What user will see

These can be removed later or kept for production debugging.

## Backward Compatibility

The fix maintains compatibility with:
- **Legacy `detail` format** (if backend ever sends it)
- **Simple string errors** (`{detail: "Some error"}`)
- **402 Payment Required errors** (tier limits)
- **Other HTTP status codes** (400, 401, 403, 404, etc.)

## Production Considerations

### Remove Debug Logs (Optional)

Before production deployment, consider removing console.log statements or wrapping them:

```javascript
if (import.meta.env.DEV) {
  console.log('[apiErrorHandler] ...', ...);
}
```

### Monitor Error Tracking

Ensure Sentry/logging captures these validation errors properly for monitoring.

## Related Files

- **Backend:** `backend/src/error_handlers.py` (validation_exception_handler)
- **Frontend:** `frontend/src/services/organizationAPI.js` (createOrganization)
- **Tests:** `frontend/src/utils/__tests__/apiErrorHandler.test.js` (may need updates)

## Status

- ✅ Fix applied
- ✅ Debug logs added
- ⏳ Manual testing required
- ⏳ Automated tests may need updates
- ⏳ Production logging strategy needed

---

**Next Steps:**
1. Test the fix manually (see "Manual Test Steps")
2. Update unit tests if needed
3. Decide on debug logging strategy (keep/remove/env-gated)
4. Test other error types (401, 402, 403, 404) to ensure no regressions
