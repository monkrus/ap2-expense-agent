// @ts-check
const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('should display login page', async ({ page }) => {
    await expect(page).toHaveTitle(/AP2 Expense/i);

    // Check for login form elements
    await expect(page.locator('input[name="username"], input[type="text"]')).toBeVisible();
    await expect(page.locator('input[name="password"], input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"], button:has-text("Login")')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    // Fill login form
    await page.fill('input[name="username"], input[type="text"]', 'emptest');
    await page.fill('input[name="password"], input[type="password"]', 'AgentTest!');

    // Submit form
    await page.click('button[type="submit"], button:has-text("Login")');

    // Wait for navigation
    await page.waitForLoadState('networkidle');

    // Should be redirected to dashboard/expenses page
    await expect(page).toHaveURL(/\/(dashboard|expenses)/);

    // Check for authenticated content
    await expect(page.locator('text=/logout/i')).toBeVisible();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    // Fill login form with invalid credentials
    await page.fill('input[name="username"], input[type="text"]', 'invaliduser');
    await page.fill('input[name="password"], input[type="password"]', 'wrongpassword');

    // Submit form
    await page.click('button[type="submit"], button:has-text("Login")');

    // Should show error message
    await expect(page.locator('text=/invalid|incorrect|error/i')).toBeVisible({timeout: 5000});

    // Should remain on login page
    await expect(page).toHaveURL(/login|^\//);
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('input[name="username"], input[type="text"]', 'emptest');
    await page.fill('input[name="password"], input[type="password"]', 'AgentTest!');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    // Find and click logout button
    await page.click('text=/logout/i');

    // Wait for redirect
    await page.waitForLoadState('networkidle');

    // Should be back on login page
    await expect(page).toHaveURL(/login|^\//);
    await expect(page.locator('input[name="username"], input[type="text"]')).toBeVisible();
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
    await page.goto(`${BASE_URL}/dashboard`);

    // Should redirect to login
    await expect(page).toHaveURL(/login|^\//);
  });

  test('should allow access to protected routes when authenticated', async ({ page }) => {
    // Login
    await page.goto(BASE_URL);
    await page.fill('input[name="username"], input[type="text"]', 'emptest');
    await page.fill('input[name="password"], input[type="password"]', 'AgentTest!');
    await page.click('button[type="submit"], button:has-text("Login")');
    await page.waitForLoadState('networkidle');

    // Access protected route
    await page.goto(`${BASE_URL}/expenses`);

    // Should not redirect
    await expect(page).toHaveURL(/expenses/);
  });
});
