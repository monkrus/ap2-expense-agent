# Database Migration Guide: SQLite to PostgreSQL

This guide explains how to migrate from SQLite (development) to PostgreSQL (production).

## Current Status

The application is **already configured** to support PostgreSQL! The default `database_url` in `config.py` is:
```
postgresql://ap2user:changeme@localhost:5432/expenses
```

## Quick Start

### Option 1: Use Environment Variable (Recommended)

Create a `.env` file in the `backend` directory:

```bash
# For SQLite (Development/Testing)
DATABASE_URL=sqlite:///./test.db

# For PostgreSQL (Production)
DATABASE_URL=postgresql://username:password@host:port/database

# For Google Cloud SQL (Production)
DATABASE_URL=postgresql://username:password@/database?host=/cloudsql/PROJECT:REGION:INSTANCE
```

### Option 2: Modify config.py

Edit `backend/src/config.py`:

```python
database_url: str = "sqlite:///./test.db"  # For development
# database_url: str = "postgresql://ap2user:changeme@localhost:5432/expenses"  # For production
```

## PostgreSQL Setup

### Local PostgreSQL Installation

#### Windows
```powershell
# Install PostgreSQL using winget
winget install PostgreSQL.PostgreSQL

# Or using Chocolatey
choco install postgresql

# Start PostgreSQL service
net start postgresql-x64-14
```

#### Create Database and User

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE expenses;

-- Create user
CREATE USER ap2user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;

-- Exit
\q
```

### Google Cloud SQL Setup

#### 1. Create Cloud SQL Instance

```bash
gcloud sql instances create ap2-expense-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=your_secure_password \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00
```

#### 2. Create Database

```bash
gcloud sql databases create expenses --instance=ap2-expense-db
```

#### 3. Create User

```bash
gcloud sql users create ap2user \
    --instance=ap2-expense-db \
    --password=your_secure_password
```

#### 4. Connection String

**For Cloud Run (recommended):**
```
DATABASE_URL=postgresql://ap2user:password@/expenses?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

**For external connection (development):**
```
DATABASE_URL=postgresql://ap2user:password@PUBLIC_IP:5432/expenses
```

## Database Migration Process

### Step 1: Install Dependencies

The application already has the required dependencies. Verify in `requirements.txt`:

```txt
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0  # PostgreSQL driver
alembic>=1.12.0         # For migrations (optional)
```

Install if needed:
```bash
cd backend
pip install psycopg2-binary
```

### Step 2: Export Data from SQLite (Optional)

If you have existing data in SQLite that you want to migrate:

```python
# Create a migration script: backend/migrate_data.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, User, Expense, Organization  # Import all models

# Source (SQLite)
sqlite_engine = create_engine('sqlite:///./test.db')
SqliteSession = sessionmaker(bind=sqlite_engine)

# Destination (PostgreSQL)
postgres_engine = create_engine('postgresql://ap2user:password@localhost:5432/expenses')
PostgresSession = sessionmaker(bind=postgres_engine)

# Create tables in PostgreSQL
Base.metadata.create_all(postgres_engine)

# Migrate data
sqlite_session = SqliteSession()
postgres_session = PostgresSession()

try:
    # Migrate users
    users = sqlite_session.query(User).all()
    for user in users:
        postgres_session.merge(user)

    # Migrate organizations
    orgs = sqlite_session.query(Organization).all()
    for org in orgs:
        postgres_session.merge(org)

    # Migrate expenses
    expenses = sqlite_session.query(Expense).all()
    for expense in expenses:
        postgres_session.merge(expense)

    postgres_session.commit()
    print("Migration completed successfully!")

except Exception as e:
    postgres_session.rollback()
    print(f"Migration failed: {e}")
finally:
    sqlite_session.close()
    postgres_session.close()
```

Run the migration:
```bash
cd backend
python migrate_data.py
```

### Step 3: Update Environment Configuration

Update `.env` file:

