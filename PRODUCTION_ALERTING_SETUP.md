# Production Alerting Configuration Guide

**Priority**: CRITICAL
**Estimated Time**: 2 hours
**Prerequisites**: Production environment deployed
**Status**: ⚠️ Code exists, needs activation

---

## Overview

This guide configures production alerting for AP2 Expense Agent, including:
- Slack notifications (team alerts)
- PagerDuty (critical incidents)
- Cloud Monitoring alerts (GCP)
- On-call rotation setup

**Alert Infrastructure Status**:
- ✅ Code implemented (`backend/src/monitoring.py`)
- ✅ Alert policies defined (`monitoring/alerts/alert-policies.yaml`)
- ❌ Environment variables not configured
- ❌ On-call rotation not defined

---

## Part 1: Slack Integration (30 minutes)

### Step 1: Create Slack Webhook

**Instructions**:
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. App Name: "AP2 Expense Agent Alerts"
4. Workspace: Select your Slack workspace
5. Click "Incoming Webhooks" in sidebar
6. Toggle "Activate Incoming Webhooks" to ON
7. Click "Add New Webhook to Workspace"
8. Select channel: `#ap2-alerts` (create if doesn't exist)
9. Click "Allow"
10. Copy webhook URL (starts with `https://hooks.slack.com/services/...`)

### Step 2: Configure Environment Variable

**Production `.env`**:
```bash
# Add to backend/.env.production or Secret Manager
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

**Cloud Run Deployment**:
```bash
gcloud run services update ap2-expense-backend \
  --update-env-vars SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  --region us-central1
```

**Kubernetes Secret**:
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: alert-secrets
type: Opaque
stringData:
  slack-webhook-url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Step 3: Test Slack Alerts

**Test Script** (`scripts/test-slack-alert.sh`):
```bash
#!/bin/bash

# Test Slack webhook
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "🧪 *TEST ALERT*: AP2 Expense Agent alerting system is configured!",
    "attachments": [{
      "text": "This is a test alert from the production monitoring system.",
      "color": "good"
    }]
  }' \
  $SLACK_WEBHOOK_URL

echo "Check #ap2-alerts channel for test message"
```

**Run test**:
```bash
chmod +x scripts/test-slack-alert.sh
./scripts/test-slack-alert.sh
```

**Expected Result**: Message appears in `#ap2-alerts` Slack channel within 5 seconds.

---

## Part 2: PagerDuty Integration (30 minutes)

### Step 1: Create PagerDuty Service

**Instructions**:
1. Login to https://pagerduty.com (or create account - free trial available)
2. Go to Services → Create New Service
3. Service Name: "AP2 Expense Agent - Production"
4. Integration: Events API V2
5. Escalation Policy: Create or select existing
6. Click "Create Service"
7. Copy **Integration Key** (32-character alphanumeric)

### Step 2: Configure Environment Variable

**Production `.env`**:
```bash
PAGERDUTY_INTEGRATION_KEY=your-32-character-integration-key-here
```

**Cloud Run**:
```bash
gcloud run services update ap2-expense-backend \
  --update-env-vars PAGERDUTY_INTEGRATION_KEY=your-integration-key \
  --region us-central1
```

### Step 3: Test PagerDuty Alerts

**Test Script** (`scripts/test-pagerduty-alert.sh`):
```bash
#!/bin/bash

# Test PagerDuty integration
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H 'Content-Type: application/json' \
  -d '{
    "routing_key": "'$PAGERDUTY_INTEGRATION_KEY'",
    "event_action": "trigger",
    "payload": {
      "summary": "TEST: AP2 Expense Agent alerting test",
      "severity": "info",
      "source": "AP2 Expense Agent - Test",
      "custom_details": {
        "test": true,
        "environment": "production",
        "message": "This is a test alert to verify PagerDuty integration"
      }
    }
  }'

echo "Check PagerDuty for test incident"
```

**Run test**:
```bash
chmod +x scripts/test-pagerduty-alert.sh
./scripts/test-pagerduty-alert.sh
```

**Expected Result**: Incident appears in PagerDuty dashboard. Acknowledge and resolve it.

---

## Part 3: Google Cloud Monitoring Alerts (45 minutes)

### Step 1: Deploy Alert Policies

**Alert Policies Defined** (`monitoring/alerts/alert-policies.yaml`):
```yaml
# Already configured in your repo
alertPolicies:
  - uptime: 99.5%
  - error_rate: >5% in 5 minutes
  - latency_p95: >2 seconds
  - database_connection_failures: >3 in 1 minute
```

**Deploy to GCP**:
```bash
# Run monitoring setup script
cd monitoring
chmod +x setup-monitoring.sh
./setup-monitoring.sh
```

**Manual Deployment** (if script fails):
```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=<channel-id> \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s \
  --condition-filter='metric.type="logging.googleapis.com/user/errors"'
```

