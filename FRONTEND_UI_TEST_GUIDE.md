# Frontend UI Testing Guide - AP2 Auto-Approval
**Goal:** Verify auto-approval badges and messages display correctly

---

## Prerequisites

### 1. Start Frontend Server (if not running)
```bash
cd frontend
npm run dev
```
**Expected:** Server starts on http://localhost:5173

### 2. Start Backend Server (if not running)
```bash
cd backend
uvicorn src.api:app --reload
```
**Expected:** Server starts on http://localhost:8000

---

## Test Scenario 1: View Existing Auto-Approved Expense

### Steps:
1. Open browser: http://localhost:5173
2. Login with:
   - Username: **adminfree**
   - Password: (your password)
3. Navigate to **Employee Dashboard** (should be default page)
4. Look for expenses in the list

### Expected Results:
✅ **You should see an expense:**
- Amount: **$45.00**
- Vendor: **Amazon**
- Category: **OFFICE_SUPPLIES**
- Description: "USB cables - Direct AP2 test"
- Status: **APPROVED** (green badge)
- Auto-approval: **✨ AI Agent** (purple badge) ← THIS IS KEY!

### Visual Check:
```
┌─────────────────────────────────────────────────────┐
│ Date      Amount  Vendor  Category  Status          │
├─────────────────────────────────────────────────────┤
│ 1/10/26   $45.00  Amazon  OFFICE... [APPROVED]     │
│                                      [✨ AI Agent]  │
└─────────────────────────────────────────────────────┘
```

### Troubleshooting:
- **No purple badge?** → Frontend code not loaded, restart dev server
- **Don't see expense?** → Run `python backend/verify_test_result.py` to confirm it exists
- **Shows PENDING instead of APPROVED?** → Backend didn't auto-approve (check logs)

---

## Test Scenario 2: Submit New Matching Expense (AI Auto-Approval)

### Steps:
1. Click **"+ Submit Expense"** button
2. Fill in the form:
   - **Expense Date:** Today's date
   - **Amount:** **55.00**
   - **Vendor:** **Amazon** ← IMPORTANT: Must match Intent Mandate
   - **Category:** **OFFICE_SUPPLIES** ← IMPORTANT: Must match
   - **Description:** "Keyboard and mouse - UI test"
3. Click **"Submit"**

### Expected Results:
✅ **Instant success toast message:**
```
✨ Auto-approved by AI agent via Intent Mandate (AP2)!
```

✅ **In expense list, you should immediately see:**
- New expense appears
- Status: **APPROVED** (green badge)
- **✨ AI Agent** badge (purple) ← KEY INDICATOR
- No need to refresh - appears instantly

### Visual Check:
```
Toast Notification:
┌────────────────────────────────────────────┐
│ ✅ ✨ Auto-approved by AI agent via       │
│    Intent Mandate (AP2)!                   │
└────────────────────────────────────────────┘

Expense List:
┌─────────────────────────────────────────────────────┐
│ Date      Amount  Vendor  Category  Status          │
├─────────────────────────────────────────────────────┤
│ 1/10/26   $55.00  Amazon  OFFICE... [APPROVED]     │
│                                      [✨ AI Agent]  │
│ 1/10/26   $45.00  Amazon  OFFICE... [APPROVED]     │
│                                      [✨ AI Agent]  │
└─────────────────────────────────────────────────────┘
```

---

## Test Scenario 3: Submit Non-Matching Expense (Manual Approval)

