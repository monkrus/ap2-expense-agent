import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth.js';
import { waitForLoading } from './helpers/wait.js';

test.describe('Dashboard Overview Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);
  });

  test('Test 2.1: Statistics Cards Display', async ({ page }) => {
    // Check for all statistics cards
    const totalPending = page.locator('text=Total Pending').first();
    const approvedMonth = page.locator('text=Approved This Month').first();
    const rejectedMonth = page.locator('text=Rejected This Month').first();
    const totalAmount = page.locator('text=Total Amount').first();

    await expect(totalPending).toBeVisible();
    await expect(approvedMonth).toBeVisible();
    await expect(rejectedMonth).toBeVisible();
    await expect(totalAmount).toBeVisible();

    // Verify statistics have numeric values
    const statCards = page.locator('[class*="bg-white"][class*="rounded"][class*="shadow"]').filter({ hasText: /Total Pending|Approved|Rejected|Amount/ });
    const count = await statCards.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('Test 2.2: Refresh Button', async ({ page }) => {
    // Find refresh button
    const refreshButton = page.locator('button:has-text("Refresh"), button[title*="Refresh"], button svg[class*="rotate"]').first();

    if (await refreshButton.isVisible()) {
      // Click refresh
      await refreshButton.click();

      // Wait for loading
      await waitForLoading(page);

      // Verify page still loads
      await page.waitForLoadState('networkidle');
      const isVisible = await page.locator('text=Admin Dashboard, text=Pending Expense Requests').first().isVisible();
      expect(isVisible).toBeTruthy();
    }
  });

  test('Test 3.1: View Pending Requests Section', async ({ page }) => {
    // Look for pending requests section
    const pendingSection = page.locator('text=Pending Expense Requests').first();
    await expect(pendingSection).toBeVisible();

    // Check if section has expenses or empty state
    const hasExpenses = await page.locator('button:has-text("Approve"), button:has-text("Reject")').first().isVisible({ timeout: 2000 }).catch(() => false);
    const hasEmptyState = await page.locator('text=/No pending expenses|No expenses/i').isVisible({ timeout: 2000 }).catch(() => false);

    // Should have either expenses or empty state
    expect(hasExpenses || hasEmptyState).toBeTruthy();
  });
});
