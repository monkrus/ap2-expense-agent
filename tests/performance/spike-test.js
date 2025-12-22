import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const failureRate = new Rate('failed_requests');

// Spike test configuration
export const options = {
  stages: [
    { duration: '1m', target: 50 },    // Ramp up to baseline
    { duration: '30s', target: 500 },  // Spike to 10x load
    { duration: '1m', target: 500 },   // Stay at spike
    { duration: '30s', target: 50 },   // Drop back to baseline
    { duration: '1m', target: 50 },    // Recover
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],  // More lenient during spike
    'failed_requests': ['rate<0.05'],      // Allow up to 5% failures
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check passed': (r) => r.status === 200,
  });

  // Login
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ username: 'adminfree', password: 'Testme1!' }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  const success = check(loginRes, {
    'login successful': (r) => r.status === 200,
  });

  failureRate.add(!success);

  sleep(Math.random() * 2);
}

export function setup() {
  console.log('Starting spike test - simulating sudden traffic surge...');
}

export function teardown() {
  console.log('Spike test completed');
}
