// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

// Helper function to login
async function login(page, username = 'adminfree', password = 'Testme1!') {
  await page.goto(BASE_URL);
  await page.fill('input[name="username"], input[type="text"]', username);
  await page.fill('input[name="password"], input[type="password"]', password);
  await page.click('button[type="submit"], button:has-text("Login")');
  await page.waitForLoadState('networkidle');
}

test.describe('Expense Submission Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display expense submission form', async ({ page }) => {
    // Navigate to expense submission page
    await page.click('text=/submit|new expense/i');

    // Check form elements
    await expect(page.locator('input[name="amount"], input[placeholder*="amount" i]')).toBeVisible();
    await expect(page.locator('input[name="vendor"], input[placeholder*="vendor" i]')).toBeVisible();
    await expect(page.locator('select[name="category"], input[name="category"]')).toBeVisible();
    await expect(page.locator('textarea[name="description"], input[name="description"]')).toBeVisible();
  });

  test('should submit expense successfully', async ({ page }) => {
    // Navigate to expense submission
    await page.click('text=/submit|new expense/i');

    // Fill form
    await page.fill('input[name="amount"], input[placeholder*="amount" i]', '150.00');
    await page.fill('input[name="vendor"], input[placeholder*="vendor" i]', 'Test Vendor Inc');
    await page.selectOption('select[name="category"]', { label: /travel|meals/i });
    await page.fill('textarea[name="description"], input[name="description"]', 'Business lunch with client');

    // Submit
    await page.click('button[type="submit"], button:has-text(/submit|save/i)');

    // Check for success message
    await expect(page.locator('text=/success|submitted/i')).toBeVisible({ timeout: 5000 });

    // Should redirect or show expense in list
    await page.waitForLoadState('networkidle');
  });

  test('should validate required fields', async ({ page }) => {
    // Navigate to expense submission
    await page.click('text=/submit|new expense/i');

    // Try to submit empty form
    await page.click('button[type="submit"], button:has-text(/submit|save/i)');

    // Should show validation errors
    await expect(page.locator('text=/required|mandatory/i')).toBeVisible({ timeout: 3000 });
  });

  test('should validate amount field', async ({ page }) => {
    // Navigate to expense submission
    await page.click('text=/submit|new expense/i');

    // Enter invalid amount
    await page.fill('input[name="amount"], input[placeholder*="amount" i]', '-50');

    // Should show validation error
    await expect(page.locator('text=/invalid|positive|greater/i')).toBeVisible({ timeout: 3000 });
  });

  test('should upload receipt', async ({ page }) => {
    // Navigate to expense submission
    await page.click('text=/submit|new expense/i');

    // Fill basic fields
    await page.fill('input[name="amount"], input[placeholder*="amount" i]', '100.00');
    await page.fill('input[name="vendor"], input[placeholder*="vendor" i]', 'Receipt Test Vendor');
    await page.selectOption('select[name="category"]', { index: 1 });
    await page.fill('textarea[name="description"], input[name="description"]', 'Test with receipt');

    // Upload receipt (if file input exists)
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles({
        name: 'receipt.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-image-data'),
      });

      // Check for upload confirmation
      await expect(page.locator('text=/uploaded|attached/i')).toBeVisible({ timeout: 3000 });
    }
  });
});

test.describe('Expense List & Status', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display expense list', async ({ page }) => {
    // Navigate to expenses page
    await page.click('text=/my expenses|expenses/i');

    // Should show expenses or empty state
    const hasExpenses = await page.locator('table, .expense-card, .expense-item').count();
    if (hasExpenses > 0) {
      await expect(page.locator('text=/pending|approved|rejected/i')).toBeVisible();
    } else {
      await expect(page.locator('text=/no expenses|empty/i')).toBeVisible();
    }
  });

  test('should filter expenses by status', async ({ page }) => {
    // Navigate to expenses page
    await page.click('text=/my expenses|expenses/i');

    // Look for status filter
    const statusFilter = page.locator('select[name="status"], button:has-text("Status")');
    if (await statusFilter.count() > 0) {
      await statusFilter.click();
      await page.click('text=/pending/i');

      // Should filter expenses
      await page.waitForLoadState('networkidle');
      await expect(page.locator('text=/pending/i')).toBeVisible();
    }
  });

  test('should view expense details', async ({ page }) => {
    // Navigate to expenses page
    await page.click('text=/my expenses|expenses/i');

    // Click on first expense (if any)
    const firstExpense = page.locator('tr, .expense-card, .expense-item').first();
    if (await firstExpense.count() > 0) {
      await firstExpense.click();

      // Should show details
      await expect(page.locator('text=/amount|vendor|category/i')).toBeVisible();
    }
  });
});

test.describe('Expense Approval Flow (Admin/Manager)', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await login(page, 'adminfree', 'Testme1!');
  });

  test('should display pending expenses for approval', async ({ page }) => {
    // Navigate to pending/approval page
    await page.click('text=/pending|approve|review/i');

    // Should show pending expenses or empty state
    const hasPending = await page.locator('table, .expense-card').count();
    if (hasPending > 0) {
      await expect(page.locator('button:has-text(/approve/i)')).toBeVisible();
    }
  });

  test('should approve expense', async ({ page }) => {
    // Navigate to pending page
    await page.click('text=/pending|approve|review/i');

    // Find approve button
    const approveButton = page.locator('button:has-text(/approve/i)').first();
    if (await approveButton.count() > 0) {
      await approveButton.click();

      // May need to confirm
      const confirmButton = page.locator('button:has-text(/confirm|yes/i)');
      if (await confirmButton.count() > 0) {
        await confirmButton.click();
      }

      // Check for success message
      await expect(page.locator('text=/approved|success/i')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should reject expense with reason', async ({ page }) => {
    // Navigate to pending page
    await page.click('text=/pending|approve|review/i');

    // Find reject button
    const rejectButton = page.locator('button:has-text(/reject|decline/i)').first();
    if (await rejectButton.count() > 0) {
      await rejectButton.click();

      // Fill rejection reason
      const reasonInput = page.locator('textarea[name="reason"], input[name="reason"]');
      if (await reasonInput.count() > 0) {
        await reasonInput.fill('Does not comply with expense policy');
        await page.click('button:has-text(/submit|confirm/i)');

        // Check for success message
        await expect(page.locator('text=/rejected|declined/i')).toBeVisible({ timeout: 5000 });
      }
    }
  });
});
