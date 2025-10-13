# Performance Optimization Guide

Complete guide for load testing and optimizing the AP2 Expense Agent for production.

## Overview

This guide covers:
- Load testing with Locust and K6
- Database optimization
- Caching strategies
- CDN configuration
- Monitoring performance metrics

## Load Testing

### Locust Load Testing

**Setup:**
```bash
pip install locust
```

**Run basic load test:**
```bash
# Test with 10 users, spawn rate 1/sec
locust -f performance/locust-load-test.py \
  --host=https://your-domain.com \
  --users 10 \
  --spawn-rate 1
```

**Run headless (CI/CD):**
```bash
locust -f performance/locust-load-test.py \
  --host=https://your-domain.com \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --html report.html
```

**Test scenarios:**
- `ExpenseUser`: Regular employee operations (weight: 10)
- `AdminUser`: Admin operations (weight: 1)
- `BillingCronJob`: Background billing tasks (weight: 0.1)

**Expected results:**
- 95th percentile latency: < 2 seconds
- Error rate: < 5%
- Throughput: > 100 requests/second

### K6 Load Testing

**Setup:**
```bash
# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Run load test:**
```bash
# Basic test
k6 run performance/k6-load-test.js

# With custom URL
BASE_URL=https://your-domain.com k6 run performance/k6-load-test.js

# Output to InfluxDB
k6 run --out influxdb=http://localhost:8086/k6 performance/k6-load-test.js
```

**Test stages:**
1. Ramp up: 0 → 10 users (2 min)
2. Ramp up: 10 → 50 users (5 min)
3. Steady state: 100 users (10 min)
4. Spike: 200 users (5 min)
5. Recovery: 100 users (5 min)
6. Ramp down: 0 users (2 min)

**Thresholds:**
- 95th percentile < 2s
- Error rate < 5%

## Database Optimization

### Index Optimization

Add indexes for frequently queried columns:

```sql
-- Expenses table
CREATE INDEX idx_expenses_user_id ON expenses(user_id);
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_expenses_transaction_date ON expenses(transaction_date);
CREATE INDEX idx_expenses_org_id ON expenses(organization_id);
CREATE INDEX idx_expenses_created_at ON expenses(created_at DESC);

-- Composite indexes for common queries
CREATE INDEX idx_expenses_user_status ON expenses(user_id, status);
CREATE INDEX idx_expenses_org_status ON expenses(organization_id, status);

-- Audit trail
CREATE INDEX idx_audit_expense_id ON audit_trail(expense_id);
CREATE INDEX idx_audit_user_id ON audit_trail(user_id);
CREATE INDEX idx_audit_timestamp ON audit_trail(timestamp DESC);

-- Usage metrics
CREATE INDEX idx_usage_org_id ON usage_metrics(organization_id);
CREATE INDEX idx_usage_period ON usage_metrics(period_start, period_end);
CREATE INDEX idx_usage_reported ON usage_metrics(reported_to_gcp) WHERE reported_to_gcp = false;
```

### Query Optimization

**Use pagination:**
```python
# Instead of loading all records
expenses = db.query(Expense).all()

# Use pagination
expenses = db.query(Expense)\
    .offset(skip)\
    .limit(limit)\
    .all()
```

**Use select_related/joinedload:**
```python
# Instead of N+1 queries
expenses = db.query(Expense).all()
for expense in expenses:
    print(expense.user.name)  # N+1 query

# Use eager loading
from sqlalchemy.orm import joinedload
expenses = db.query(Expense)\
    .options(joinedload(Expense.user))\
    .all()
```

**Filter before join:**
```python
# Filter early to reduce join size
expenses = db.query(Expense)\
    .filter(Expense.status == 'pending')\
    .join(User)\
    .filter(User.organization_id == org_id)\
    .all()
```

### Connection Pooling

Configure SQLAlchemy connection pool:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Number of connections to maintain
    max_overflow=10,        # Max additional connections
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle connections every hour
    echo_pool=True          # Log pool events
)
```

## Caching Strategies

### Redis Setup

Add Redis to Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: ap2-expense
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: ap2-expense
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### Application Caching

**Install Redis client:**
```bash
pip install redis
```

**Configure caching in FastAPI:**
```python
import redis
from functools import wraps
import json

redis_client = redis.Redis(
    host='redis-service',
    port=6379,
    decode_responses=True
)

def cache(expire: int = 300):
    """Cache decorator with expiration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(key, expire, json.dumps(result))

            return result
        return wrapper
    return decorator

# Usage
@app.get("/api/v1/expenses/report")
@cache(expire=600)  # Cache for 10 minutes
async def get_expense_report():
    # Expensive database query
    pass
```

