/**
 * Automated UI Test for AP2 Auto-Approval Badges
 * Requires: npm install playwright
 * Run: npx playwright test test_ui_automated.js
 */

const { test, expect } = require('@playwright/test');

test.describe('AP2 Auto-Approval UI Tests', () => {
  test('should display purple AI Agent badge on auto-approved expense', async ({ page }) => {
    // 1. Navigate to app
    await page.goto('http://localhost:5173');

    // 2. Login
    await page.fill('input[name="username"]', 'adminfree');
    await page.fill('input[name="password"]', 'your-password-here');
    await page.click('button[type="submit"]');

    // 3. Wait for dashboard to load
    await page.waitForSelector('text=Employee Dashboard');

    // 4. Look for expense with Amazon vendor
    const amazonExpense = page.locator('text=Amazon').first();
    await expect(amazonExpense).toBeVisible();

    // 5. Check for purple "AI Agent" badge near Amazon expense
    const aiAgentBadge = page.locator('text=✨ AI Agent').first();
    await expect(aiAgentBadge).toBeVisible();

    // 6. Verify badge color is purple (bg-purple-100)
    const badgeElement = await aiAgentBadge.locator('..');
    await expect(badgeElement).toHaveClass(/bg-purple-100/);

    // 7. Check tooltip on hover
    await aiAgentBadge.hover();
    await expect(page.locator('title=*AP2*')).toBeVisible();

    console.log('✅ Purple AI Agent badge displays correctly!');
  });

  test('should show auto-approval toast on expense submission', async ({ page }) => {
    // Login and navigate to expense form
    await page.goto('http://localhost:5173');
    // ... login steps ...

    // Submit matching expense
    await page.click('button:has-text("Submit Expense")');
    await page.fill('input[name="amount"]', '55.00');
    await page.fill('input[name="vendor"]', 'Amazon');
    await page.selectOption('select[name="category"]', 'OFFICE_SUPPLIES');
    await page.click('button:has-text("Submit")');

    // Verify toast message
    await expect(page.locator('text=✨ Auto-approved by AI agent')).toBeVisible();

    console.log('✅ Auto-approval toast message displays correctly!');
  });
});
