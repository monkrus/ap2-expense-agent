# API Error Handling Guide

## 🚨 CRITICAL: Always Use Standardized Error Handler

**This pattern MUST be followed for ALL API calls** to ensure proper error handling in components.

---

## The Problem We Solved

### ❌ **Before (Broken)**
```javascript
// organizationAPI.js
export const createInvitation = async (orgId, email, role) => {
  const response = await fetch(url, { method: "POST", ... });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail.message);  // ❌ No status property!
  }

  return response.json();
};

// OrganizationManagement.jsx
try {
  await organizationAPI.createInvitation(...);
} catch (err) {
  if (err.status === 402) {  // ❌ err.status is undefined!
    showUpgradeModal();
  } else {
    showError(err.message);  // Always executes (wrong!)
  }
}
```

**Result:** Toast notification shown instead of upgrade modal 😞

### ✅ **After (Fixed)**
```javascript
// organizationAPI.js
import { createAPIError } from "../utils/apiErrorHandler";

export const createInvitation = async (orgId, email, role) => {
  const response = await fetch(url, { method: "POST", ... });

  if (!response.ok) {
    const errorData = await response.json();
    throw createAPIError(response, errorData);  // ✅ Has status & data!
  }

  return response.json();
};

// OrganizationManagement.jsx
try {
  await organizationAPI.createInvitation(...);
} catch (err) {
  if (err.status === 402) {  // ✅ err.status is 402!
    showUpgradeModal(extractTierLimitInfo(err));  // ✅ Works!
  } else {
    showError(err.message);
  }
}
```

**Result:** Upgrade modal shown correctly 🎉

---

## Required Pattern for ALL API Functions

### 1. Import the Error Handler

```javascript
import { createAPIError } from "../utils/apiErrorHandler";
```

### 2. Use It in Every API Function

```javascript
export const yourAPIFunction = async (...args) => {
  const response = await fetch(url, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  // CRITICAL: Always use createAPIError for error responses
  if (!response.ok) {
    const errorData = await response.json();
    throw createAPIError(response, errorData);
  }

  return response.json();
};
```

### 3. Handle Errors in Components

```javascript
import { isTierLimitError, extractTierLimitInfo } from "../utils/apiErrorHandler";

const handleAction = async () => {
  try {
    await organizationAPI.someAction(...);
    success("Action completed!");
  } catch (err) {
    // Check for tier limit errors (402 Payment Required)
    if (isTierLimitError(err)) {
      const tierInfo = extractTierLimitInfo(err);
      setUpgradeTierInfo(tierInfo);
      setShowUpgradePrompt(true);
      return;
    }

    // Handle other errors
    showError(err.message);
  }
};
```

---

## API Error Handler Functions

### `createAPIError(response, errorData)`

**Purpose:** Creates a standardized Error object with `status` and `data` properties.

**Parameters:**
- `response` (Response): The fetch API response object
- `errorData` (Object): Parsed JSON error data from response

**Returns:** Error object with:
- `message` (string): User-friendly error message
- `status` (number): HTTP status code (e.g., 402, 400, 404)
- `data` (Object): Full error data from backend
- Helper methods: `is402PaymentRequired()`, `is401Unauthorized()`, etc.

**Example:**
```javascript
const response = await fetch('/api/endpoint');
if (!response.ok) {
  const errorData = await response.json();
  throw createAPIError(response, errorData);
}
```

### `isTierLimitError(error)`

**Purpose:** Checks if error is a 402 Payment Required (tier limit exceeded).

**Parameters:**
- `error` (Error): Error object to check

**Returns:** `boolean`

**Example:**
```javascript
catch (err) {
  if (isTierLimitError(err)) {
    // Show upgrade modal
  }
}
```

### `extractTierLimitInfo(error)`

**Purpose:** Extracts tier information from 402 error for upgrade modal.

**Parameters:**
- `error` (Error): 402 error object

**Returns:** Object with:
- `currentTier` (string): Current tier (e.g., "Free")
- `currentLimit` (number): Maximum allowed (e.g., 1)
- `currentCount` (number): Current usage (e.g., 1)
- `message` (string): User-friendly error message
- `upgradeOptions` (Object): Suggested upgrade tier

**Example:**
```javascript
if (isTierLimitError(err)) {
  const tierInfo = extractTierLimitInfo(err);
  setUpgradeTierInfo(tierInfo);
  setShowUpgradePrompt(true);
}
```

---

## Common Error Handling Patterns

### Pattern 1: Tier Limit with Upgrade Modal

```javascript
const handleCreateOrg = async () => {
  try {
    const org = await organizationAPI.createOrganization(formData);
    success(`Organization "${org.name}" created!`);
  } catch (err) {
    // 402 Payment Required - Tier limit
    if (isTierLimitError(err)) {
      setUpgradeTierInfo(extractTierLimitInfo(err));
      setShowUpgradePrompt(true);
      return;
    }

    // Other errors - show toast
    showError(err.message);
  }
};
```

### Pattern 2: Validation Errors with Suggestions