### Step 2: Create Notification Channels

**Slack Channel**:
```bash
gcloud alpha monitoring channels create \
  --display-name="Slack #ap2-alerts" \
  --type=slack \
  --channel-labels=url=$SLACK_WEBHOOK_URL
```

**Email Channel**:
```bash
gcloud alpha monitoring channels create \
  --display-name="On-Call Email" \
  --type=email \
  --channel-labels=email_address=oncall@yourcompany.com
```

**PagerDuty Channel**:
```bash
gcloud alpha monitoring channels create \
  --display-name="PagerDuty" \
  --type=pagerduty \
  --channel-labels=service_key=$PAGERDUTY_INTEGRATION_KEY
```

### Step 3: Verify Alert Policies

**List Alert Policies**:
```bash
gcloud alpha monitoring policies list
```

**Test Alert** (trigger manually):
```bash
# Trigger a test error to verify alerting
curl -X POST https://your-api.run.app/api/test/trigger-alert \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Part 4: On-Call Rotation Setup (15 minutes)

### Option 1: PagerDuty Schedule (Recommended)

**Create Schedule**:
1. PagerDuty → Schedules → Create New Schedule
2. Schedule Name: "AP2 Expense Agent - Primary On-Call"
3. Time Zone: Your team's timezone
4. Rotation Type: Weekly
5. Add team members:
   - Week 1: Alice (alice@yourcompany.com)
   - Week 2: Bob (bob@yourcompany.com)
   - Week 3: Charlie (charlie@yourcompany.com)
6. Handoff time: Monday 9:00 AM
7. Link to Escalation Policy

**Escalation Policy**:
1. Level 1: On-call engineer (immediate)
2. Level 2: Team lead (if no response in 15 min)
3. Level 3: Engineering manager (if no response in 30 min)

### Option 2: Google Calendar Schedule

**Create Shared Calendar**:
1. Google Calendar → Create new calendar
2. Name: "AP2 On-Call Schedule"
3. Share with: ops-team@yourcompany.com
4. Create recurring events:
   - Title: "On-Call: [Name]"
   - Duration: 1 week
   - Recurring: Weekly
   - Color code by person

**Document Schedule** (`docs/ON_CALL_SCHEDULE.md`):
```markdown
# On-Call Rotation

**Current On-Call**: Check Google Calendar "AP2 On-Call Schedule"

**Rotation Schedule**:
- Week of Dec 2: Alice
- Week of Dec 9: Bob
- Week of Dec 16: Charlie
- (Repeats)

**Handoff Checklist**:
- [ ] Review open incidents
- [ ] Check monitoring dashboards
- [ ] Read incident postmortems from previous week
- [ ] Ensure PagerDuty app installed on phone
```

---

## Part 5: Alert Types & Thresholds

### Critical Alerts (PagerDuty)

**Triggers PagerDuty Page**:
```python
# backend/src/monitoring.py:424-430
def alert_database_down():
    """Alert when database is down"""
    AlertManager.send_alert(
        severity="critical",
        title="Database Connection Lost",
        message="Unable to connect to the database",
        details={},
    )
```

**Defined Critical Alerts**:
1. **Database Down**: Can't connect to Cloud SQL
   - Threshold: 3 connection failures in 1 minute
   - Action: Page on-call engineer immediately

2. **Service Down**: Health check failing
   - Threshold: 3 consecutive failures
   - Action: Page on-call engineer

3. **High Error Rate**: >10% of requests failing
   - Threshold: 10% error rate for 5 minutes
   - Action: Page on-call engineer

### Warning Alerts (Slack Only)

**No PagerDuty Page**:
```python
# backend/src/monitoring.py:413-420
def alert_high_error_rate(error_count: int, time_window: int):
    """Alert on high error rate"""
    AlertManager.send_alert(
        severity="warning",
        title="High Error Rate Detected",
        message=f"{error_count} errors in {time_window} seconds",
        details={"error_count": error_count, "time_window": time_window},
    )
