-- Migration: Add auto_approved_via field to expenses table
-- Date: 2026-01-09
-- Purpose: Track whether auto-approval was via Intent Mandate (AP2) or Approval Policy

-- Add auto_approved_via column
ALTER TABLE expenses ADD COLUMN auto_approved_via VARCHAR(50);

-- Backfill existing auto-approved expenses
-- If they have an intent_mandate_id, mark as 'intent_mandate'
UPDATE expenses
SET auto_approved_via = 'intent_mandate'
WHERE auto_approved = TRUE AND intent_mandate_id IS NOT NULL;

-- If they have an approval_policy_id but no intent_mandate_id, mark as 'approval_policy'
UPDATE expenses
SET auto_approved_via = 'approval_policy'
WHERE auto_approved = TRUE AND approval_policy_id IS NOT NULL AND intent_mandate_id IS NULL;

-- Verification query (run after migration)
-- SELECT auto_approved, auto_approved_via, COUNT(*) as count
-- FROM expenses
-- GROUP BY auto_approved, auto_approved_via;
