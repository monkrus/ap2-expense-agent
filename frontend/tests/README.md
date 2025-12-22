# Automated Test Suite for Admin Dashboard

This directory contains end-to-end tests for the Admin Dashboard using Playwright.

## Quick Start

```bash
# Install dependencies (if not done)
npm install

# Install Playwright browsers
npx playwright install chromium

# Run all tests
npm test

# Run tests in UI mode (recommended for debugging)
npm run test:ui

# Run tests in headed mode (see browser)
npm run test:headed

# View test report
npm run test:report
```

## Test Structure

```
tests/
├── helpers/
│   ├── auth.js          # Authentication utilities
│   ├── wait.js          # Wait and timing helpers
│   └── dataSeeder.js    # Test data creation
├── 01-authentication.spec.js      # Login, logout, session tests
├── 02-dashboard.spec.js           # Dashboard and statistics tests
├── 03-expenses.spec.js            # Expense management tests
├── 04-user-management.spec.js     # User administration tests
└── 05-security.spec.js            # Security and permissions tests
```

## Test Credentials

### Admin User
- **Username:** `admintest`
- **Password:** `Testme1!`

### Employee User (for permission tests)
- **Username:** `emptest`
- **Password:** `EmpTest123!`

## Test Categories

### Authentication (4 tests)
- ✓ Admin login with correct credentials
- ✓ Session persistence after refresh
- ✓ Logout functionality
- ✓ Invalid credentials rejection

### Dashboard Overview (3 tests)
- Statistics cards display
- Refresh button functionality
- Pending requests section

### My Expenses (8 tests)
- View Active/History tabs
- Create new expense
- Edit existing expense
- Delete/withdraw expense
- Upload receipts
- Search expenses
- Filter by category
- Sort expenses

### User Management (6 tests)
- Access user management interface
- Create new user
- Edit user details
- Suspend/activate users
- Verify suspended user cannot login
- Verify auto-logout for suspended users

### Security & Permissions (6 tests)
- Employee cannot access admin features
- Session persistence across refreshes
- Independent sessions in different browsers
- Cannot modify own account (admin safety)
- Suspended user auto-logout
- Invalid data validation

## Test Data Seeding

Tests automatically create dummy data as needed:

```javascript
// Create a single expense
await createExpense(token, {
  amount: 125.50,
  vendor: 'Test Vendor',
  description: 'Test expense'
});

// Create multiple expenses
await createMultipleExpenses(page, 5);

// Create a user
await createUser(token, {
  email: 'test@example.com',
  username: 'testuser',
  password: 'Test123!'
});
```

## Running Specific Tests

### Run single test file
```bash
npx playwright test tests/01-authentication.spec.js
```

### Run specific test by name
```bash
npx playwright test -g "Admin Login"
```

### Run in debug mode
```bash
npx playwright test --debug
```

### Run and keep browser open on failure
```bash
npx playwright test --headed --debug
```

## Viewing Test Results

### HTML Report
```bash
npm run test:report
```

### View Screenshots
Failed tests save screenshots in `test-results/`

### View Videos
Failed tests record videos in `test-results/`

### View Traces
```bash
npx playwright show-trace test-results/path-to-trace.zip
```

## Writing New Tests

### Basic Test Structure
```javascript
import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth.js';
import { waitForLoading } from './helpers/wait.js';

test.describe('My Feature Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await waitForLoading(page);
  });

  test('Test Feature X', async ({ page }) => {
    // Your test code here
    const element = page.locator('button:has-text("Click Me")');
    await expect(element).toBeVisible();
    await element.click();
  });
});
```

### Using Test Data
```javascript
import { createExpense, getAccessToken, getUserId } from './helpers/dataSeeder.js';

test('Test with data', async ({ page }) => {
  const token = await getAccessToken(page);
  const userId = await getUserId(page);

  await createExpense(token, {
    user_id: userId,
    amount: 99.99,
    vendor: 'Test Vendor'
  });

  // Test code here
});
```

## Common Issues & Solutions

### Issue: "Element not found"
**Solution:** Use `--headed` mode to see actual UI and adjust selectors

```bash
npm run test:headed
```

### Issue: "Timeout waiting for element"
**Solution:** Increase timeout or add explicit waits

```javascript
await page.waitForSelector('button', { timeout: 10000 });
```

### Issue: "Tests fail randomly"
**Solution:** Add better wait conditions

```javascript
await page.waitForLoadState('networkidle');
await waitForLoading(page);
```

### Issue: "Cannot connect to localhost"
**Solution:** Make sure both frontend and backend are running

```bash
# Terminal 1
cd backend && .venv/Scripts/python.exe -m uvicorn src.api:app --reload

# Terminal 2
cd frontend && npm run dev
```

## Test Configuration

Configuration is in `playwright.config.js`:

- **Base URL:** `http://localhost:5173`
- **Browser:** Chromium
- **Workers:** 1 (sequential execution)
- **Retries:** 0 (increase in CI)
- **Timeout:** 30 seconds per test

## Best Practices

1. **Use Data Test IDs** instead of text selectors
   ```jsx
   <button data-testid="submit-btn">Submit</button>
   ```
   ```javascript
   await page.click('[data-testid="submit-btn"]');
   ```

2. **Wait for Loading States**
   ```javascript
   await waitForLoading(page);
   await page.waitForLoadState('networkidle');
   ```

3. **Use Page Object Model** for complex pages
   ```javascript
   class AdminDashboard {
     constructor(page) {
       this.page = page;
       this.newExpenseBtn = page.locator('[data-testid="new-expense"]');
     }

     async createExpense(data) {
       await this.newExpenseBtn.click();
       // ...
     }
   }
   ```

4. **Clean Up Test Data** after tests
   ```javascript
   test.afterEach(async ({ page }) => {
     // Delete created test data
   });
   ```

5. **Use Fixtures** for common setup
   ```javascript
   const test = base.extend({
     authenticatedPage: async ({ page }, use) => {
       await loginAsAdmin(page);
       await use(page);
     },
   });
   ```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## Troubleshooting

### Tests pass locally but fail in CI
- Add `--headed` flag to see what CI sees
- Check for timing issues
- Verify environment variables

### Flaky tests (pass sometimes, fail sometimes)
- Add more explicit waits
- Use `waitForLoadState('networkidle')`
- Avoid hard-coded delays

### Slow tests
- Run tests in parallel (increase `workers` in config)
- Use API for data setup instead of UI
- Mock external services

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Locators](https://playwright.dev/docs/locators)
- [Playwright Assertions](https://playwright.dev/docs/test-assertions)

## Support

For issues or questions:
1. Check test results in `TEST_RESULTS.md`
2. View screenshots/videos in `test-results/`
3. Run with `--debug` flag for step-by-step execution
4. Check browser console for errors

---

Last Updated: October 24, 2025
