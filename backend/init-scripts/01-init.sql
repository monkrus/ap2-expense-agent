-- PostgreSQL Initialization Script for AP2 Expense Agent
-- This script runs automatically when the Docker container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For multi-column indexes

-- Create custom types if needed
DO $$ BEGIN
    CREATE TYPE subscription_tier AS ENUM ('starter', 'professional', 'enterprise', 'enterprise_plus');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'manager', 'employee');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE expense_status AS ENUM ('pending', 'approved', 'rejected', 'paid');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Set timezone
SET timezone TO 'UTC';

-- Performance tuning settings
ALTER DATABASE expenses SET random_page_cost = 1.1;  -- For SSD storage
ALTER DATABASE expenses SET effective_cache_size = '4GB';
ALTER DATABASE expenses SET shared_buffers = '1GB';
ALTER DATABASE expenses SET work_mem = '50MB';

-- Enable row-level security (for future use)
ALTER DATABASE expenses SET row_security = on;

-- Logging for development
ALTER DATABASE expenses SET log_min_duration_statement = 1000;  -- Log queries > 1s
ALTER DATABASE expenses SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;

-- Create schema for future partitioning
CREATE SCHEMA IF NOT EXISTS partitions;
GRANT ALL ON SCHEMA partitions TO ap2user;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialization completed successfully';
    RAISE NOTICE 'Database: expenses';
    RAISE NOTICE 'User: ap2user';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_trgm, btree_gin';
END $$;