```bash
# Database
DATABASE_URL=postgresql://ap2user:your_secure_password@localhost:5432/expenses

# For Cloud SQL
# DATABASE_URL=postgresql://ap2user:password@/expenses?host=/cloudsql/PROJECT:REGION:INSTANCE

# Environment
ENVIRONMENT=production
DEBUG=False

# JWT Secret (CHANGE THIS!)
JWT_SECRET=your-random-secret-key-here

# CORS (Update with your production domains)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### Step 4: Initialize Database

The application will automatically create tables on startup:

```bash
cd backend
python -m uvicorn src.api:app --reload
```

Or manually:
```python
from src.database import init_db
init_db()
```

### Step 5: Verify Connection

```bash
# Test database connection
python -c "from src.database import engine; print(engine.execute('SELECT 1').scalar())"
```

## Using Alembic for Migrations (Optional but Recommended)

Alembic provides version control for your database schema.

### Initialize Alembic

```bash
cd backend
alembic init alembic
```

### Configure Alembic

Edit `alembic/env.py`:

```python
from src.config import settings
from src.models import Base

config.set_main_option('sqlalchemy.url', settings.database_url)
target_metadata = Base.metadata
```

### Create Initial Migration

```bash
alembic revision --autogenerate -m "Initial migration"
```

### Apply Migration

```bash
alembic upgrade head
```

### Future Schema Changes

```bash
# After modifying models
alembic revision --autogenerate -m "Add new field to User model"
alembic upgrade head
```

## Performance Optimization for PostgreSQL

### 1. Add Indexes

Key indexes are already defined in the models, but you can add more:

```sql
-- Index for faster user lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Index for expense queries
CREATE INDEX idx_expenses_status ON expenses(status);
CREATE INDEX idx_expenses_user_id ON expenses(user_id);
CREATE INDEX idx_expenses_created_at ON expenses(created_at DESC);

-- Composite indexes for common queries
CREATE INDEX idx_expenses_user_status ON expenses(user_id, status);
CREATE INDEX idx_expenses_org_status ON expenses(organization_id, status);
```

### 2. Connection Pooling

Already configured in `database.py`:

```python
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,           # Adjust based on load
    max_overflow=10,       # Max additional connections
    pool_pre_ping=True,    # Test connections before use
    pool_recycle=3600      # Recycle after 1 hour
)
```

Adjust in `config.py` or `.env`:
```bash
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800
```

### 3. Query Optimization

- Use `joinedload()` for relationships
- Add `limit()` to queries
- Use `select()` instead of loading full objects when possible

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
# Windows
sc query postgresql-x64-14

# Start service
net start postgresql-x64-14
```

### Authentication Failed

```bash
# Update pg_hba.conf
# Location: C:\Program Files\PostgreSQL\14\data\pg_hba.conf

# Add line:
host    all             all             127.0.0.1/32            md5

# Restart PostgreSQL
net stop postgresql-x64-14
net start postgresql-x64-14
```

### Cloud SQL Connection Issues

```bash
# Install Cloud SQL Proxy
gcloud components install cloud-sql-proxy

# Run proxy
cloud-sql-proxy PROJECT:REGION:INSTANCE

# Test connection
psql "host=127.0.0.1 port=5432 sslmode=disable dbname=expenses user=ap2user"
```

### Permission Denied

```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ap2user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ap2user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ap2user;
```

## Database Backup

### PostgreSQL Backup

```bash
# Backup
pg_dump -h localhost -U ap2user expenses > backup.sql

# Restore
psql -h localhost -U ap2user expenses < backup.sql
```

### Cloud SQL Backup

```bash
# Create backup
gcloud sql backups create --instance=ap2-expense-db

# List backups
gcloud sql backups list --instance=ap2-expense-db

# Restore
gcloud sql backups restore BACKUP_ID --backup-instance=ap2-expense-db
```

## Monitoring

### Connection Pool Stats

```python
from src.database import engine

# Check pool status
print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
print(f"Overflow: {engine.pool.overflow()}")
```

### Query Performance

```sql
-- Enable query logging in postgresql.conf
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000  # Log queries > 1s

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Production Checklist

- [ ] PostgreSQL installed and running
- [ ] Database and user created
- [ ] Connection string configured in `.env`
- [ ] Database tables initialized
- [ ] Indexes created
- [ ] Backup strategy configured
- [ ] Monitoring enabled
- [ ] SSL/TLS enabled for connections
- [ ] Firewall rules configured
- [ ] Connection pooling optimized
- [ ] Query performance tested

## Summary

The application is **ready for PostgreSQL**! Simply:

1. Set `DATABASE_URL` environment variable
2. Run the application
3. Tables are created automatically

For production deployment on Google Cloud, follow the Cloud SQL setup instructions.
