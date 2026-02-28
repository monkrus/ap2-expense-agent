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
    await expect(page.locator('#login-password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    // Fill login form
    await page.getByLabel('Username').fill('emptest');
    await page.locator('#login-password').fill('Testme1!');

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
    await page.locator('#login-password').fill('wrongpassword');

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
    // Login normally to establish a valid session
    await login(page);

    // Overwrite both tokens with invalid values to simulate expiration
    // (access token expired, refresh token also invalid so refresh fails)
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired.invalid.token');
      localStorage.setItem('refresh_token', 'expired.invalid.refresh');
    });

    // Reload so React re-reads from localStorage and fires API calls with the bad token
    await page.reload();

    // App should detect 401, attempt refresh (also 401), then logout and redirect to login
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible({ timeout: 15000 });

    // Confirm tokens were cleared from localStorage
    const accessToken = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(accessToken).toBeNull();
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
    await page.locator('#login-password').fill('Testme1!');
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
