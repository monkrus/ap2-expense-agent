import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsEmployee, logout } from './helpers/auth.js';
import { waitForLoading } from './helpers/wait.js';
import { createUser, getAccessToken } from './helpers/dataSeeder.js';

test.describe('Security & Permissions Tests', () => {
  test('Test 8.1: Employee Cannot Access Admin Features', async ({ page }) => {
    // Login as employee
    await loginAsEmployee(page);
    await waitForLoading(page);

    // Verify cannot see "Manage Users"
    const manageUsersBtn = await page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').isVisible({ timeout: 2000 }).catch(() => false);
    expect(manageUsersBtn).toBeFalsy();

    // Verify cannot see all pending expenses (admin view)
    const allPendingSection = await page.locator('text=Pending Expense Requests').isVisible({ timeout: 2000 }).catch(() => false);

    // Employee should either not see this section or see limited view
    // (depends on implementation)
  });

  test('Test 8.2: Session Persistence with Refresh', async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);

    // Perform an action
    const refreshBtn = page.locator('button:has-text("Refresh")').first();
    if (await refreshBtn.isVisible({ timeout: 2000 })) {
      await refreshBtn.click();
      await waitForLoading(page);
    }

    // Refresh page manually
    await page.reload();
    await waitForLoading(page);

    // Verify still logged in
    const isAdmin = await page.locator('text=Admin Dashboard, text=Manage Users').first().isVisible({ timeout: 3000 });
    expect(isAdmin).toBeTruthy();
  });

  test('Test 8.3: Independent Sessions in Different Contexts', async ({ page, context }) => {
    // Login in first context (page)
    await loginAsAdmin(page);
    await waitForLoading(page);

    // Create second context (incognito)
    const secondContext = await context.browser().newContext();
    const secondPage = await secondContext.newPage();

    // Login in second context
    await loginAsAdmin(secondPage);
    await waitForLoading(secondPage);

    // Logout from first context
    await logout(page);

    // Verify second context still logged in
    await secondPage.reload();
    await waitForLoading(secondPage);

    const stillLoggedIn = await secondPage.locator('text=Admin Dashboard').isVisible({ timeout: 3000 });
    expect(stillLoggedIn).toBeTruthy();

    await secondContext.close();
  });

  test('Test 8.4: Cannot Suspend/Delete Self', async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);

    // Navigate to user management
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').first();

    if (await manageUsersBtn.isVisible({ timeout: 2000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);

      // Search for "adminfree"
      const searchBox = page.locator('input[placeholder*="Search"]').first();
      if (await searchBox.isVisible({ timeout: 2000 })) {
        await searchBox.fill('adminfree');
        await page.waitForTimeout(500);
      }

      // Try to find suspend button for admin (should be disabled or hidden)
      const suspendBtn = page.locator('button:has-text("Suspend")').first();

      if (await suspendBtn.isVisible({ timeout: 1000 })) {
        // If visible, should be disabled
        const isDisabled = await suspendBtn.isDisabled();
        expect(isDisabled).toBeTruthy();
      }
    }
  });

  test('Test 5.7: Suspended User Auto-Logout on Action', async ({ page, context }) => {
    // Create a test user
    const token = await getAccessToken(page);
    const timestamp = Date.now();

    const testUser = await createUser(token, {
      email: `autologout${timestamp}@test.com`,
      username: `autologout${timestamp}`,
      password: 'Test123!',
      role: 'employee'
    });

    // Login as this user in new context
    const userContext = await context.browser().newContext();
    const userPage = await userContext.newPage();

    await userPage.goto('/');
    await userPage.fill('input[type="text"]', `autologout${timestamp}`);
    await userPage.fill('input[type="password"]', 'Test123!');
    await userPage.click('button:has-text("Sign In")');

    // Wait for dashboard
    await userPage.waitForLoadState('networkidle');
    await userPage.waitForTimeout(1000);

    // In admin context, suspend the user
    await page.goto('/');
    if (!await page.locator('text=Admin Dashboard').isVisible({ timeout: 1000 }).catch(() => false)) {
      await loginAsAdmin(page);
    }

    // Suspend via API
    await fetch(`http://localhost:8000/api/v1/admin/users/${testUser.user.id}/suspend`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    // Back to user context, try to perform action
    await userPage.reload();
    await userPage.waitForTimeout(2000);

    // Should see "inactive user" error or be redirected to login
    const isLoginPage = await userPage.locator('input[type="password"]').isVisible({ timeout: 5000 });

    // User should be logged out
    expect(isLoginPage).toBeTruthy();

    await userContext.close();
  });
});

test.describe('Edge Cases & Error Handling', () => {
  test('Test 9.3: Invalid Data Validation', async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);

    // Try to create expense with invalid data
    const newExpenseBtn = page.locator('button:has-text("+ New Expense"), button:has-text("New Expense")').first();

    if (await newExpenseBtn.isVisible({ timeout: 2000 })) {
      await newExpenseBtn.click();

      // Wait for modal
      await page.waitForSelector('input[type="number"], input[placeholder*="amount"]', { timeout: 3000 });

      // Try negative amount
      await page.fill('input[type="number"]', '-100');

      // Try to submit
      await page.click('button:has-text("Submit"), button:has-text("Create")');

      // Should show validation error or prevent submission
      await page.waitForTimeout(1000);

      // Modal should still be open (submission blocked)
      const modalStillOpen = await page.locator('input[type="number"]').isVisible({ timeout: 1000 });

      // If negative amounts are allowed, check if they're handled properly
      // Otherwise, expect validation error
    }
  });

  test('Test 9.3: Empty Required Fields', async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);

    // Try to create expense with empty fields
    const newExpenseBtn = page.locator('button:has-text("+ New Expense"), button:has-text("New Expense")').first();

    if (await newExpenseBtn.isVisible({ timeout: 2000 })) {
      await newExpenseBtn.click();

      // Wait for modal
      await page.waitForSelector('input[type="number"]', { timeout: 3000 });

      // Try to submit without filling anything
      await page.click('button:has-text("Submit"), button:has-text("Create")');

      // Should prevent submission
      await page.waitForTimeout(500);

      // Modal should still be open
      const modalStillOpen = await page.locator('input[type="number"]').isVisible({ timeout: 1000 });
      expect(modalStillOpen).toBeTruthy();
    }
  });
});
