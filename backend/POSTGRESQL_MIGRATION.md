# PostgreSQL Migration Guide

## Overview
This guide covers migrating from SQLite (testing) to PostgreSQL (production) for the AP2 Expense Agent.

## Prerequisites
- PostgreSQL 14+ installed
- Python 3.11+
- Access to Google Cloud SQL (for production)

---

## Step 1: Local PostgreSQL Setup

### Option A: Docker (Recommended for Testing)

Create `docker-compose.yml` in the backend directory:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ap2user
      POSTGRES_PASSWORD: changeme
      POSTGRES_DB: expenses
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ap2user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
```

Start PostgreSQL:
```bash
docker-compose up -d postgres
```

### Option B: Local Installation

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
createuser -s ap2user
createdb -O ap2user expenses
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql-15
sudo -u postgres createuser -s ap2user
sudo -u postgres createdb -O ap2user expenses
```

Set password:
```bash
psql -U postgres
ALTER USER ap2user PASSWORD 'changeme';
\q
```

---

## Step 2: Update Environment Configuration

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses

# Or for Cloud SQL (production):
# DATABASE_URL=postgresql://ap2user:PASSWORD@/expenses?host=/cloudsql/PROJECT:REGION:INSTANCE

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=GENERATE_STRONG_KEY_HERE  # openssl rand -hex 32

# Stripe
STRIPE_SECRET_KEY=sk_test_...  # Use test key initially
STRIPE_PUBLISHABLE_KEY=pk_test_...

# GCP
GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_KEY=/path/to/service-account-key.json

# Application
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## Step 3: Create Migration for Recent Changes

Generate migration for nullable max_users:

```bash
cd /home/user/ap2-expense-agent/backend

# Generate new migration
alembic revision --autogenerate -m "make_subscription_limits_nullable"
```

This will create a new migration file. Review it to ensure it includes:
- Making `max_users` nullable in `subscriptions` table
- Any other recent model changes

---

## Step 4: Run Migrations

```bash
# Check current migration status
alembic current

# View pending migrations
alembic heads

# Run all pending migrations
alembic upgrade head

# Verify migration success
alembic current
```

---

## Step 5: Verify Database Schema

Connect to PostgreSQL:
```bash
psql -U ap2user -d expenses
```

Verify tables:
```sql
-- List all tables
\dt

-- Check subscriptions table structure
\d subscriptions

-- Verify max_users is nullable
SELECT column_name, is_nullable, data_type
FROM information_schema.columns
WHERE table_name = 'subscriptions'
  AND column_name = 'max_users';

-- Should show: max_users | YES | integer
```

---

## Step 6: Test with PostgreSQL

Update your `.env` to use PostgreSQL:
```bash
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
```

Run tests:
```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/test_subscription_service.py -v
pytest tests/test_tenant_isolation.py -v
pytest tests/test_expenses.py -v
```

Expected result: **268/278 tests passing** (same as SQLite)

---

## Step 7: Production Setup (Google Cloud SQL)

### Create Cloud SQL Instance

```bash
# Set variables
PROJECT_ID=your-project-id
REGION=us-central1
INSTANCE_NAME=ap2-expense-db

# Create PostgreSQL instance
gcloud sql instances create $INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-7680 \
  --region=$REGION \
  --network=default \
  --no-assign-ip \
  --enable-bin-log \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04

# Create database
gcloud sql databases create expenses \
  --instance=$INSTANCE_NAME

# Create user
gcloud sql users create ap2user \
  --instance=$INSTANCE_NAME \
  --password=STRONG_RANDOM_PASSWORD

# Get connection name (for Cloud Run)
gcloud sql instances describe $INSTANCE_NAME \
  --format="value(connectionName)"
```

### Configure Cloud Run to Connect

In Cloud Run deployment, set:
```bash
DATABASE_URL=postgresql://ap2user:PASSWORD@/expenses?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Enable Cloud SQL Admin API and add the Cloud SQL connection in Cloud Run settings.

---

## Step 8: Data Migration (if needed)

If you have existing SQLite data to migrate:

```python
# create_migration_script.py
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# Connect to both databases
sqlite_conn = sqlite3.connect('expenses.db')
pg_conn = psycopg2.connect('postgresql://ap2user:changeme@localhost/expenses')

# Get all table names
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in sqlite_cursor.fetchall()]

# Migrate each table
for table in tables:
    if table.startswith('alembic'):
        continue

    print(f"Migrating {table}...")

    # Get data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()

    if not rows:
        continue

    # Get column names
    column_names = [desc[0] for desc in sqlite_cursor.description]

    # Insert into PostgreSQL
    pg_cursor = pg_conn.cursor()
    insert_query = f"INSERT INTO {table} ({','.join(column_names)}) VALUES %s"
    execute_values(pg_cursor, insert_query, rows)
    pg_conn.commit()

    print(f"  Migrated {len(rows)} rows")

pg_conn.close()
sqlite_conn.close()
```

---

## Step 9: Performance Tuning

### Create Indexes

```sql
-- Indexes for frequent queries
CREATE INDEX CONCURRENTLY idx_expenses_org_status
  ON expenses(organization_id, status);

CREATE INDEX CONCURRENTLY idx_expenses_user_date
  ON expenses(user_id, date DESC);

CREATE INDEX CONCURRENTLY idx_usage_records_subscription_date
  ON usage_records(subscription_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_audit_logs_resource
  ON audit_logs(resource_type, resource_id);

-- Partial indexes for active records
CREATE INDEX CONCURRENTLY idx_active_subscriptions
  ON subscriptions(user_id)
  WHERE status IN ('active', 'trialing');

CREATE INDEX CONCURRENTLY idx_pending_expenses
  ON expenses(organization_id, created_at DESC)
  WHERE status = 'pending';
```

### Connection Pooling

Update `database.py`:

```python
from sqlalchemy.pool import NullPool, QueuePool

# For production
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=settings.debug
)
```

---

## Step 10: Monitoring

### Enable Query Logging (Development Only)

```sql
ALTER DATABASE expenses SET log_statement = 'all';
ALTER DATABASE expenses SET log_duration = 'on';
```

### Check Slow Queries

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT
  query,
  calls,
  total_time / 1000 as total_seconds,
  mean_time / 1000 as mean_seconds,
  max_time / 1000 as max_seconds
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_time DESC
LIMIT 20;
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql -U ap2user -d expenses -h localhost

# Check PostgreSQL is running
docker-compose ps  # If using Docker
# or
pg_isadmin -U ap2user  # If local install
```

### Migration Errors

```bash
# Rollback last migration
alembic downgrade -1

# Show migration history
alembic history

# Check current version
alembic current
```

### CASCADE Deletion Issues

The nullable max_users fix and explicit OrganizationMember deletion already handles this:

```python
# In routes/users.py - already implemented
db.query(OrganizationMember).filter(
    OrganizationMember.user_id == user_id
).delete(synchronize_session=False)
```

---

## Success Criteria

✅ PostgreSQL instance running
✅ All migrations applied successfully
✅ 268/278 tests passing (same as SQLite)
✅ Connection pooling configured
✅ Indexes created for performance
✅ Cloud SQL instance provisioned (production)
✅ Backups configured

---

## Next Steps

After PostgreSQL migration:
1. ✅ GCP Marketplace Integration Testing
2. ✅ Deploy to Cloud Run
3. ✅ Configure production secrets
4. ✅ Performance testing under load
5. ✅ Beta launch

---

## Rollback Plan

If issues occur:

```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Switch back to SQLite temporarily
DATABASE_URL=sqlite:///./expenses.db
```
