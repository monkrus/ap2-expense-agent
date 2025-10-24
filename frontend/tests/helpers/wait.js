/**
 * Wait helper functions for Playwright tests
 */

/**
 * Wait for toast notification to appear and disappear
 * @param {import('@playwright/test').Page} page
 * @param {string} message - Expected message in toast
 */
export async function waitForToast(page, message) {
  // Wait for toast to appear
  const toast = page.locator(`text=${message}`).first();
  await toast.waitFor({ state: 'visible', timeout: 5000 });

  // Optionally wait for it to disappear
  await toast.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
}

/**
 * Wait for loading spinner to disappear
 * @param {import('@playwright/test').Page} page
 */
export async function waitForLoading(page) {
  // Wait for any loading spinners to disappear
  await page.waitForSelector('.animate-spin', { state: 'hidden', timeout: 10000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
}

/**
 * Wait for modal to appear
 * @param {import('@playwright/test').Page} page
 * @param {string} title - Modal title
 */
export async function waitForModal(page, title) {
  await page.waitForSelector(`text=${title}`, { timeout: 5000 });
}

/**
 * Close modal by clicking backdrop or close button
 * @param {import('@playwright/test').Page} page
 */
export async function closeModal(page) {
  // Try clicking close button first
  const closeButton = page.locator('button:has-text("Cancel"), button:has-text("Close"), button[aria-label="Close"]').first();

  if (await closeButton.isVisible({ timeout: 1000 }).catch(() => false)) {
    await closeButton.click();
  }
}

/**
 * Wait for element to be removed from DOM
 * @param {import('@playwright/test').Page} page
 * @param {string} selector
 */
export async function waitForRemoval(page, selector) {
  await page.waitForSelector(selector, { state: 'detached', timeout: 5000 });
}
