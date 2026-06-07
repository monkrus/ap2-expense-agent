# AP2 Mandate Status Guide

## Understanding the Numbers

When you see: **All(20) Active(11) Expired(8) Used(0)**

These are counts for different **filter combinations**:

---

## What Each Number Means

### Filter View: Type = "All"

```
All(20) = Total mandates across ALL types (Intent + Cart + Payment)

Then by status:
  Active(11) = Mandates with status "active" (Intent only)
  Expired(8) = Mandates with status "expired" (Intent only)
  Used(0) = Payment mandates with status "completed"
```

---

## Why "Used(0)" Seems Wrong

### What "Used" Actually Means

```
"Used" = Payment Mandates with status "completed"

NOT Intent Mandates!
```

### The Confusion

```
You have:
  - 5 Intent Mandates (active)
  - 3 Cart Mandates (2 completed, 1 failed)
  - 3 Payment Mandates (2 completed, 1 failed)

So "Used" should be: 2 ✅
(2 payment mandates with status "completed")

But you're seeing: 0 ❌
```

---

## Actual Current State

Based on the data from your account:

```
All Mandates: 11 (not 20)
  └─ Intent: 5
  └─ Cart: 3
  └─ Payment: 3

Intent Mandates (5):
  ✅ Active: 5
  ❌ Expired: 0 (not 8)

Payment Mandates (3):
  ✅ Completed (Used): 2 (not 0)
  ❌ Failed: 1
```

---

## Inconsistency Analysis

### Your UI Shows:
```
All(20) Active(11) Expired(8) Used(0)
```

### Reality Shows:
```
All(11) Active(5) Expired(0) Used(2)
```

### Possible Causes:

#### 1. **Different User Account** ⚠️
```
You might be looking at a different user's mandates
Solution: Check which user you're logged in as
```

#### 2. **Cached Data** ⚠️
```
Frontend showing old cached data
Solution: Hard refresh (Ctrl+Shift+R)
```

#### 3. **Database Has Old Data** ⚠️
```
Test database has mandates from previous tests
Solution: Check database directly
```

#### 4. **Bug in Frontend Display** ⚠️
```
Frontend counting wrong statuses
Solution: Check console for errors
```

---

## Status Mapping

### Intent Mandates
```
Possible statuses:
  - "active" → Shows in Active(X) count
  - "expired" → Shows in Expired(X) count
  - "revoked" → Should show separately
  - "deleted" → Should be hidden
```

### Cart Mandates
```
Possible statuses:
  - "pending" → Shows in Pending(X) count
  - "completed" → Shows in Completed(X) count
  - "failed" → Shows in Failed(X) count
  - "revoked" → Should show separately
```

### Payment Mandates
```
Possible statuses:
  - "pending" → Shows in Pending(X) count
  - "completed" → Shows in USED(X) count ← This is "used"
  - "failed" → Shows in Failed(X) count
  - "revoked" → Should show separately
```

---

## Expected Behavior

### Filter: Type = "Intent", Status = "All"
```
Should show:
  All(5) Active(5) Expired(0)
```

### Filter: Type = "Payment", Status = "All"
```
Should show:
  All(3) Completed(2) Failed(1)
```

### Filter: Type = "All", Status = "All"
```
Should show:
  All(11) Active(5) Pending(0) Completed(2) Failed(1)
```

---

## The "Used" Count Specifically

### What It Tracks

```python
# backend/src/routes/ap2.py - get_ap2_stats()

"Used" = Payment Mandates with status "completed"

# Query:
payment_mandates = db.query(PaymentMandate).filter(
    PaymentMandate.status == "completed"
).count()
```

### Your Current Data

```
Payment Mandates:
  - completed: 2 ← This is "Used"
  - failed: 1

Therefore: Used(2) ✅ NOT Used(0) ❌
```

---

## How to Debug

### Check Frontend

```javascript
// Open browser console (F12)
// Look for API response

GET /api/ap2/user/mandates
Response should show:
{
  "mandates": [...],
  "count": 11  // Not 20
}

GET /api/ap2/stats
Response should show:
{
  "payment_mandates": {
    "completed": 2  // Not 0
  }
}
```

### Check Database

```sql
-- Count all mandates
SELECT
  'intent' as type,
  status,
  COUNT(*) as count
FROM intent_mandates
WHERE user_id = 'YOUR_USER_ID'
GROUP BY status

UNION ALL

SELECT
  'payment' as type,
  status,
  COUNT(*) as count
FROM payment_mandates
WHERE ...
GROUP BY status
```

---

## Correct Numbers for testuser

Based on current database state:

```
Type: All
  All(11)
  └─ Intent: 5 (all active)
  └─ Cart: 3 (2 completed, 1 failed)
  └─ Payment: 3 (2 completed, 1 failed)

Status Breakdown:
  Active(5) ← Intent mandates
  Completed(2) ← Cart + Payment completed
  Failed(1) ← Cart + Payment failed
  Used(2) ← Payment mandates completed

Total Amount Processed: $70.00
```

---

## Action Items

### If UI shows different numbers:

1. **Hard refresh page** (Ctrl+Shift+R)
2. **Check browser console** for errors
3. **Verify logged-in user**
4. **Check API responses** in Network tab
5. **Clear browser cache**
6. **Check database** directly

### Expected after refresh:

```
Current testuser data:
  All(11) - not All(20)
  Active(5) - not Active(11)
  Expired(0) - not Expired(8)
  Used(2) - not Used(0) ✅
```

---

## Summary

### Your Question: Is "All(20) Active(11) Expired(8) Used(0)" consistent?

**Answer: NO ❌**

**Reasons:**
1. Used(0) is wrong - should be Used(2)
2. Total count mismatch (20 vs 11)
3. Active count mismatch (11 vs 5)
4. Expired count mismatch (8 vs 0)

**Most likely cause:**
- Frontend showing cached/stale data
- OR looking at different user account
- OR database has old test data

**Solution:**
- Hard refresh browser
- Check which user is logged in
- Verify API responses in Network tab
