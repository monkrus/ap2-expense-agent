// @ts-check
import { test, expect } from '@playwright/test';
import { BASE_URL, clickWithOverlayTolerance, login } from './helpers/ui';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('should display login page', async ({ page }) => {
    await expect(page).toHaveTitle(/AP2 Expense/i);

    // Check for login form elements
    await expect(page.getByLabel('Username')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    // Fill login form
    await page.getByLabel('Username').fill('emptest');
    await page.getByLabel('Password').fill('Testme1!');

    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show authenticated dashboard content
    await expect(page.getByRole('heading', { name: /my expenses/i })).toBeVisible();

    // Check for authenticated content
    await expect(page.getByTitle('Logout')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Fill login form with invalid credentials
    await page.getByLabel('Username').fill('invaliduser');
    await page.getByLabel('Password').fill('wrongpassword');

    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show error message
    await expect(page.locator('text=/invalid|incorrect|error/i')).toBeVisible({timeout: 5000});

    // Should remain on login page
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await login(page);

    // Find and click logout button
    const logoutButton = page.getByTitle('Logout');
    await logoutButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(page, logoutButton);

    // Wait for redirect
    await page.waitForLoadState('networkidle');

    // Should be back on login page
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should handle token expiration', async ({ page }) => {
    // This test would require manipulating token expiry
    // For now, it's a placeholder for future implementation
    test.skip();
  });
});

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    // Try to access a protected route directly
    await page.goto(`${BASE_URL}/organizations`);

    // Should redirect to login
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should allow access to protected routes when authenticated', async ({ page }) => {
    // Login
    await page.goto(BASE_URL);
    await page.getByLabel('Username').fill('emptest');
    await page.getByLabel('Password').fill('Testme1!');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByTitle('Logout')).toBeVisible();

    // Access protected route
    await page.goto(`${BASE_URL}/organizations`);

    // Should not redirect
    await expect(
      page.getByRole('heading', { name: /organization management/i }),
    ).toBeVisible({ timeout: 10000 });
  });
});
