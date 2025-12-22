# Quick Reference: API Error Handling

## ✅ Correct Pattern (Copy This!)

### API Function (organizationAPI.js, etc.)
```javascript
import { createAPIError } from "../utils/apiErrorHandler";

export const yourFunction = async (...args) => {
  const response = await fetch(url, { method: "POST", ... });

  if (!response.ok) {
    const errorData = await response.json();
    throw createAPIError(response, errorData);  // ✅ Always use this
  }

  return response.json();
};
```

### Component Error Handling
```javascript
import { isTierLimitError, extractTierLimitInfo } from "../utils/apiErrorHandler";

const handleAction = async () => {
  try {
    await yourAPIFunction(...);
    success("Done!");
  } catch (err) {
    // 402 Payment Required → Upgrade Modal
    if (isTierLimitError(err)) {
      setUpgradeTierInfo(extractTierLimitInfo(err));
      setShowUpgradePrompt(true);
      return;
    }

    // All other errors → Toast
    showError(err.message);
  }
};
```

### Bulk Operations
```javascript
for (const item of items) {
  try {
    await apiFunction(item);
  } catch (error) {
    if (error.status === 402) {
      throw error;  // ✅ Throw immediately for upgrade modal
    }
    // Collect other errors
    results.failed.push({ item, error: error.message });
  }
}
```

---

## ❌ Wrong Patterns (DON'T Do This!)

### ❌ Missing Status Property
```javascript
// ❌ WRONG - error won't have status property
throw new Error(error.detail.message);

// ✅ RIGHT
throw createAPIError(response, errorData);
```

### ❌ Not Checking 402
```javascript
// ❌ WRONG - always shows toast
catch (err) {
  showError(err.message);
}

// ✅ RIGHT
catch (err) {
  if (isTierLimitError(err)) {
    showUpgradeModal(extractTierLimitInfo(err));
    return;
  }
  showError(err.message);
}
```

### ❌ Collecting 402 Errors
```javascript
// ❌ WRONG - continues after tier limit
for (const email of emails) {
  try {
    await invite(email);
  } catch (error) {
    results.failed.push(error);  // ❌ Collects 402
  }
}

// ✅ RIGHT
for (const email of emails) {
  try {
    await invite(email);
  } catch (error) {
    if (error.status === 402) throw error;  // ✅ Stop immediately
    results.failed.push(error);
  }
}
```

---

## Testing Checklist

- [ ] Login as FREE tier user
- [ ] Try to create 2nd organization → See upgrade modal (not toast)
- [ ] Try to invite member when at limit → See upgrade modal (not toast)
- [ ] Try bulk invite when at limit → See upgrade modal (not toast)
- [ ] Try invalid action → See toast notification

---

## Files to Check

1. **API Functions:** `frontend/src/services/organizationAPI.js`
2. **Error Handler:** `frontend/src/utils/apiErrorHandler.js`
3. **Full Guide:** `frontend/API_ERROR_HANDLING_GUIDE.md`

---

## In Case of Emergency

If errors aren't working:

```javascript
// Add this to catch block for debugging
catch (err) {
  console.log("Error status:", err.status);  // Should be a number
  console.log("Error data:", err.data);      // Should be an object
  console.log("Error message:", err.message); // Should be a string

  if (err.status === 402) {
    console.log("402 detected!");  // Should print
  }
}
```

If `err.status` is `undefined`, the API function isn't using `createAPIError()`.