```

**Defined Warning Alerts**:
1. **High Error Rate**: 5-10% of requests failing
   - Threshold: 5% error rate for 5 minutes
   - Action: Slack notification to #ap2-alerts

2. **High Latency**: P95 latency > 2 seconds
   - Threshold: P95 > 2s for 5 minutes
   - Action: Slack notification

3. **Low Disk Space**: < 10% disk remaining
   - Threshold: < 10% free space
   - Action: Slack notification

4. **High Memory Usage**: > 90% memory used
   - Threshold: > 90% for 10 minutes
   - Action: Slack notification

---

## Part 6: Incident Response Playbook

### Alert Response Process

**1. Alert Received** (0-2 minutes)
- Acknowledge alert in PagerDuty (or Slack if warning)
- Check severity (critical vs warning)
- Open monitoring dashboards

**2. Initial Assessment** (2-5 minutes)
- Check service health: https://your-api.run.app/health
- Review Cloud Logging for errors
- Check recent deployments (was there a recent release?)
- Identify affected users/organizations

**3. Mitigation** (5-15 minutes)
- **If database down**: Check Cloud SQL status in GCP Console
- **If high error rate**: Review recent code changes, consider rollback
- **If high latency**: Check for traffic spike, scale up if needed
- Document steps taken in incident notes

**4. Communication** (15+ minutes)
- If user-facing: Post status update to status page (if configured)
- Update #incidents channel with progress
- Notify stakeholders if widespread impact

**5. Resolution** (varies)
- Verify metrics return to normal
- Monitor for 15 minutes to ensure stability
- Resolve PagerDuty incident
- Post summary to #incidents

**6. Postmortem** (within 48 hours)
- For critical incidents: Write blameless postmortem
- Identify root cause
- Define action items to prevent recurrence
- Share learnings with team

---

## Part 7: Monitoring Dashboards

### Google Cloud Monitoring Dashboards

**Deploy Dashboards**:
```bash
# Main dashboard
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboards/main-dashboard.json

# Billing dashboard
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboards/billing-dashboard.json
```

**Access Dashboards**:
1. GCP Console → Monitoring → Dashboards
2. Bookmark URLs for quick access during incidents

**Dashboard Metrics**:
- **System Health**: CPU, memory, disk, network
- **Application Metrics**: Request rate, error rate, latency (P50, P95, P99)
- **Business Metrics**: Expenses created, approved, AP2 transactions
- **Database Metrics**: Connection pool, query duration
- **Cache Metrics**: Hit rate, miss rate

---

## Verification Checklist

Before marking alerting as complete:

- [ ] Slack webhook configured and tested
- [ ] PagerDuty integration key configured and tested
- [ ] Test alert sent to Slack successfully
- [ ] Test incident created in PagerDuty successfully
- [ ] GCP Monitoring alert policies deployed
- [ ] Notification channels created (Slack, Email, PagerDuty)
- [ ] On-call rotation defined and documented
- [ ] Team members added to PagerDuty
- [ ] Mobile app installed on on-call phones
- [ ] Incident response playbook reviewed by team
- [ ] Dashboards deployed and accessible
- [ ] Environment variables set in production
- [ ] Alert thresholds reviewed and approved

---

## Testing Alerts End-to-End

### Full Integration Test

**Test Critical Alert**:
```bash
# 1. Temporarily break database connection (staging only!)
# 2. Trigger health check failure
curl https://your-staging-api.run.app/api/test/trigger-critical-alert

# Expected:
# - Slack message appears in #ap2-alerts (red color)
# - PagerDuty incident created
# - On-call engineer receives notification
```

**Test Warning Alert**:
```bash
# Trigger high latency warning
curl https://your-staging-api.run.app/api/test/trigger-warning-alert

# Expected:
# - Slack message appears in #ap2-alerts (orange color)
# - No PagerDuty page (warning only)
```

**Verify Alert Manager Code**:
```python
# backend/src/monitoring.py:348-411
# Review AlertManager class methods:
# - send_alert()
# - alert_high_error_rate()
# - alert_database_down()
# - alert_high_latency()
```

---

## Maintenance

### Monthly Tasks
- [ ] Review alert thresholds (too sensitive? too lenient?)
- [ ] Update on-call rotation if team changes
- [ ] Test alert delivery (fire test alert)
- [ ] Review incident response times
- [ ] Update escalation policies if needed

### Quarterly Tasks
- [ ] Audit PagerDuty users (remove inactive)
- [ ] Review incident postmortems for patterns
- [ ] Update runbooks based on learnings
- [ ] Evaluate alert fatigue (too many false positives?)

---

## Cost Estimation

**Slack**: Free (webhook-based)
**PagerDuty**:
- Free tier: 5 users, 100 SMS notifications/month
- Starter: $19/user/month (unlimited SMS, phone calls)
- Professional: $39/user/month (advanced features)

**Google Cloud Monitoring**: Included in GCP bill
- First 150 MB logs: Free
- Additional: $0.50/GB
- Alert policy notifications: Free (to Pub/Sub)
- SMS notifications: $0.10 each (via third-party)

**Recommended**: Start with free tiers, upgrade as needed.

---

## Support & Resources

**PagerDuty Documentation**: https://support.pagerduty.com
**Slack Incoming Webhooks**: https://api.slack.com/messaging/webhooks
**GCP Monitoring**: https://cloud.google.com/monitoring/docs
**Incident Response Best Practices**: https://response.pagerduty.com

**Internal Contacts**:
- DevOps Lead: devops@yourcompany.com
- On-Call Schedule: oncall@yourcompany.com
- Incident Commander: incidents@yourcompany.com

---

*Last Updated: December 4, 2025*
*Next Review: March 4, 2026*
