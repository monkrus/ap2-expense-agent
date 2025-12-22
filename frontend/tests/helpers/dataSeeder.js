/**
 * Data seeding helper for creating test data
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Create a test expense via API
 * @param {string} accessToken
 * @param {object} expenseData
 */
export async function createExpense(accessToken, expenseData = {}) {
  const defaultData = {
    amount: 125.50,
    category: 'Office Supplies',
    vendor: 'Test Vendor',
    description: 'Test expense for automation',
    date: new Date().toISOString().split('T')[0],
    ...expenseData
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/expenses`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify(defaultData)
  });

  if (!response.ok) {
    throw new Error(`Failed to create expense: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Create a test user via API
 * @param {string} accessToken - Admin access token
 * @param {object} userData
 */
export async function createUser(accessToken, userData = {}) {
  const timestamp = Date.now();
  const defaultData = {
    email: `testuser${timestamp}@test.com`,
    username: `testuser${timestamp}`,
    full_name: `Test User ${timestamp}`,
    password: 'Test123!',
    role: 'employee',
    department_id: 'engineering',
    ...userData
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify(defaultData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to create user: ${error.detail || response.statusText}`);
  }

  return await response.json();
}

/**
 * Get access token from localStorage via page
 * @param {import('@playwright/test').Page} page
 */
export async function getAccessToken(page) {
  return await page.evaluate(() => localStorage.getItem('access_token'));
}

/**
 * Get user ID from localStorage
 * @param {import('@playwright/test').Page} page
 */
export async function getUserId(page) {
  const userJson = await page.evaluate(() => localStorage.getItem('user'));
  if (!userJson) return null;
  const user = JSON.parse(userJson);
  return user.id;
}

/**
 * Create multiple test expenses
 * @param {import('@playwright/test').Page} page
 * @param {number} count
 */
export async function createMultipleExpenses(page, count = 5) {
  const token = await getAccessToken(page);
  const userId = await getUserId(page);

  const categories = ['Travel', 'Meals', 'Office Supplies', 'Software', 'Other'];
  const vendors = ['Amazon', 'Staples', 'Delta Airlines', 'Restaurant', 'Software Co'];
  const expenses = [];

  for (let i = 0; i < count; i++) {
    const category = categories[i % categories.length];
    const vendor = vendors[i % vendors.length];

    const expense = await createExpense(token, {
      user_id: userId,
      amount: (Math.random() * 1000 + 10).toFixed(2),
      category,
      vendor,
      description: `Test expense ${i + 1}`,
      date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0] // Different dates
    });

    expenses.push(expense);
  }

  return expenses;
}

/**
 * Delete an expense
 * @param {string} accessToken
 * @param {string} expenseId
 */
export async function deleteExpense(accessToken, expenseId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/expenses/${expenseId}/withdraw`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  return response.ok;
}

/**
 * Approve an expense
 * @param {string} accessToken
 * @param {string} expenseId
 * @param {string} approverId
 */
export async function approveExpense(accessToken, expenseId, approverId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/expenses/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      expense_id: expenseId,
      approver_id: approverId
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to approve expense: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Reject an expense
 * @param {string} accessToken
 * @param {string} expenseId
 * @param {string} approverId
 * @param {string} reason
 */
export async function rejectExpense(accessToken, expenseId, approverId, reason = 'Test rejection') {
  const response = await fetch(`${API_BASE_URL}/api/v1/expenses/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      expense_id: expenseId,
      approver_id: approverId,
      rejection_reason: reason
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to reject expense: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Delete a user
 * @param {string} accessToken - Admin token
 * @param {string} userId
 */
export async function deleteUser(accessToken, userId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/users/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  return response.ok;
}

/**
 * Create test data setup for comprehensive testing
 * @param {import('@playwright/test').Page} page
 */
export async function seedTestData(page) {
  const token = await getAccessToken(page);
  const userId = await getUserId(page);

  // Create 5 pending expenses
  const pendingExpenses = await createMultipleExpenses(page, 5);

  // Create 2 approved expenses
  const approvedExpenses = [];
  for (let i = 0; i < 2; i++) {
    const expense = await createExpense(token, {
      user_id: userId,
      amount: (Math.random() * 500 + 50).toFixed(2),
      category: 'Travel',
      vendor: 'Approved Vendor',
      description: `Approved expense ${i + 1}`
    });

    await approveExpense(token, expense.expense.id, userId);
    approvedExpenses.push(expense);
  }

  return {
    pendingExpenses,
    approvedExpenses
  };
}
