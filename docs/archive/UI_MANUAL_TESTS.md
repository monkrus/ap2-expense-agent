# AP2 Automation - Simple UI Manual Tests

**Test on**: http://localhost:5173
**Time needed**: 15-20 minutes

---

## Test 1: Login

**Steps:**
1. Open http://localhost:5173
2. Login with:
   - Username: `user1`
   - Password: `Passowrd123!`

**Expected:**
- [ ] Login successful
- [ ] Redirected to dashboard

**Result:** ⬜ Pass ⬜ Fail

---

## Test 2: Navigate to AI Assistant Page

**Steps:**
1. Look for "AI Assistant" in the navigation menu
2. If not visible, try going directly to: http://localhost:5173/ai-assistant

**Expected:**
- [ ] Page loads without errors
- [ ] See dashboard or mandate controls

**Result:** ⬜ Pass ⬜ Fail

**Notes:** _________________________________________________________

---

## Test 3: Create Intent Mandate (if UI available)

**Steps:**
1. On AI Assistant page, look for "Create Intent Mandate" button
2. If available, click and fill in:
   - Max Amount: `200`
   - Monthly Limit: `1000`
   - Category: `OFFICE_SUPPLIES`
   - Merchant: `Amazon`
3. Click "Create" or "Save"

**Expected:**
- [ ] Success message appears
- [ ] New mandate shows in list

**Result:** ⬜ Pass ⬜ Fail ⬜ UI Not Available

**Notes:** _________________________________________________________

---

## Test 4: Submit Expense That Should Auto-Approve

**Steps:**
1. Go to Expenses page or Employee Dashboard
2. Click "+ Submit Expense" or "New Expense"
3. Fill in:
   - **Amount**: `45.99`
   - **Vendor**: `Amazon`
   - **Category**: `OFFICE_SUPPLIES`
   - **Description**: `Keyboard and mouse`
   - **Date**: Today
4. Click "Submit"

**Expected:**
- [ ] Success message with "auto-approved" or ✨ AI Agent
- [ ] Expense appears in list
- [ ] Status shows: **APPROVED** (green)
- [ ] See auto-approval badge or icon

**Result:** ⬜ Pass ⬜ Fail

**Actual status:** _________________________________________________________

**Screenshot?** _________________________________________________________

---

## Test 5: Submit Expense - Wrong Merchant (Should NOT Auto-Approve)

**Steps:**
1. Click "+ Submit Expense"
2. Fill in:
   - **Amount**: `35.00`
   - **Vendor**: `Microsoft` ← Different from mandate
   - **Category**: `OFFICE_SUPPLIES`
   - **Description**: `Mouse pad`
   - **Date**: Today
3. Click "Submit"

**Expected:**
- [ ] Success message (no auto-approve mention)
- [ ] Expense appears in list
- [ ] Status shows: **PENDING** (yellow/orange)
- [ ] NO auto-approval badge

**Result:** ⬜ Pass ⬜ Fail

**Actual status:** _________________________________________________________

---

## Test 6: Submit Expense - Amount Too High (Should NOT Auto-Approve)

**Steps:**
1. Click "+ Submit Expense"
2. Fill in:
   - **Amount**: `250.00` ← Exceeds max of 200
   - **Vendor**: `Amazon`
   - **Category**: `OFFICE_SUPPLIES`
   - **Description**: `Office chair`
   - **Date**: Today
3. Click "Submit"

**Expected:**
- [ ] Success message (no auto-approve mention)
- [ ] Status shows: **PENDING**
- [ ] NO auto-approval badge

**Result:** ⬜ Pass ⬜ Fail

**Actual status:** _________________________________________________________

---

## Test 7: Submit Expense - Wrong Category (Should NOT Auto-Approve)

**Steps:**
1. Click "+ Submit Expense"
2. Fill in:
   - **Amount**: `50.00`
   - **Vendor**: `Amazon`
   - **Category**: `TRAVEL` ← Different category
   - **Description**: `Flight ticket`
   - **Date**: Today
3. Click "Submit"

**Expected:**
- [ ] Success message (no auto-approve mention)
- [ ] Status shows: **PENDING**
- [ ] NO auto-approval badge

**Result:** ⬜ Pass ⬜ Fail

**Actual status:** _________________________________________________________

---

## Test 8: Check Expense List

**Steps:**
1. Go to Expenses list page
2. Look at the expenses you just submitted

**Expected:**
- [ ] Test 4 (Amazon, $45.99): **APPROVED** with auto-approve indicator
- [ ] Test 5 (Microsoft, $35.00): **PENDING**
- [ ] Test 6 (Amazon, $250.00): **PENDING**
- [ ] Test 7 (Amazon Travel, $50.00): **PENDING**

**Result:** ⬜ Pass ⬜ Fail

**Notes:** _________________________________________________________

---

## Test 9: View Expense Details

**Steps:**
1. Click on the auto-approved expense (Test 4)
2. View details page or modal

