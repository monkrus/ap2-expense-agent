# Performance Testing Guide

This directory contains performance and load testing for the AP2 Expense Agent API using Locust.

## Prerequisites

```bash
pip install locust
```

## Running Performance Tests

### Basic Load Test

Test with 10 concurrent users, spawning 2 users per second:

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2
```

### Web UI Mode

Run with web interface for real-time monitoring:

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser.

### Headless Mode

Run without web UI (useful for CI/CD):

```bash
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html reports/load_test_report.html
```

## Test Scenarios

### 1. Normal Load Test
Simulates realistic user behavior with normal traffic patterns:
```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 10m
```

**Expected Results:**
- Response time (95th percentile): < 500ms
- Error rate: < 1%
- Requests per second: > 100

### 2. Spike Test
Tests system behavior under sudden traffic spike:
```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 200 --spawn-rate 50 --run-time 5m
```

**Expected Results:**
- System should handle spike gracefully
- Auto-scaling should trigger
- No data loss or corruption

### 3. Soak Test (Endurance)
Long-running test to identify memory leaks and stability issues:
```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 30 --spawn-rate 2 --run-time 2h
```

**Expected Results:**
- Consistent performance over time
- No memory leaks
- Stable resource utilization

### 4. Stress Test
Push system beyond normal capacity to find breaking point:
```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 500 --spawn-rate 25 --run-time 15m
```

**Expected Results:**
- Identify maximum capacity
- Graceful degradation
- System recovery after load reduction

## User Types

The test suite includes different user behavior patterns:

### WebsiteUser (weight: 1)
- Realistic user behavior
- Wait time: 1-5 seconds between actions
- Balanced read/write operations

### BurstUser (weight: 1)
- Aggressive traffic patterns
- Wait time: 0.1-1 seconds
- Simulates API-heavy clients

### ReportViewerUser (weight: 2)
- Read-heavy operations
- Wait time: 2-8 seconds
- Primarily views dashboards and reports

### SpikeTestUser (weight: 1)
- Very aggressive requests
- Wait time: 0.1-0.5 seconds
- Tests extreme load conditions

### SoakTestUser (weight: 1)
- Slow and steady requests
- Wait time: 5-15 seconds
- Long-term stability testing

## Task Distribution

Tasks are weighted by frequency:

| Task | Weight | Description |
|------|--------|-------------|
| List Expenses | 15 | Most frequent operation |
| Create Expense | 10 | Common write operation |
| Search Expenses | 5 | Filtered queries |
| Get Expense Detail | 5 | Individual record access |
| Update Expense | 3 | Modification operations |
| Get Organization Members | 2 | Organization queries |
| Health Check | 1 | Monitoring |
| Metrics Check | 1 | Observability |

## Performance Benchmarks

### API Response Times

| Endpoint | Target (p95) | Acceptable (p95) |
|----------|--------------|------------------|
| GET /api/v1/expenses | < 200ms | < 500ms |
| POST /api/v1/expenses | < 300ms | < 800ms |
| GET /api/v1/expenses/{id} | < 100ms | < 300ms |
| PATCH /api/v1/expenses/{id} | < 250ms | < 600ms |
| GET /api/v1/organizations/{id}/members | < 150ms | < 400ms |
| POST /api/v1/auth/login | < 200ms | < 500ms |
| GET /health | < 50ms | < 100ms |

### Throughput Targets

- **Normal Load**: 100-200 requests/second
- **Peak Load**: 500-1000 requests/second
- **Maximum Sustainable**: 300 requests/second

### Resource Utilization

- **CPU**: < 70% under normal load
- **Memory**: < 2GB per instance
- **Database Connections**: < 50 active connections
- **Redis Operations**: > 10,000 ops/second

## Monitoring During Tests

### Prometheus Metrics
```bash
# View metrics during test
curl http://localhost:8000/metrics
```

Key metrics to monitor:
- `http_requests_total` - Total request count
- `http_request_duration_seconds` - Response time distribution
- `http_requests_in_progress` - Concurrent requests
- `db_query_duration_seconds` - Database performance
- `cache_hits_total` / `cache_misses_total` - Cache effectiveness

### Health Endpoint
```bash
curl http://localhost:8000/health
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run performance tests
  run: |
    locust -f backend/tests/performance/locustfile.py \
      --host=http://localhost:8000 \
      --users 50 \
      --spawn-rate 5 \
      --run-time 5m \
      --headless \
      --html reports/performance_report.html \
      --csv reports/performance
```

## Analyzing Results

### Locust generates several report files:

1. **HTML Report** (`--html`): Visual report with charts
2. **CSV Reports** (`--csv`): Raw data for analysis
   - `*_stats.csv` - Request statistics
   - `*_stats_history.csv` - Time-series data
   - `*_failures.csv` - Failed requests

### Key Metrics to Analyze

1. **Response Time Distribution**
   - 50th percentile (median)
   - 95th percentile (p95)
   - 99th percentile (p99)
   - Maximum response time

2. **Throughput**
   - Requests per second (RPS)
   - Failed requests per second

3. **Error Rate**
   - Percentage of failed requests
   - Types of errors

4. **Resource Utilization**
   - CPU usage
   - Memory consumption
   - Database connection pool
   - Cache hit ratio

## Troubleshooting

### High Response Times
- Check database query performance
- Verify cache is working
- Review slow query logs
- Check for N+1 queries

### High Error Rates
- Check application logs
- Verify database connections
- Check rate limiting
- Review error tracking (Sentry)

### Resource Exhaustion
- Scale up instances
- Optimize queries
- Increase cache TTL
- Review database indexes

## Best Practices

1. **Start Small**: Begin with low user counts and gradually increase
2. **Monitor Everything**: Watch metrics, logs, and resources during tests
3. **Test in Isolation**: Run performance tests on dedicated environments
4. **Baseline First**: Establish baseline performance before changes
5. **Test Regularly**: Run performance tests in CI/CD pipeline
6. **Document Results**: Keep records of test results for comparison

## Example Commands

### Quick Smoke Test
```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 5 --spawn-rate 1 --run-time 2m --headless
```

### Production-Like Load
```bash
locust -f locustfile.py --host=https://api.example.com \
  --users 100 --spawn-rate 10 --run-time 30m \
  --headless --html prod_load_test.html
```

### Capacity Planning
```bash
# Gradually increase load to find breaking point
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 20 --run-time 20m
```