**Cache invalidation:**
```python
def invalidate_cache(pattern: str):
    """Invalidate cache by pattern"""
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)

# Invalidate when data changes
@app.post("/api/v1/expenses/")
async def create_expense(expense: ExpenseCreate):
    result = create_expense_in_db(expense)

    # Invalidate relevant caches
    invalidate_cache(f"get_expense_report:*")
    invalidate_cache(f"get_expenses:*")

    return result
```

## CDN Configuration

Cloud CDN is already configured in `k8s/ingress.yaml`:

```yaml
metadata:
  annotations:
    cloud.google.com/cdn-enabled: "true"
```

**Configure cache headers:**

```python
from fastapi import Response

@app.get("/api/v1/expenses/report")
async def get_expense_report(response: Response):
    # Set cache headers
    response.headers["Cache-Control"] = "public, max-age=600"  # 10 minutes
    response.headers["ETag"] = generate_etag(data)

    return data
```

**Static file caching (nginx):**

```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Database Optimization

### Enable Query Analysis

```sql
-- Enable query logging
ALTER DATABASE ap2_expense SET log_statement = 'all';
ALTER DATABASE ap2_expense SET log_duration = on;
ALTER DATABASE ap2_expense SET log_min_duration_statement = 1000;  -- Log queries > 1s

-- Analyze queries
EXPLAIN ANALYZE SELECT * FROM expenses WHERE user_id = 'xxx' AND status = 'pending';
```

### Vacuum and Analyze

```sql
-- Schedule regular maintenance
VACUUM ANALYZE expenses;
VACUUM ANALYZE audit_trail;
VACUUM ANALYZE usage_metrics;

-- Or enable autovacuum (usually default)
ALTER TABLE expenses SET (autovacuum_enabled = true);
```

### Partitioning Large Tables

For audit_trail (grows quickly):

```sql
-- Convert to partitioned table
CREATE TABLE audit_trail_partitioned (
    LIKE audit_trail INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE audit_trail_2025_10 PARTITION OF audit_trail_partitioned
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE audit_trail_2025_11 PARTITION OF audit_trail_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

## Backend Optimization

### Async Operations

Use async for I/O-bound operations:

```python
import asyncio
from fastapi import BackgroundTasks

@app.post("/api/v1/expenses/")
async def create_expense(expense: ExpenseCreate, background_tasks: BackgroundTasks):
    # Synchronous DB write
    result = create_expense_in_db(expense)

    # Async notifications
    background_tasks.add_task(send_notification, result.id)
    background_tasks.add_task(update_analytics, result.id)

    return result
```

### Request Batching

Batch multiple operations:

```python
@app.post("/api/v1/expenses/batch")
async def create_expenses_batch(expenses: List[ExpenseCreate]):
    # Bulk insert
    db.bulk_insert_mappings(Expense, [e.dict() for e in expenses])
    db.commit()

    return {"success": True, "count": len(expenses)}
```

### Response Compression

Enable gzip compression:

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## Monitoring Performance

### Application Metrics

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request
import time

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

### Database Monitoring

Monitor slow queries:

```sql
-- Install pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Performance Targets

Target performance metrics for production:

| Metric | Target | Acceptable | Critical |
|--------|--------|-----------|----------|
| API Response Time (p95) | < 500ms | < 2s | > 5s |
| API Response Time (p99) | < 2s | < 5s | > 10s |
| Database Query Time | < 100ms | < 500ms | > 1s |
| Error Rate | < 0.1% | < 1% | > 5% |
| Throughput | > 1000 req/s | > 500 req/s | < 100 req/s |
| CPU Usage | < 50% | < 70% | > 90% |
| Memory Usage | < 70% | < 85% | > 95% |

## Load Test Schedule

Run load tests regularly:

1. **Daily**: Smoke test (10 users, 5 min)
2. **Weekly**: Standard load test (100 users, 30 min)
3. **Monthly**: Stress test (500 users, 1 hour)
4. **Pre-release**: Soak test (200 users, 4 hours)

## Troubleshooting

### High Response Times

1. Check database indexes
2. Analyze slow queries
3. Check connection pool size
4. Review cache hit rate
5. Check external API calls

### High Memory Usage

1. Check for memory leaks
2. Review connection pool settings
3. Optimize query result sizes
4. Enable pagination
5. Monitor background tasks

### High CPU Usage

1. Optimize expensive queries
2. Review N+1 query patterns
3. Check for infinite loops
4. Profile CPU usage
5. Scale horizontally

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [K6 Documentation](https://k6.io/docs/)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/concepts/)