### Steps:
1. Click **"+ Submit Expense"** button
2. Fill in the form:
   - **Expense Date:** Today's date
   - **Amount:** **40.00**
   - **Vendor:** **Staples** ← DIFFERENT MERCHANT (won't match)
   - **Category:** **OFFICE_SUPPLIES**
   - **Description:** "Office supplies from Staples"
3. Click **"Submit"**

### Expected Results:
✅ **Standard success toast message:**
```
Expense submitted successfully! Awaiting approval.
```

✅ **In expense list:**
- New expense appears
- Status: **PENDING** (yellow badge)
- **NO purple badge** (no auto-approval)
- Will need manager to approve manually

### Visual Check:
```
Toast Notification:
┌────────────────────────────────────────────┐
│ ✅ Expense submitted successfully!        │
│    Awaiting approval.                      │
└────────────────────────────────────────────┘

Expense List:
┌─────────────────────────────────────────────────────┐
│ Date      Amount  Vendor   Category  Status         │
├─────────────────────────────────────────────────────┤
│ 1/10/26   $40.00  Staples  OFFICE... [PENDING]     │
│                                       (no badge)     │
│ 1/10/26   $55.00  Amazon   OFFICE... [APPROVED]    │
│                                       [✨ AI Agent] │
└─────────────────────────────────────────────────────┘
```

---

## Test Scenario 4: Expense Over Limit (Manual Approval)

### Steps:
1. Click **"+ Submit Expense"** button
2. Fill in the form:
   - **Expense Date:** Today's date
   - **Amount:** **250.00** ← OVER $200 LIMIT
   - **Vendor:** **Amazon**
   - **Category:** **OFFICE_SUPPLIES**
   - **Description:** "Expensive office equipment"
3. Click **"Submit"**

### Expected Results:
✅ **Standard toast:**
```
Expense submitted successfully! Awaiting approval.
```

✅ **In expense list:**
- Status: **PENDING** (yellow badge)
- **NO purple badge** (exceeded max_amount in Intent Mandate)

**Why?** Intent Mandate has `max_amount: 200.00`, so $250 expense doesn't match.

---

## Badge Colors & Meanings

### Status Badges:
- 🟢 **APPROVED** (green) - Expense approved
- 🟡 **PENDING** (yellow) - Awaiting manager approval
- 🔴 **REJECTED** (red) - Expense rejected
- ⚫ **WITHDRAWN** (gray) - Expense withdrawn

### Auto-Approval Badges:
- 🟣 **✨ AI Agent** (purple) - Auto-approved via Intent Mandate (AP2)
- 🔵 **📋 Policy** (blue) - Auto-approved via Approval Policy (free)
- (none) - Manual approval or not auto-approved

---

## Verification Checklist

After testing, verify:

- [ ] Purple **✨ AI Agent** badge appears on Amazon expenses
- [ ] Toast shows "✨ Auto-approved by AI agent via Intent Mandate (AP2)!"
- [ ] Non-matching expenses show PENDING status
- [ ] Non-matching expenses have NO auto-approval badge
- [ ] Over-limit expenses go to manual approval
- [ ] Page doesn't require refresh to see new expenses

---

## Browser Developer Console Check

### Open Console (F12):
Look for logs:
```javascript
// Should see successful API response:
{
  "id": "...",
  "status": "approved",
  "auto_approved": true,
  "auto_approved_via": "intent_mandate",
  "message": "✨ Auto-approved by AI agent via Intent Mandate (AP2)"
}
```

---

## Troubleshooting

### Issue: No purple badge appears

**Check:**
1. Frontend code changes saved?
   - File: `frontend/src/components/EmployeeDashboard.jsx`
   - Lines 279-303: `getAutoApprovalBadge()` function
   - Lines 982-983: Badge rendering in table

2. Frontend server restarted after code changes?
   ```bash
   cd frontend
   # Stop server (Ctrl+C)
   npm run dev  # Restart
   ```

3. Browser cache cleared?
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Or clear cache in DevTools

### Issue: Still shows "Awaiting approval" toast

**Check:**
1. Backend auto-approval working?
   ```bash
   cd backend
   python test_direct_ap2_submission.py
   ```

2. Intent Mandate active?
   ```bash
   cd backend
   python -c "from src.database import SessionLocal; from src.models import IntentMandate; db = SessionLocal(); m = db.query(IntentMandate).filter(IntentMandate.status == 'active').first(); print(f'Active mandate: {m.id}' if m else 'No active mandates'); db.close()"
   ```

3. Backend logs show matching?
   - Look for `[AP2]` logs in console
   - Should see "Found matching mandate" message

### Issue: Expense not appearing in list

**Check:**
1. Organization context correct?
   - Make sure you're viewing the right organization
   - Check X-Organization-Id header in Network tab

2. Expense created in backend?
   ```bash
   cd backend
   python verify_test_result.py
   ```

---

## Success Criteria ✅

Your frontend is working correctly when:

1. ✅ Purple **✨ AI Agent** badge displays on auto-approved expenses
2. ✅ Toast shows "✨ Auto-approved by AI agent" message
3. ✅ Status changes to APPROVED instantly (no PENDING state)
4. ✅ Non-matching expenses still go to PENDING
5. ✅ Badge has hover tooltip explaining AP2

---

## Next Steps After Testing

Once frontend tests pass:

### Phase 2 Enhancements:
1. **Intent Mandate Creation Wizard** - Make it easy to create mandates
2. **Dashboard Stats** - Show auto-approval rate, time saved
3. **"Will Auto-Approve" Indicator** - Show before submission
4. **Email Notifications** - "Your expense was auto-approved by AI"

### Production Checklist:
- [ ] All tests passing (backend + frontend)
- [ ] Documentation updated
- [ ] Demo video/screenshots created
- [ ] Marketing copy finalized
- [ ] Google Cloud Marketplace listing updated

---

## Questions?

**Backend working but frontend not?**
- Restart frontend dev server
- Clear browser cache
- Check browser console for errors

**Need to reset test data?**
```bash
cd backend
python -c "from src.database import SessionLocal; from src.models import Expense; db = SessionLocal(); db.query(Expense).filter(Expense.vendor == 'Amazon').delete(); db.commit(); print('Test expenses deleted'); db.close()"
```

**Ready for production?**
All tests passing = ✅ Ready to deploy!
