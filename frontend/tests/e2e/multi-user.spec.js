// @ts-check
import { test, expect } from '@playwright/test';
import {
  clickWithOverlayTolerance,
  expectToastMessage,
  login,
} from './helpers/ui';

const fillExpenseForm = async (page, options = {}) => {
  const {
    amount = '6200.00',
    vendor = 'Workflow Vendor',
    description = 'Multi-user workflow expense',
    categoryLabel = 'Travel',
  } = options;

  const today = new Date().toISOString().split('T')[0];
  await page.getByLabel(/expense date/i).fill(today);
  await page.getByLabel(/amount/i).fill(amount);
  await page.getByLabel(/vendor/i).fill(vendor);
  await page.getByLabel(/category/i).selectOption({ label: categoryLabel });
  await page.getByLabel(/description/i).fill(description);
};

const getExpenseForm = (page) =>
  page.getByRole('heading', { name: /submit new expense/i }).locator('..');

test.describe('Multi-User Workflow', () => {
  test('employee submits expense that admin approves', async ({ browser }) => {
    const employeePage = await browser.newPage();
    await login(employeePage);

    await employeePage.getByRole('button', { name: /new expense/i }).click();
    await fillExpenseForm(employeePage, {
    amount: '6200.00',
    vendor: 'API Workflow Inc',
    description: 'Multi-user scenario expense',
    categoryLabel: 'Travel',
  });

    const submitButton = getExpenseForm(employeePage).getByRole('button', {
      name: /^submit$/i,
    });
    await submitButton.scrollIntoViewIfNeeded();
    await clickWithOverlayTolerance(employeePage, submitButton);
    await expectToastMessage(employeePage, /expense submitted successfully/i, 10000);

    const managerPage = await browser.newPage();
    await login(managerPage, 'admintest');
    console.log(
      'org context',
      await employeePage.evaluate(() => localStorage.getItem('current_organization_id')),
      await managerPage.evaluate(() => localStorage.getItem('current_organization_id')),
    );
    await expect(
      managerPage.getByRole('heading', { name: /pending expense requests/i }),
    ).toBeVisible({ timeout: 10000 });

    const pendingApprovalsButton = managerPage.getByRole('button', { name: /pending approvals/i }).first();
    if (await pendingApprovalsButton.count()) {
      await pendingApprovalsButton.click();
      await managerPage.waitForTimeout(1000);
    }

    const refreshButton = managerPage.getByRole('button', { name: /^refresh$/i }).first();
    if (await refreshButton.count()) {
      await clickWithOverlayTolerance(managerPage, refreshButton);
      await managerPage.waitForTimeout(1200);
    }

    console.log(
      'raw button names',
      await managerPage.evaluate(() =>
        Array.from(document.querySelectorAll('button'))
          .map((btn) => btn.innerText.trim())
          .filter(Boolean),
      ),
    );

    const pendingExpenseText = managerPage.getByText(/multi-user scenario expense/i).first();
    await expect(pendingExpenseText).toBeVisible({ timeout: 15000 });

    const approveButton = managerPage.getByRole('button', { name: /approve via ap2/i }).first();
    await expect(approveButton).toBeVisible({ timeout: 10000 });
    await clickWithOverlayTolerance(managerPage, approveButton);
    await expectToastMessage(managerPage, /approved|success/i, 5000);

    await employeePage.reload();
    await expect(employeePage.locator('text=APPROVED').first()).toBeVisible({
      timeout: 10000,
    });

    await managerPage.close();
    await employeePage.close();
  });
});
