// K6 load testing script for AP2 Expense Agent
// Usage: k6 run k6-load-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Ramp up to 50 users
    { duration: '10m', target: 100 }, // Stay at 100 users
    { duration: '5m', target: 200 },  // Spike to 200 users
    { duration: '5m', target: 100 },  // Drop back to 100
    { duration: '2m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.05'],    // Error rate under 5%
    errors: ['rate<0.05'],             // Custom error rate under 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://your-domain.com';

// Setup: Create test users
export function setup() {
  const users = [];

  for (let i = 0; i < 10; i++) {
    const username = `k6test_${Date.now()}_${i}@example.com`;
    const password = 'Test123!@#';

    const registerRes = http.post(`${BASE_URL}/api/v1/users/register`, JSON.stringify({
      username: username,
      email: username,
      password: password,
      full_name: `K6 Test User ${i}`,
      organization_name: 'K6 Test Org'
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

    if (registerRes.status === 200 || registerRes.status === 409) {
      // Login
      const loginRes = http.post(`${BASE_URL}/api/v1/users/login`, JSON.stringify({
        username: username,
        password: password
      }), {
        headers: { 'Content-Type': 'application/json' },
      });

      if (loginRes.status === 200) {
        const token = loginRes.json('access_token');
        users.push({ username, token });
      }
    }
  }

  return { users };
}

// Main test scenario
export default function (data) {
  // Select random user
  const user = data.users[Math.floor(Math.random() * data.users.length)];
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${user.token}`
  };

  // Test 1: Health check
  {
    const res = http.get(`${BASE_URL}/health`);
    check(res, {
      'health check status is 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  }

  sleep(1);

  // Test 2: View expenses
  {
    const res = http.get(`${BASE_URL}/api/v1/expenses/`, { headers });
    check(res, {
      'view expenses status is 200': (r) => r.status === 200,
      'view expenses response time < 1s': (r) => r.timings.duration < 1000,
    }) || errorRate.add(1);
  }

  sleep(1);

  // Test 3: Create expense
  {
    const expense = {
      amount: Math.random() * 500,
      currency: 'USD',
      description: `K6 test expense ${Date.now()}`,
      category: ['travel', 'meals', 'supplies'][Math.floor(Math.random() * 3)],
      merchant: `Test Merchant ${Math.floor(Math.random() * 100)}`,
      transaction_date: new Date().toISOString()
    };

    const res = http.post(`${BASE_URL}/api/v1/expenses/`, JSON.stringify(expense), { headers });
    check(res, {
      'create expense status is 200': (r) => r.status === 200,
      'create expense response time < 2s': (r) => r.timings.duration < 2000,
    }) || errorRate.add(1);
  }

  sleep(2);

  // Test 4: View report
  {
    const res = http.get(`${BASE_URL}/api/v1/expenses/report`, { headers });
    check(res, {
      'view report status is 200': (r) => r.status === 200,
      'view report response time < 3s': (r) => r.timings.duration < 3000,
    }) || errorRate.add(1);
  }

  sleep(2);

  // Test 5: View audit trail
  {
    const res = http.get(`${BASE_URL}/api/v1/audit/`, { headers });
    check(res, {
      'view audit status is 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  }

  sleep(1);
}

// Teardown: Cleanup
export function teardown(data) {
  console.log('Load test completed');
  console.log(`Total users created: ${data.users.length}`);
}
