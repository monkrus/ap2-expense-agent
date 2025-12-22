import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

const failureRate = new Rate('failed_requests');
const memoryLeaks = new Counter('potential_memory_leaks');

// Soak test configuration - runs for extended period
export const options = {
  stages: [
    { duration: '5m', target: 50 },     // Ramp up
    { duration: '6h', target: 50 },     // Soak for 6 hours
    { duration: '5m', target: 0 },      // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<500'],
    'failed_requests': ['rate<0.01'],
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

let consecutiveFailures = 0;

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  const healthSuccess = check(healthRes, {
    'health check passed': (r) => r.status === 200,
  });

  if (!healthSuccess) {
    consecutiveFailures++;
    if (consecutiveFailures > 10) {
      memoryLeaks.add(1);
      console.error('Potential memory leak or service degradation detected');
    }
  } else {
    consecutiveFailures = 0;
  }

  // Login
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ username: 'emptest', password: 'Testme1!' }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  const loginSuccess = check(loginRes, {
    'login successful': (r) => r.status === 200,
    'response time acceptable': (r) => r.timings.duration < 1000,
  });

  failureRate.add(!loginSuccess);

  if (loginSuccess) {
    const token = loginRes.json('access_token');

    // Get expense report
    const reportRes = http.get(`${BASE_URL}/api/v1/expenses/report`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    check(reportRes, {
      'report retrieved': (r) => r.status === 200,
    });
  }

  sleep(Math.random() * 5 + 2);  // Sleep 2-7 seconds
}

export function setup() {
  console.log('Starting soak test - 6 hour endurance test...');
  console.log('This test will detect memory leaks and performance degradation');
}

export function teardown() {
  console.log('Soak test completed');
  console.log(`Potential memory leak indicators: ${memoryLeaks.value}`);
}
