// @ts-check
import { test, expect } from '@playwright/test';
import {
  BASE_URL,
  clickWithOverlayTolerance,
  expectToastMessage,
  login,
} from './helpers/ui';

const getExpenseForm = (page) =>
  page.getByRole('heading', { name: /submit new expense/i }).locator('..');

const expectPendingApprovalEmptyState = async (page) => {
  const backups = [/all caught up/i, /no pending/i, /caught up with approvals/i];
  for (const pattern of backups) {
    const candidate = page.locator(`text=${pattern}`);
    if (await candidate.count()) {
      await expect(candidate.first()).toBeVisible({ timeout: 5000 });
      return;
    }
  }

  // Fallback: look for a generic empty-state heading
  await expect(
    page.getByRole("heading", { name: /pending expense requests/i }),
  ).toBeVisible({ timeout: 5000 });
};


test.describe('Expense Submission Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display expense submission form', async ({ page }) => {
    // Navigate to expense submission page
    await page.getByRole('button', { name: /new expense/i }).click();

    // Check form elements
    await expect(page.getByRole('heading', { name: /submit new expense/i })).toBeVisible();
    await expect(page.getByLabel(/amount/i)).toBeVisible();
    await expect(page.getByLabel(/vendor/i)).toBeVisible();
    await expect(page.getByLabel(/category/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
  });

  test('should submit expense successfully', async ({ page }) => {
    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Fill form
    const today = new Date().toISOString().split('T')[0];
    await page.getByLabel(/expense date/i).fill(today);
    await page.getByLabel(/amount/i).fill('150.00');
    await page.getByLabel(/vendor/i).fill('Test Vendor Inc');
    await page.getByLabel(/category/i).selectOption({ label: 'Meals' });
    await page.getByLabel(/description/i).fill('Business lunch with client');

    // Submit
    const submitButton = getExpenseForm(page).getByRole('button', { name: /^submit$/i });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Check for success toast message
    await expectToastMessage(page, /expense submitted successfully/i, 10000);

    // Should redirect or show expense in list
    await page.waitForLoadState('networkidle');
  });

  test('should validate required fields', async ({ page }) => {
    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Try to submit empty form
    const submitButton = getExpenseForm(page).getByRole('button', { name: /^submit$/i });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Should show validation toast
    await expectToastMessage(
      page,
      /please fill in all required fields/i,
      5000,
    );
  });

  test('should validate amount field', async ({ page }) => {
    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Enter invalid amount
    const today = new Date().toISOString().split('T')[0];
    await page.getByLabel(/expense date/i).fill(today);
    await page.getByLabel(/amount/i).fill('-50');
    await page.getByLabel(/vendor/i).fill('Negative Test Vendor');
    await page.getByLabel(/description/i).fill('Negative amount test');

    const submitButton = getExpenseForm(page).getByRole('button', { name: /^submit$/i });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Should show validation toast for amount
    await expectToastMessage(
      page,
      /amount must be positive/i,
      10000,
    );
  });

  test('should upload receipt', async ({ page }) => {
    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Fill basic fields
    await page.getByLabel(/amount/i).fill('100.00');
    await page.getByLabel(/vendor/i).fill('Receipt Test Vendor');
    await page.getByLabel(/category/i).selectOption({ label: 'Travel' });
    await page.getByLabel(/description/i).fill('Test with receipt');

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
    await expect(page.getByRole('heading', { name: /active expenses/i })).toBeVisible();

    // Should show expenses or empty state
    const hasExpenses = await page.locator('table, .expense-card, .expense-item').count();
    if (hasExpenses > 0) {
      await expect(page.locator('text=/pending|approved|rejected/i').first()).toBeVisible();
    } else {
      await expect(page.locator('text=/all caught up|no expenses/i').first()).toBeVisible();
    }
  });

  test('should filter expenses by status', async ({ page }) => {
    // Navigate to history tab where status filter exists
    await page.getByRole('button', { name: /history/i }).click();

    // Look for status filter
    const statusFilter = page.locator('select').first();
    if (await statusFilter.count() > 0) {
      await statusFilter.selectOption('approved');

      // Should filter expenses
      await page.waitForLoadState('networkidle');
      const expenseTable = page.locator('table');
      if (await expenseTable.count() > 0) {
        await expect(expenseTable.locator('text=APPROVED').first()).toBeVisible();
      } else {
      await expect(page.getByText(/no expenses match the current filter/i)).toBeVisible();
      }
    }
  });

  test('should view expense details', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /active expenses/i })).toBeVisible();
    const expenseTable = page.locator('table');
    if (await expenseTable.count() > 0) {
      await expect(expenseTable.locator('text=Amount').first()).toBeVisible();
      await expect(expenseTable.locator('text=Vendor').first()).toBeVisible();
      await expect(expenseTable.locator('text=Category').first()).toBeVisible();
    } else {
      await expect(page.getByText('All caught up!')).toBeVisible();
    }
  });
});

test.describe('Expense Approval Flow (Admin/Manager)', () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await login(page, 'admintest', 'Testme1!');
  });

  test('should display pending expenses for approval', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /pending expense requests/i }),
    ).toBeVisible();

    // Should show pending expenses or empty state
    const hasPending = await page.getByRole('button', { name: /approve via ap2/i }).count();
    if (hasPending > 0) {
      await expect(page.getByRole('button', { name: /approve via ap2/i }).first()).toBeVisible();
    } else {
      await expectPendingApprovalEmptyState(page);
    }
  });

  test('should approve expense', async ({ page }) => {
    // Find approve button
    const approveButton = page.getByRole('button', { name: /approve via ap2/i }).first();
    if (await approveButton.count() > 0) {
      await approveButton.click();

      // Check for success message
      await expect(page.locator('text=/approved|success/i')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should reject expense with reason', async ({ page }) => {
    // Find reject button
    const rejectButton = page.getByRole('button', { name: /^reject$/i }).first();
    if (await rejectButton.count() > 0) {
      await rejectButton.click();

      // Fill rejection reason
      await page.getByLabel(/rejection reason/i).fill('Does not comply with expense policy');
      await page.getByRole('button', { name: /reject expense/i }).click();

      // Check for success message
      await expect(page.locator('text=/rejected|declined|success/i')).toBeVisible({ timeout: 5000 });
    }
  });
});
