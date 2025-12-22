/**
 * Authentication helper functions for Playwright tests
 */

export const ADMIN_CREDENTIALS = {
  username: 'admintest',
  password: 'Testme1!',
};

export const EMPLOYEE_CREDENTIALS = {
  username: 'emptest',
  password: 'EmpTest123!',
};

/**
 * Login as admin user
 * @param {import('@playwright/test').Page} page
 */
export async function loginAsAdmin(page) {
  await page.goto('/');

  // Wait for login page
  await page.waitForSelector('input[type="text"]', { timeout: 10000 });

  // Enter credentials
  await page.fill('input[type="text"]', ADMIN_CREDENTIALS.username);
  await page.fill('input[type="password"]', ADMIN_CREDENTIALS.password);

  // Click sign in
  await page.click('button:has-text("Sign In")');

  // Wait for dashboard to load
  await page.waitForSelector('text=Admin Dashboard', { timeout: 10000 });
}

/**
 * Login as employee user
 * @param {import('@playwright/test').Page} page
 */
export async function loginAsEmployee(page) {
  await page.goto('/');

  // Wait for login page
  await page.waitForSelector('input[type="text"]', { timeout: 10000 });

  // Enter credentials
  await page.fill('input[type="text"]', EMPLOYEE_CREDENTIALS.username);
  await page.fill('input[type="password"]', EMPLOYEE_CREDENTIALS.password);

  // Click sign in
  await page.click('button:has-text("Sign In")');

  // Wait for dashboard to load
  await page.waitForLoadState('networkidle');
}

/**
 * Logout current user
 * @param {import('@playwright/test').Page} page
 */
export async function logout(page) {
  // Look for logout button
  const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Log Out"), button:has-text("Sign Out")').first();

  if (await logoutButton.isVisible({ timeout: 1000 }).catch(() => false)) {
    await logoutButton.click();
    await page.waitForURL('/', { timeout: 5000 });
  }
}

/**
 * Check if user is logged in
 * @param {import('@playwright/test').Page} page
 */
export async function isLoggedIn(page) {
  try {
    await page.waitForSelector('text=Dashboard', { timeout: 2000 });
    return true;
  } catch {
    return false;
  }
}
