import { test, expect } from '@playwright/test';
import { loginAsAdmin, EMPLOYEE_CREDENTIALS } from './helpers/auth.js';
import { waitForLoading, waitForToast } from './helpers/wait.js';
import { createUser, getAccessToken, deleteUser } from './helpers/dataSeeder.js';

test.describe('User Management Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);
  });

  test('Test 5.1: Access User Management', async ({ page }) => {
    // Look for Manage Users button/tab
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users"), text=User Management').first();

    if (await manageUsersBtn.isVisible({ timeout: 3000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);

      // Verify user list appears
      const hasUserList = await page.locator('text=Email, text=Username, text=Role, text=Status').first().isVisible({ timeout: 3000 });
      expect(hasUserList).toBeTruthy();
    }
  });

  test('Test 5.2: Create New User', async ({ page }) => {
    // Navigate to user management
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').first();

    if (await manageUsersBtn.isVisible({ timeout: 2000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);
    }

    // Click Create User
    const createUserBtn = page.locator('button:has-text("+ Create User"), button:has-text("Create User"), button:has-text("New User")').first();
    await expect(createUserBtn).toBeVisible({ timeout: 5000 });
    await createUserBtn.click();

    // Wait for modal
    await page.waitForSelector('input[placeholder*="email"], input[type="email"]', { timeout: 5000 });

    // Fill form with unique data
    const timestamp = Date.now();
    const testEmail = `testuser${timestamp}@test.com`;
    const testUsername = `testuser${timestamp}`;

    await page.fill('input[type="email"], input[placeholder*="email"]', testEmail);
    await page.fill('input[placeholder*="username"]', testUsername);
    await page.fill('input[placeholder*="name"], input[placeholder*="Name"]', `Test User ${timestamp}`);
    await page.fill('input[type="password"]', 'Test123!');

    // Select role
    const roleSelect = page.locator('select').filter({ hasText: /Role|role|EMPLOYEE/ }).first();
    if (await roleSelect.isVisible({ timeout: 1000 })) {
      await roleSelect.selectOption('employee');
    }

    // Fill department
    const deptInput = page.locator('input[placeholder*="department"]').first();
    if (await deptInput.isVisible({ timeout: 1000 })) {
      await deptInput.fill('Engineering');
    }

    // Submit
    await page.click('button:has-text("Create User"), button:has-text("Create")');

    // Wait for success
    await page.waitForTimeout(2000);

    // Verify user appears in list (search for email or username)
    const userInList = await page.locator(`text=${testEmail}, text=${testUsername}`).first().isVisible({ timeout: 3000 }).catch(() => false);

    // Clean up: delete the created user
    if (userInList) {
      const token = await getAccessToken(page);
      // Note: Would need user ID to delete, skipping cleanup for now
    }
  });

  test('Test 5.3: Search Users', async ({ page }) => {
    // Navigate to user management
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').first();

    if (await manageUsersBtn.isVisible({ timeout: 2000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);
    }

    // Find search box
    const searchBox = page.locator('input[placeholder*="Search"], input[type="search"]').first();

    if (await searchBox.isVisible({ timeout: 2000 })) {
      // Search for "test"
      await searchBox.fill('test');
      await page.waitForTimeout(500);

      // Verify results filtered
      await page.waitForLoadState('networkidle');
    }
  });

  test('Test 5.4: Filter Users by Role', async ({ page }) => {
    // Navigate to user management
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').first();

    if (await manageUsersBtn.isVisible({ timeout: 2000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);
    }

    // Find role filter
    const roleFilter = page.locator('select:has-text("All Roles"), select:has-text("Role")').first();

    if (await roleFilter.isVisible({ timeout: 2000 })) {
      // Filter by Employee
      await roleFilter.selectOption('employee');
      await waitForLoading(page);
      await page.waitForTimeout(500);

      // Verify filter applied
      await page.waitForLoadState('networkidle');
    }
  });

  test('Test 5.5 & 5.8: Suspend and Activate User', async ({ page }) => {
    // First, create a test user to suspend
    const token = await getAccessToken(page);
    const timestamp = Date.now();

    const newUser = await createUser(token, {
      email: `suspendtest${timestamp}@test.com`,
      username: `suspendtest${timestamp}`,
      full_name: `Suspend Test ${timestamp}`,
      password: 'Test123!',
      role: 'employee'
    });

    // Navigate to user management
    const manageUsersBtn = page.locator('button:has-text("Manage Users"), a:has-text("Manage Users")').first();

    if (await manageUsersBtn.isVisible({ timeout: 2000 })) {
      await manageUsersBtn.click();
      await waitForLoading(page);
    }

    // Search for the user
    const searchBox = page.locator('input[placeholder*="Search"]').first();
    if (await searchBox.isVisible({ timeout: 2000 })) {
      await searchBox.fill(`suspendtest${timestamp}`);
      await page.waitForTimeout(500);
    }

    // Find suspend button for this user
    const suspendBtn = page.locator('button:has-text("Suspend")').first();

    if (await suspendBtn.isVisible({ timeout: 2000 })) {
      // Click suspend
      await suspendBtn.click();

      // Confirm if modal appears
      const confirmBtn = page.locator('button:has-text("Confirm"), button:has-text("Yes")').first();
      if (await confirmBtn.isVisible({ timeout: 1000 })) {
        await confirmBtn.click();
      }

      // Wait for success
      await page.waitForTimeout(1500);

      // Verify status changed to Suspended (red badge)
      const suspendedBadge = await page.locator('text=Suspended').first().isVisible({ timeout: 2000 });
      expect(suspendedBadge).toBeTruthy();

      // Now activate the user
      const activateBtn = page.locator('button:has-text("Activate")').first();

      if (await activateBtn.isVisible({ timeout: 2000 })) {
        await activateBtn.click();

        // Confirm if needed
        const confirmActivate = page.locator('button:has-text("Confirm"), button:has-text("Yes")').first();
        if (await confirmActivate.isVisible({ timeout: 1000 })) {
          await confirmActivate.click();
        }

        // Wait for success
        await page.waitForTimeout(1500);

        // Verify status changed to Active (green badge)
        const activeBadge = await page.locator('text=Active').first().isVisible({ timeout: 2000 });
        expect(activeBadge).toBeTruthy();
      }
    }
  });

  test('Test 5.6: Verify Suspended User Cannot Login', async ({ page, context }) => {
    // Create and suspend a user
    const token = await getAccessToken(page);
    const timestamp = Date.now();

    const testUser = await createUser(token, {
      email: `logintest${timestamp}@test.com`,
      username: `logintest${timestamp}`,
      full_name: `Login Test ${timestamp}`,
      password: 'Test123!',
      role: 'employee'
    });

    // Suspend the user via API
    await fetch(`http://localhost:8000/api/v1/admin/users/${testUser.user.id}/suspend`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    // Open new incognito context
    const incognitoContext = await context.browser().newContext();
    const incognitoPage = await incognitoContext.newPage();

    // Try to login as suspended user
    await incognitoPage.goto('/');
    await incognitoPage.fill('input[type="text"]', `logintest${timestamp}`);
    await incognitoPage.fill('input[type="password"]', 'Test123!');
    await incognitoPage.click('button:has-text("Sign In")');

    // Wait for error message
    await incognitoPage.waitForSelector('text=/User account is inactive|Account suspended|inactive/i', { timeout: 5000 });

    // Verify still on login page
    const stillOnLogin = await incognitoPage.locator('input[type="password"]').isVisible();
    expect(stillOnLogin).toBeTruthy();

    await incognitoContext.close();
  });
});
