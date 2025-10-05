# Data Retention Policy

## Overview
This document outlines the data retention policies for the AP2 Expense Management system.

## Retention Periods

### Authentication & Security Data

| Data Type | Retention Period | Cleanup Method | Rationale |
|-----------|-----------------|----------------|-----------|
| Audit Logs | 90 days | Automated daily cleanup | Compliance, security investigation |
| User Sessions | 30 days | Automated daily cleanup | Active session tracking |
| Revoked Refresh Tokens | 7 days | Automated daily cleanup | Security audit trail |
| Expired Refresh Tokens | Immediate | Automated daily cleanup | No longer valid |
| Used Password Reset Tokens | 1 day | Automated daily cleanup | Prevent token reuse |
| Expired Password Reset Tokens | Immediate | Automated daily cleanup | No longer valid |

### User Data

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| User Accounts | Indefinite | Until user deletion or GDPR request |
| User Profile Data | Indefinite | Updated as needed |
| Login History (via audit logs) | 90 days | Part of audit log retention |
| 2FA Backup Codes | Until used or 2FA disabled | Stored encrypted |

## Configuration

### Settings (backend/src/config.py)
```python
# Data Retention (in days)
audit_log_retention_days: int = 90
session_retention_days: int = 30
revoked_token_retention_days: int = 7
```

### Environment Variables
Override in `.env` file:
```bash
AUDIT_LOG_RETENTION_DAYS=90
SESSION_RETENTION_DAYS=30
REVOKED_TOKEN_RETENTION_DAYS=7
```

## Automated Cleanup

### Maintenance Service
Located at: `backend/src/maintenance.py`

Cleanup tasks:
1. **Old Audit Logs** - Remove logs older than 90 days
2. **Expired Sessions** - Remove sessions older than 30 days or expired
3. **Revoked Tokens** - Remove revoked tokens older than 7 days
4. **Expired Tokens** - Remove all expired refresh/reset tokens
5. **Used Reset Tokens** - Remove used password reset tokens older than 1 day

### Running Maintenance Tasks

#### Manual Execution
```bash
# From backend directory
python scripts/run_maintenance.py
```

#### Automated Scheduling (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add daily cleanup at 3 AM
0 3 * * * cd /path/to/backend && python scripts/run_maintenance.py >> /var/log/ap2-maintenance.log 2>&1
```

#### Automated Scheduling (Windows)
```powershell
# Create scheduled task (PowerShell as Administrator)
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\backend\scripts\run_maintenance.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "AP2-Database-Maintenance" -Description "Daily database cleanup"
```

### API Endpoint (Admin Only)
```bash
# Trigger manual cleanup via API
curl -X POST http://localhost:8000/api/v1/admin/maintenance \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## Compliance

### GDPR - Right to be Forgotten
When a user requests account deletion:

1. **Soft Delete** (Recommended)
   - Mark user as `is_active = False`
   - Anonymize personal data
   - Retain audit logs with anonymized user ID

2. **Hard Delete** (Full Removal)
   ```sql
   -- This cascades to all related data
   DELETE FROM users WHERE id = 'user_id';
   ```

3. **Audit Trail**
   - Log deletion request in audit logs
   - Export user data before deletion (if requested)

### Data Export
Users can request their data via:
```python
# Implement in backend/src/routes/users.py
@router.get("/export")
async def export_user_data(current_user: User = Depends(get_current_active_user)):
    # Return JSON with all user data
    pass
```

## Monitoring

### Cleanup Statistics
The maintenance service returns statistics:
```json
{
  "audit_logs": 1250,
  "sessions": 45,
  "revoked_tokens": 12,
  "expired_tokens": 8,
  "used_reset_tokens": 3,
  "timestamp": "2025-01-04T03:00:00"
}
```

### Alerts
Set up monitoring for:
- Maintenance task failures
- Excessive data accumulation (tables growing too large)
- Cleanup tasks taking too long (> 5 minutes)

### Logging
All cleanup operations are logged:
```python
logger.info(f"Deleted {deleted_count} audit logs older than {retention_days} days")
```

## Database Growth Estimation

### Expected Growth Rates
- **Audit Logs**: ~1,000 entries/day (varies by usage)
- **Sessions**: ~100 new sessions/day
- **Refresh Tokens**: ~100 new tokens/day

### Storage Estimates (90-day retention)
- Audit Logs: ~90,000 rows × 500 bytes = ~45 MB
- Sessions: ~3,000 rows × 300 bytes = ~900 KB
- Refresh Tokens: ~9,000 rows × 200 bytes = ~1.8 MB

**Total retention data: ~50 MB** (minimal impact)

## Legal Requirements

### Compliance Standards
- **GDPR**: 30 days for marketing data, varies for operational data
- **SOX**: 7 years for financial audit trails
- **PCI DSS**: 90 days minimum for security logs

### Recommended Adjustments for Compliance
If handling financial data requiring SOX compliance:
```python
# Extend audit log retention for financial transactions
audit_log_retention_days: int = 2555  # 7 years
```

## Review Schedule

- **Monthly**: Review retention policy effectiveness
- **Quarterly**: Analyze storage usage and adjust retention periods
- **Annually**: Update policy to comply with new regulations

## Emergency Data Recovery

If data needs to be recovered after cleanup:
1. Check database backups (see DATABASE_BACKUP_STRATEGY.md)
2. Restore to test environment
3. Extract required data
4. Import to production (if approved)

## Performance Optimization

### Partitioning Large Tables
For high-volume deployments, consider table partitioning:
```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs_2025_01 PARTITION OF audit_logs
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### Index Optimization
Ensure indexes on date columns for efficient cleanup:
```sql
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
```

## Contact

For questions about data retention:
- Technical: dev-team@ap2expense.com
- Legal/Compliance: legal@ap2expense.com
- DPO (Data Protection Officer): dpo@ap2expense.com