```javascript
const handleCreateOrg = async () => {
  try {
    const org = await organizationAPI.createOrganization(formData);
    success("Created!");
  } catch (err) {
    // 400 Bad Request - Validation error
    if (err.status === 400) {
      let errorMessage = err.message;

      // Add suggestions if available
      if (err.data?.suggestions?.length > 0) {
        errorMessage += "\n\nSuggestions:\n";
        errorMessage += err.data.suggestions.map(s => `  • ${s}`).join("\n");
      }

      showError(errorMessage);
      return;
    }

    // Tier limit
    if (isTierLimitError(err)) {
      setUpgradeTierInfo(extractTierLimitInfo(err));
      setShowUpgradePrompt(true);
      return;
    }

    // Other errors
    showError(err.message);
  }
};
```

### Pattern 3: Bulk Operations (Throw 402 Immediately)

```javascript
export const bulkInviteMembers = async (orgId, emails, role = "member") => {
  const results = { successful: [], failed: [] };

  for (const email of emails) {
    try {
      const result = await createInvitation(orgId, email.trim(), role);
      results.successful.push({ email, result });
    } catch (error) {
      // ⚠️ CRITICAL: Throw 402 errors immediately (don't collect them)
      if (error.status === 402) {
        throw error;  // This will trigger upgrade modal
      }

      // Collect other errors
      results.failed.push({ email, error: error.message });
    }
  }

  return results;
};
```

---

## Error Response Formats from Backend

### 402 Payment Required (Tier Limit)

```json
{
  "detail": {
    "error": "limit_exceeded",
    "feature": "Users",
    "limit": 1,
    "current": 1,
    "message": "Users limit exceeded: 1/1. Upgrade to Starter to add more team members.",
    "upgrade_message": "Upgrade to Starter to add more team members.",
    "current_tier": "free",
    "upgrade_options": {
      "next_tier": "starter",
      "price": "$29/month"
    }
  }
}
```

### 400 Bad Request (Validation Error)

```json
{
  "detail": {
    "error": "slug_already_taken",
    "message": "The slug 'test1' is already in use.",
    "field": "slug",
    "suggestions": [
      "test1-team",
      "test1-inc",
      "test1-co"
    ]
  }
}
```

### 422 Validation Error (Pydantic)

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Testing Checklist

Before committing any API changes, verify:

### ✅ Error Object Has Required Properties

```javascript
// Test in browser console after triggering error
catch (err) {
  console.log("Status:", err.status);  // Must be a number
  console.log("Data:", err.data);      // Must be an object
  console.log("Message:", err.message); // Must be a string
}
```

### ✅ 402 Errors Show Upgrade Modal

1. Login as FREE tier user
2. Try to:
   - Create 2nd organization → Should show upgrade modal
   - Invite a member (when already have 1 user) → Should show upgrade modal
   - Bulk invite members → Should show upgrade modal
3. Verify modal shows:
   - Correct title ("Organization Limit Reached" or "Team Member Limit Reached")
   - Current usage (e.g., "1/1 organizations")
   - Upgrade button that works

### ✅ Other Errors Show Toast Notifications

1. Try to create org with existing slug → Toast notification (400)
2. Try to access forbidden resource → Toast notification (403)
3. Try invalid API call → Toast notification

---

## Files Modified

1. ✅ `frontend/src/utils/apiErrorHandler.js` - Standardized error handler
2. ✅ `frontend/src/services/organizationAPI.js` - Uses `createAPIError`
3. ✅ `frontend/src/components/OrganizationManagement.jsx` - Handles 402 errors
4. ✅ `frontend/API_ERROR_HANDLING_GUIDE.md` - This documentation

---

## Red Flags to Watch For

### 🚩 Missing `status` Property

```javascript
// ❌ BAD
throw new Error(error.detail.message);

// ✅ GOOD
throw createAPIError(response, errorData);
```

### 🚩 Not Handling 402 Errors

```javascript
// ❌ BAD
catch (err) {
  showError(err.message);  // Always shows toast
}

// ✅ GOOD
catch (err) {
  if (isTierLimitError(err)) {
    showUpgradeModal(extractTierLimitInfo(err));
    return;
  }
  showError(err.message);
}
```

### 🚩 Collecting 402 Errors in Bulk Operations

```javascript
// ❌ BAD - Continues trying to invite after tier limit
for (const email of emails) {
  try {
    await createInvitation(orgId, email, role);
  } catch (error) {
    results.failed.push({ email, error: error.message });
  }
}

// ✅ GOOD - Throws immediately to show upgrade modal
for (const email of emails) {
  try {
    await createInvitation(orgId, email, role);
  } catch (error) {
    if (error.status === 402) {
      throw error;  // Stop and show modal
    }
    results.failed.push({ email, error: error.message });
  }
}
```

---

## Summary

**To prevent this error from happening again:**

1. ✅ **ALWAYS** use `createAPIError(response, errorData)` in API functions
2. ✅ **ALWAYS** check `isTierLimitError(err)` in catch blocks
3. ✅ **ALWAYS** show upgrade modal for 402 errors (not toast)
4. ✅ **ALWAYS** throw 402 errors immediately in bulk operations
5. ✅ **Test** both upgrade modal and toast notifications before committing

**If you add a new API function:**
1. Copy the pattern from an existing function (e.g., `createInvitation`)
2. Ensure it uses `createAPIError`
3. Test that errors have `status` and `data` properties
4. Verify 402 errors trigger upgrade modal

---

## Questions?

If unclear about error handling:
1. Check `frontend/src/services/organizationAPI.js` for examples
2. Check `frontend/src/utils/apiErrorHandler.js` for documentation
3. Test in browser console: `console.log(err.status, err.data)`
