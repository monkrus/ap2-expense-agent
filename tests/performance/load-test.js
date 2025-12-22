import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const failureRate = new Rate('failed_requests');
const loginDuration = new Trend('login_duration');
const expenseSubmissionDuration = new Trend('expense_submission_duration');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],  // 95% of requests under 500ms
    'failed_requests': ['rate<0.01'],     // Less than 1% failures
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data
const TEST_USERS = [
  { username: 'emptest', password: 'Testme1!' },
  { username: 'admintest', password: 'Testme1!' },
  { username: 'testuser', password: 'Testme1!' },
];

/**
 * Login and get access token
 */
function login(username, password) {
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ username, password }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { name: 'Login' },
    }
  );

  const success = check(loginRes, {
    'login successful': (r) => r.status === 200,
    'access token received': (r) => r.json('access_token') !== undefined,
  });

  failureRate.add(!success);
  loginDuration.add(loginRes.timings.duration);

  if (success) {
    return loginRes.json('access_token');
  }
  return null;
}

/**
 * Submit expense
 */
function submitExpense(token) {
  const expense = {
    user_id: 'test-user-id',
    amount: Math.random() * 500 + 50,  // Random amount between $50-$550
    vendor: `Vendor ${Math.floor(Math.random() * 100)}`,
    category: ['Travel', 'Meals', 'Software', 'Office Supplies', 'Other'][
      Math.floor(Math.random() * 5)
    ],
    description: `Test expense ${Date.now()}`,
    date: new Date().toISOString(),
  };

  const res = http.post(
    `${BASE_URL}/api/v1/expenses`,
    JSON.stringify(expense),
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      tags: { name: 'SubmitExpense' },
    }
  );

  const success = check(res, {
    'expense submitted': (r) => r.status === 201 || r.status === 200,
  });

  failureRate.add(!success);
  expenseSubmissionDuration.add(res.timings.duration);

  return success;
}

/**
 * Get expense report
 */
function getExpenseReport(token) {
  const res = http.get(`${BASE_URL}/api/v1/expenses/report`, {
    headers: { Authorization: `Bearer ${token}` },
    tags: { name: 'GetReport' },
  });

  const success = check(res, {
    'report retrieved': (r) => r.status === 200,
  });

  failureRate.add(!success);
  return success;
}

/**
 * Get pending expenses (admin/manager)
 */
function getPendingExpenses(token) {
  const res = http.get(`${BASE_URL}/api/v1/expenses/all-pending`, {
    headers: { Authorization: `Bearer ${token}` },
    tags: { name: 'GetPending' },
  });

  const success = check(res, {
    'pending expenses retrieved': (r) => r.status === 200,
  });

  failureRate.add(!success);
  return success;
}

/**
 * Health check
 */
function healthCheck() {
  const res = http.get(`${BASE_URL}/health`, {
    tags: { name: 'HealthCheck' },
  });

  const success = check(res, {
    'health check passed': (r) => r.status === 200,
    'service healthy': (r) => r.json('status') === 'healthy',
  });

  failureRate.add(!success);
  return success;
}

/**
 * Main test scenario
 */
export default function () {
  // Health check
  group('Health Check', () => {
    healthCheck();
  });

  sleep(1);

  // Select random test user
  const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];

  // Login
  let token;
  group('Authentication', () => {
    token = login(user.username, user.password);
  });

  if (!token) {
    console.error(`Failed to login as ${user.username}`);
    return;
  }

  sleep(1);

  // Submit expense (70% of users)
  if (Math.random() < 0.7) {
    group('Submit Expense', () => {
      submitExpense(token);
    });
    sleep(2);
  }

  // Get expense report (50% of users)
  if (Math.random() < 0.5) {
    group('View Report', () => {
      getExpenseReport(token);
    });
    sleep(1);
  }

  // Get pending expenses (30% of users - simulating managers/admins)
  if (Math.random() < 0.3) {
    group('View Pending', () => {
      getPendingExpenses(token);
    });
    sleep(1);
  }

  sleep(Math.random() * 3 + 1);  // Random sleep 1-4 seconds
}

/**
 * Setup function (runs once)
 */
export function setup() {
  console.log('Starting load test...');
  console.log(`Base URL: ${BASE_URL}`);

  // Verify API is accessible
  const healthRes = http.get(`${BASE_URL}/health`);
  if (healthRes.status !== 200) {
    throw new Error(`API not accessible: ${healthRes.status}`);
  }

  console.log('API health check passed');
}

/**
 * Teardown function (runs once)
 */
export function teardown(data) {
  console.log('Load test completed');
}