**Expected:**
- [ ] Shows status: APPROVED
- [ ] Shows auto-approval indicator
- [ ] May show "Approved via Intent Mandate" or similar
- [ ] Shows all expense details correctly

**Result:** ⬜ Pass ⬜ Fail

---

## Test 10: View Pending Expense Details

**Steps:**
1. Click on one of the pending expenses (Test 5, 6, or 7)
2. View details

**Expected:**
- [ ] Shows status: PENDING
- [ ] NO auto-approval indicator
- [ ] Shows "Awaiting approval" or similar
- [ ] Shows all expense details correctly

**Result:** ⬜ Pass ⬜ Fail

---

## Test 11: Create Another Matching Expense

**Steps:**
1. Submit another expense that matches the mandate:
   - **Amount**: `75.00`
   - **Vendor**: `Amazon`
   - **Category**: `OFFICE_SUPPLIES`
   - **Description**: `Desk lamp`

**Expected:**
- [ ] Auto-approved immediately
- [ ] Status: APPROVED
- [ ] Shows auto-approval badge

**Result:** ⬜ Pass ⬜ Fail

---

## Test 12: Check Monthly Limit (Optional)

**Steps:**
1. Keep submitting matching expenses:
   - $100 (Amazon, OFFICE_SUPPLIES)
   - $100 (Amazon, OFFICE_SUPPLIES)
   - $100 (Amazon, OFFICE_SUPPLIES)
   - $100 (Amazon, OFFICE_SUPPLIES)
2. You've now submitted: $45.99 + $75 + $400 = $520.99

**Expected:**
- [ ] Early expenses: APPROVED
- [ ] Later expenses: Should start going to PENDING when you hit the $1000 monthly limit

**Result:** ⬜ Pass ⬜ Fail ⬜ Skipped

**Total approved:** $_________

---

## Test 13: Visual Indicators Check

**Steps:**
1. Review the expenses list
2. Check for visual differences between auto-approved and pending

**Expected:**
- [ ] Auto-approved expenses have special badge/icon (like ✨)
- [ ] Status badges are different colors (green vs yellow)
- [ ] Easy to visually distinguish auto-approved from pending

**Result:** ⬜ Pass ⬜ Fail

**Notes:** _________________________________________________________

---

## Test 14: Case Sensitivity Check

**Steps:**
1. Submit expense with:
   - **Amount**: `25.00`
   - **Vendor**: `AMAZON` ← All caps
   - **Category**: `office_supplies` ← All lowercase
   - **Description**: `USB cable`

**Expected:**
- [ ] Auto-approved (case doesn't matter)
- [ ] Status: APPROVED

**Result:** ⬜ Pass ⬜ Fail

---

## Test 15: Dashboard/Statistics (if available)

**Steps:**
1. Go to Dashboard or AI Assistant page
2. Look for statistics about auto-approvals

**Expected:**
- [ ] Shows count of auto-approved expenses
- [ ] Shows active mandates count
- [ ] Shows total amount processed
- [ ] Statistics are accurate

**Result:** ⬜ Pass ⬜ Fail ⬜ Not Available

**Notes:** _________________________________________________________

---

## Summary

### Quick Results

| Test | Description | Status |
|------|-------------|--------|
| 1 | Login | ⬜ Pass ⬜ Fail |
| 4 | Auto-approve (matching) | ⬜ Pass ⬜ Fail |
| 5 | No auto-approve (wrong merchant) | ⬜ Pass ⬜ Fail |
| 6 | No auto-approve (amount too high) | ⬜ Pass ⬜ Fail |
| 7 | No auto-approve (wrong category) | ⬜ Pass ⬜ Fail |
| 8 | Expense list shows correct statuses | ⬜ Pass ⬜ Fail |
| 11 | Second matching expense auto-approves | ⬜ Pass ⬜ Fail |
| 14 | Case-insensitive matching works | ⬜ Pass ⬜ Fail |

### Overall Result

**Total Passed:** _____ / 15

**AP2 Auto-Approval Working?** ⬜ Yes ⬜ No ⬜ Partially

### Issues Found

1. ___________________________________________________________________

2. ___________________________________________________________________

3. ___________________________________________________________________

### Screenshots

Attach screenshots showing:
- [ ] Auto-approved expense with badge
- [ ] Pending expense
- [ ] Expense list with mixed statuses

---

## What Success Looks Like

✅ **Test 4** (Amazon, $45.99, OFFICE_SUPPLIES) → **APPROVED** with ✨ badge

❌ **Test 5** (Microsoft, $35.00, OFFICE_SUPPLIES) → **PENDING** (wrong merchant)

❌ **Test 6** (Amazon, $250.00, OFFICE_SUPPLIES) → **PENDING** (amount too high)

❌ **Test 7** (Amazon, $50.00, TRAVEL) → **PENDING** (wrong category)

✅ **Test 11** (Amazon, $75.00, OFFICE_SUPPLIES) → **APPROVED** with ✨ badge

---

**Tester:** _______________
**Date:** _______________
**Time Spent:** ___________ minutes
