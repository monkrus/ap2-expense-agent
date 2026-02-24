import { expect } from '@playwright/test';

export const BASE_URL = process.env.BASE_URL || 'http://localhost:5174';

export const expectToastMessage = async (page, messagePattern, timeout = 10000) => {
  const toastMessage = page.locator('[data-testid="toast-message"]', {
    hasText: messagePattern,
  });
  await expect(toastMessage).toBeVisible({ timeout });
};

export const waitForBlockingOverlay = async (page) => {
  const overlay = page.locator('div.fixed.inset-0');
  if ((await overlay.count()) === 0) {
    return;
  }
  try {
    await overlay.first().waitFor({ state: 'detached', timeout: 5000 });
  } catch {
    // swallow: overlay might not disappear in time
  }
  await page.waitForTimeout(250);
};

export const clickWithOverlayTolerance = async (page, locator) => {
  await waitForBlockingOverlay(page);
  const viewport = await page.viewportSize();
  const options = viewport && viewport.width < 768 ? { force: true } : {};
  await locator.click(options);
};

export const login = async (page, username = 'emptest', password = 'Testme1!') => {
  await page.goto(BASE_URL);
  await page.getByLabel('Username').fill(username);
  await page.locator('#login-password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByTitle('Logout')).toBeVisible({ timeout: 15000 });
  await page.waitForFunction(() => localStorage.getItem('current_organization_id'));
};
