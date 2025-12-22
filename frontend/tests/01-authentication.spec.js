import { test, expect } from '@playwright/test';
import { loginAsAdmin, logout, ADMIN_CREDENTIALS } from './helpers/auth.js';

test.describe('Authentication Tests', () => {
  test('Test 1.1: Admin Login', async ({ page }) => {
    await page.goto('/');

    // Wait for login page
    await page.waitForSelector('input[type="text"]');

    // Enter credentials
    await page.fill('input[type="text"]', ADMIN_CREDENTIALS.username);
    await page.fill('input[type="password"]', ADMIN_CREDENTIALS.password);

    // Click sign in
    await page.click('button:has-text("Sign In")');

    // Verify login successful
    await expect(page).toHaveURL(/\//, { timeout: 10000 });

    // Verify admin interface loads
    await page.waitForLoadState('networkidle');

    // Check for admin dashboard indicators
    const hasAdminDashboard = await page.locator('text=Admin Dashboard, text=Pending Expense Requests, text=Manage Users').first().isVisible({ timeout: 5000 });
    expect(hasAdminDashboard).toBeTruthy();
  });

  test('Test 1.2: Session Persistence', async ({ page }) => {
    // Login
    await loginAsAdmin(page);

    // Refresh page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify still logged in
    const stillLoggedIn = await page.locator('text=Admin Dashboard, text=Pending Expense Requests').first().isVisible({ timeout: 5000 });
    expect(stillLoggedIn).toBeTruthy();
  });

  test('Test 1.3: Logout', async ({ page }) => {
    // Login
    await loginAsAdmin(page);

    // Click logout
    await logout(page);

    // Verify redirected to login
    await expect(page).toHaveURL('/', { timeout: 5000 });

    // Verify cannot access dashboard directly
    await page.goto('/');
    const isLoginPage = await page.locator('input[type="password"]').isVisible();
    expect(isLoginPage).toBeTruthy();
  });

  test('Test 1.4: Invalid Credentials', async ({ page }) => {
    await page.goto('/');

    // Enter invalid credentials
    await page.fill('input[type="text"]', 'wronguser');
    await page.fill('input[type="password"]', 'wrongpass');

    // Click sign in
    await page.click('button:has-text("Sign In")');

    // Wait for error message
    await page.waitForSelector('text=/Incorrect username or password|Login failed|Invalid credentials/i', { timeout: 5000 });

    // Verify still on login page
    await expect(page).toHaveURL('/');
  });
});
