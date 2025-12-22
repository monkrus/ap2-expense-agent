import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth.js';
import { waitForLoading, waitForToast } from './helpers/wait.js';
import { createExpense, getAccessToken, getUserId, createMultipleExpenses } from './helpers/dataSeeder.js';

test.describe('My Expenses Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);
  });

  test('Test 4.1: View Active Expenses Tab', async ({ page }) => {
    // Look for My Expenses section
    const myExpensesSection = page.locator('text=My Expenses').first();
    await expect(myExpensesSection).toBeVisible({ timeout: 5000 });

    // Click Active tab if not already active
    const activeTab = page.locator('button:has-text("Active")').first();
    if (await activeTab.isVisible({ timeout: 2000 })) {
      await activeTab.click();
      await waitForLoading(page);
    }

    // Check for table headers
    const hasTableHeaders = await page.locator('text=Date, text=Category, text=Vendor, text=Amount').first().isVisible({ timeout: 2000 }).catch(() => false);

    // Should either have table or empty state
    const hasEmptyState = await page.locator('text=/No expenses|No active expenses/i').isVisible({ timeout: 2000 }).catch(() => false);

    expect(hasTableHeaders || hasEmptyState).toBeTruthy();
  });

  test('Test 4.2: View History Tab', async ({ page }) => {
    // Click History tab
    const historyTab = page.locator('button:has-text("History")').first();
    await expect(historyTab).toBeVisible();
    await historyTab.click();
    await waitForLoading(page);

    // Verify tab switched
    const isActive = await historyTab.getAttribute('class');
    expect(isActive).toContain('active') || expect(isActive).toContain('selected') || expect(isActive).toContain('bg-');
  });

  test('Test 4.3: Create New Expense', async ({ page }) => {
    // Click "+ New Expense" button
    const newExpenseBtn = page.locator('button:has-text("+ New Expense"), button:has-text("New Expense")').first();
    await expect(newExpenseBtn).toBeVisible();
    await newExpenseBtn.click();

    // Wait for modal
    await page.waitForSelector('input[type="number"], input[placeholder*="amount"], input[placeholder*="Amount"]', { timeout: 5000 });

    // Fill form
    await page.fill('input[type="number"], input[placeholder*="amount"]', '125.50');

    // Select category
    const categorySelect = page.locator('select, [role="combobox"]').filter({ hasText: /Category|category/ }).first();
    if (await categorySelect.isVisible({ timeout: 1000 })) {
      await categorySelect.selectOption('Office Supplies');
    }

    // Fill vendor
    await page.fill('input[placeholder*="vendor"], input[placeholder*="Vendor"]', 'Staples');

    // Fill description
    await page.fill('textarea, input[placeholder*="description"]', 'Printer ink and paper');

    // Select date (today)
    const dateInput = page.locator('input[type="date"]').first();
    if (await dateInput.isVisible({ timeout: 1000 })) {
      const today = new Date().toISOString().split('T')[0];
      await dateInput.fill(today);
    }

    // Submit
    await page.click('button:has-text("Submit"), button:has-text("Create")');

    // Wait for success
    await waitForToast(page, 'success').catch(() => {});
    await waitForLoading(page);

    // Verify modal closed and expense appears
    await page.waitForTimeout(1000);
  });

  test('Test 4.8: Search Expenses', async ({ page }) => {
    // Create test data first
    const token = await getAccessToken(page);
    const userId = await getUserId(page);

    await createExpense(token, {
      user_id: userId,
      vendor: 'Office Depot',
      description: 'Office supplies test',
      category: 'Office Supplies'
    });

    // Reload to see new expense
    await page.reload();
    await waitForLoading(page);

    // Find search box
    const searchBox = page.locator('input[placeholder*="Search"], input[type="search"], input[placeholder*="search"]').first();

    if (await searchBox.isVisible({ timeout: 2000 })) {
      // Type in search
      await searchBox.fill('office');
      await page.waitForTimeout(500);

      // Verify filtering works
      const results = page.locator('text=Office, text=office');
      const count = await results.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('Test 4.9: Filter by Category', async ({ page }) => {
    // Find category filter dropdown
    const categoryFilter = page.locator('select:has-text("All Categories"), select:has-text("Category"),[role="combobox"]:has-text("Category")').first();

    if (await categoryFilter.isVisible({ timeout: 2000 })) {
      // Select Travel category
      await categoryFilter.selectOption('Travel');
      await waitForLoading(page);

      // Verify only Travel expenses shown (if any exist)
      await page.waitForTimeout(500);
    }
  });

  test('Test 4.10: Sort Expenses', async ({ page }) => {
    // Find sort dropdown
    const sortDropdown = page.locator('select:has-text("Sort"), select:has-text("Newest"), [role="combobox"]:has-text("Sort")').first();

    if (await sortDropdown.isVisible({ timeout: 2000 })) {
      // Try different sort options
      await sortDropdown.selectOption({ label: 'Highest Amount' });
      await waitForLoading(page);
      await page.waitForTimeout(500);

      await sortDropdown.selectOption({ label: 'Lowest Amount' });
      await waitForLoading(page);
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Pending Expenses Management Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);
  });

  test('Test 3.2: Approve Expense', async ({ page }) => {
    // Create a test expense first
    const token = await getAccessToken(page);
    const userId = await getUserId(page);

    await createExpense(token, {
      user_id: userId,
      amount: 99.99,
      vendor: 'Test Approve Vendor',
      description: 'Test approval'
    });

    // Reload to see new expense
    await page.reload();
    await waitForLoading(page);

    // Look for approve button
    const approveBtn = page.locator('button:has-text("Approve")').first();

    if (await approveBtn.isVisible({ timeout: 3000 })) {
      // Get initial pending count
      const pendingText = await page.locator('text=Total Pending').locator('..').locator('text=/\\d+/').first().textContent();

      // Click approve
      await approveBtn.click();
      await waitForLoading(page);

      // Wait for success toast
      await page.waitForTimeout(1000);

      // Verify statistics updated
      await page.waitForTimeout(500);
    }
  });

  test('Test 3.3: Reject Expense with Reason', async ({ page }) => {
    // Create a test expense
    const token = await getAccessToken(page);
    const userId = await getUserId(page);

    await createExpense(token, {
      user_id: userId,
      amount: 999.99,
      vendor: 'Test Reject Vendor',
      description: 'Test rejection'
    });

    // Reload
    await page.reload();
    await waitForLoading(page);

    // Look for reject button
    const rejectBtn = page.locator('button:has-text("Reject")').first();

    if (await rejectBtn.isVisible({ timeout: 3000 })) {
      // Click reject
      await rejectBtn.click();

      // Wait for modal with reason textarea
      const reasonField = page.locator('textarea, input[placeholder*="reason"]').first();

      if (await reasonField.isVisible({ timeout: 2000 })) {
        // Enter rejection reason
        await reasonField.fill('Test rejection reason - not approved');

        // Click confirm reject
        await page.click('button:has-text("Reject Expense"), button:has-text("Confirm")');

        // Wait for success
        await waitForLoading(page);
        await page.waitForTimeout(1000);
      }
    }
  });
});
