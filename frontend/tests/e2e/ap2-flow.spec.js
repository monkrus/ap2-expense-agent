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

/**
 * Helper: authenticate via API and return { token, orgId } for direct API calls.
 */
const getApiCredentials = async (page) => {
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  const orgId = await page.evaluate(() =>
    localStorage.getItem('current_organization_id'),
  );
  return { token, orgId };
};

/**
 * Helper: create an intent mandate via the backend API.
 */
const createIntentMandate = async (page, constraints, expirationHours = 24) => {
  const { token, orgId } = await getApiCredentials(page);
  const response = await page.request.post(`${BASE_URL}/api/ap2/intent-mandate`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Organization-Id': orgId,
    },
    data: {
      constraints,
      expiration_hours: expirationHours,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
};

test.describe('AP2 Auto-Approval Flow', () => {
  // Use emptest (employee) so we get the Employee Dashboard with "New Expense" button.
  // Intent mandate creation only requires authentication, not admin role.
  test.beforeEach(async ({ page }) => {
    await login(page, 'emptest', 'Testme1!');
  });

  test('expense matching intent mandate is auto-approved', async ({ page }) => {
    // Create an intent mandate allowing meals up to $500 at AP2 Test Restaurant
    await createIntentMandate(page, {
      max_amount: 500.0,
      monthly_limit: 5000.0,
      categories: ['meals'],
      merchants: ['AP2 Test Restaurant'],
    });

    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Fill form with values matching the mandate constraints
    const today = new Date().toISOString().split('T')[0];
    await page.getByLabel(/expense date/i).fill(today);
    await page.getByLabel(/amount/i).fill('45.00');
    await page.getByLabel(/vendor/i).fill('AP2 Test Restaurant');
    await page.getByLabel(/category/i).selectOption({ label: 'Meals' });
    await page.getByLabel(/description/i).fill('Business lunch - AP2 auto-approval test');

    // Submit the expense
    const submitButton = getExpenseForm(page).getByRole('button', {
      name: /^submit$/i,
    });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Verify auto-approval toast from intent mandate
    await expectToastMessage(
      page,
      /auto-approved.*intent mandate|auto-approved.*ai agent/i,
      10000,
    );

    // Wait for page to settle
    await page.waitForLoadState('networkidle');

    // Verify the expense shows as approved in the list
    const approvedBadge = page.locator('text=/approved/i').first();
    await expect(approvedBadge).toBeVisible({ timeout: 10000 });
  });

  test('expense not matching intent mandate stays pending', async ({ page }) => {
    // Navigate to expense submission (no matching mandate for this vendor)
    await page.getByRole('button', { name: /new expense/i }).click();

    // Fill form with a vendor that does NOT match any mandate
    const today = new Date().toISOString().split('T')[0];
    await page.getByLabel(/expense date/i).fill(today);
    await page.getByLabel(/amount/i).fill('75.00');
    await page.getByLabel(/vendor/i).fill('Unmatched Vendor XYZ');
    await page.getByLabel(/category/i).selectOption({ label: 'Travel' });
    await page.getByLabel(/description/i).fill('Travel expense - should stay pending');

    // Submit the expense
    const submitButton = getExpenseForm(page).getByRole('button', {
      name: /^submit$/i,
    });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Verify normal submission toast (not auto-approved)
    await expectToastMessage(
      page,
      /expense submitted successfully/i,
      10000,
    );

    // Wait for page to settle
    await page.waitForLoadState('networkidle');
  });

  test('expense exceeding mandate amount is not auto-approved', async ({ page }) => {
    // Create mandate with low max_amount for a UNIQUE merchant
    // (avoids conflict with test 1's $500 mandate for "AP2 Test Restaurant")
    await createIntentMandate(page, {
      max_amount: 50.0,
      monthly_limit: 5000.0,
      categories: ['meals'],
      merchants: ['AP2 Budget Cafe'],
    });

    // Navigate to expense submission
    await page.getByRole('button', { name: /new expense/i }).click();

    // Fill form with amount exceeding the mandate limit
    const today = new Date().toISOString().split('T')[0];
    await page.getByLabel(/expense date/i).fill(today);
    await page.getByLabel(/amount/i).fill('150.00');
    await page.getByLabel(/vendor/i).fill('AP2 Budget Cafe');
    await page.getByLabel(/category/i).selectOption({ label: 'Meals' });
    await page.getByLabel(/description/i).fill('Over-limit expense - should not auto-approve');

    // Submit the expense
    const submitButton = getExpenseForm(page).getByRole('button', {
      name: /^submit$/i,
    });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, submitButton);

    // Verify normal submission (not auto-approved)
    await expectToastMessage(
      page,
      /expense submitted successfully/i,
      10000,
    );

    await page.waitForLoadState('networkidle');
  });
});
