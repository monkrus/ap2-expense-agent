# Database Backup Strategy

## Overview
This document outlines the backup and disaster recovery strategy for the AP2 Expense Management PostgreSQL database.

## Backup Types

### 1. Full Database Backups (Daily)
**Schedule:** Every day at 2:00 AM UTC
**Retention:** 30 days
**Method:** `pg_dump` with custom format

```bash
# Backup command
pg_dump -U ap2user -h localhost -d expenses -F c -f backup_$(date +%Y%m%d).dump

# With compression
pg_dump -U ap2user -h localhost -d expenses -F c -Z 9 -f backup_$(date +%Y%m%d).dump
```

### 2. Incremental Backups (Hourly)
**Schedule:** Every hour
**Retention:** 7 days
**Method:** PostgreSQL Write-Ahead Logging (WAL) archiving

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
```

### 3. Continuous Archiving
**Method:** WAL-E or pgBackRest
**Storage:** AWS S3, Azure Blob, or local NAS

## Backup Script

### Automated Daily Backup
```bash
#!/bin/bash
# /usr/local/bin/backup_postgres.sh

# Configuration
DB_NAME="expenses"
DB_USER="ap2user"
BACKUP_DIR="/var/backups/postgresql"
RETENTION_DAYS=30
S3_BUCKET="s3://ap2-expense-backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup filename with timestamp
BACKUP_FILE="$BACKUP_DIR/expenses_$(date +%Y%m%d_%H%M%S).dump"

# Perform backup
pg_dump -U $DB_USER -d $DB_NAME -F c -Z 9 -f $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE $S3_BUCKET/

# Remove old backups
find $BACKUP_DIR -name "expenses_*.dump" -mtime +$RETENTION_DAYS -delete

# Log completion
echo "Backup completed: $BACKUP_FILE" | logger -t postgres-backup
```

### Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /usr/local/bin/backup_postgres.sh
```

## Restore Procedures

### Full Database Restore
```bash
# Drop existing database (WARNING: This deletes all data)
dropdb -U ap2user expenses

# Create new database
createdb -U ap2user expenses

# Restore from backup
pg_restore -U ap2user -d expenses -F c backup_20250104.dump
```

### Point-in-Time Recovery (PITR)
```bash
# 1. Restore base backup
pg_restore -U ap2user -d expenses backup_20250104.dump

# 2. Configure recovery in postgresql.conf
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2025-01-04 12:30:00'

# 3. Create recovery.signal file
touch /var/lib/postgresql/data/recovery.signal

# 4. Restart PostgreSQL
systemctl restart postgresql
```

## Backup Verification

### Monthly Restore Testing
```bash
#!/bin/bash
# Test restore to separate database

TEST_DB="expenses_restore_test"

# Create test database
createdb -U ap2user $TEST_DB

# Restore latest backup
LATEST_BACKUP=$(ls -t /var/backups/postgresql/expenses_*.dump | head -1)
pg_restore -U ap2user -d $TEST_DB -F c $LATEST_BACKUP

# Verify table counts
psql -U ap2user -d $TEST_DB -c "SELECT
    'users' as table, COUNT(*) as count FROM users
    UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
    UNION ALL SELECT 'audit_logs', COUNT(*) FROM audit_logs;"

# Cleanup
dropdb -U ap2user $TEST_DB
```

## Disaster Recovery Plan

### RTO (Recovery Time Objective): 1 hour
### RPO (Recovery Point Objective): 1 hour

### Recovery Steps:
1. **Identify Failure**: Monitor database health
2. **Assess Damage**: Determine if full or partial restore needed
3. **Stop Application**: Prevent further data corruption
4. **Restore Database**: Use latest backup + WAL files
5. **Verify Data**: Run integrity checks
6. **Resume Application**: Bring services back online
7. **Post-Mortem**: Document incident and improve processes

## Storage Locations

### Primary Backup Storage
- **Location:** `/var/backups/postgresql`
- **Retention:** 30 days
- **Monitoring:** Disk space alerts at 80% usage

### Off-site Backup Storage
- **Cloud Provider:** AWS S3 / Azure Blob Storage
- **Bucket:** `ap2-expense-backups`
- **Retention:** 90 days
- **Encryption:** AES-256

### WAL Archive Storage
- **Location:** `/var/lib/postgresql/wal_archive`
- **Retention:** 7 days
- **Size:** Monitor and alert when > 10GB

## Monitoring and Alerts

### Backup Health Checks
```bash
# Check last backup age
find /var/backups/postgresql -name "expenses_*.dump" -mtime -1 | wc -l

# Alert if no backup in last 24 hours
if [ $(find /var/backups/postgresql -name "expenses_*.dump" -mtime -1 | wc -l) -eq 0 ]; then
    echo "ALERT: No PostgreSQL backup in last 24 hours" | mail -s "Backup Alert" admin@example.com
fi
```

### Metrics to Monitor
- Backup completion status
- Backup file size (detect anomalies)
- Backup duration (detect performance issues)
- Disk space on backup volumes
- S3/Cloud storage sync status

## Security

### Backup Encryption
```bash
# Encrypt backup before upload
pg_dump -U ap2user -d expenses -F c | gzip | \
    openssl enc -aes-256-cbc -salt -out backup_$(date +%Y%m%d).dump.gz.enc \
    -pass pass:$BACKUP_PASSWORD
```

### Access Control
- Backup files: chmod 600
- Backup scripts: chmod 700
- Database credentials: Use .pgpass file
- S3 buckets: IAM roles with least privilege

## Compliance

### Data Retention Policy
- **Production Backups:** 90 days
- **Audit Logs:** 90 days (configurable in settings)
- **User Sessions:** 30 days
- **Revoked Tokens:** 7 days

### GDPR Compliance
- Ensure backups exclude sensitive data if user requests deletion
- Document data retention in privacy policy
- Implement secure deletion of old backups

## Cost Optimization

### Storage Tiers
- **Hot:** Last 7 days (S3 Standard)
- **Warm:** 8-30 days (S3 Infrequent Access)
- **Cold:** 31-90 days (S3 Glacier)

### Compression
- Use `pg_dump -Z 9` for maximum compression
- Typical compression ratio: 5:1 to 10:1

## Automation Tools

### Recommended Tools
1. **pgBackRest** - Advanced backup and restore
2. **Barman** - Backup and Recovery Manager
3. **WAL-E** - Continuous archiving to S3
4. **pg_probackup** - PITR backup tool

### Example pgBackRest Configuration
```ini
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=4
start-fast=y
stop-auto=y

[expenses]
pg1-path=/var/lib/postgresql/14/main
```

## Testing Schedule

- **Daily:** Automated backup verification
- **Weekly:** Test backup file integrity
- **Monthly:** Full restore to test environment
- **Quarterly:** Disaster recovery drill
- **Annually:** Review and update backup strategy
