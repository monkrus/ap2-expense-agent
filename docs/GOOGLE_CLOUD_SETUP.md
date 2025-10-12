# Google Cloud Deployment Setup Guide

This guide walks you through deploying the AP2 Expense Agent to Google Cloud Platform.

## Prerequisites

- Google Cloud Project: `ap2-expense-agent` (✓ Already created)
- Project ID: `ap2-expense-agent`
- [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install) installed
- GitHub repository access

## Step-by-Step Setup

### 1. Install Google Cloud SDK

If you haven't already, install the gcloud CLI:

**Windows:**
```bash
# Download and run the installer from:
# https://cloud.google.com/sdk/docs/install#windows
```

**macOS/Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 2. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project ap2-expense-agent
```

### 3. Run the Setup Script

The setup script will:
- Enable required Google Cloud APIs
- Create a service account for GitHub Actions
- Generate a service account key
- Grant necessary permissions

```bash
# Make the script executable (macOS/Linux)
chmod +x setup-gcloud.sh
./setup-gcloud.sh

# Windows (Git Bash or WSL)
bash setup-gcloud.sh
```

### 4. Set Up Cloud SQL (PostgreSQL Database)

```bash
# Create PostgreSQL instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_SECURE_ROOT_PASSWORD

# Create the application database
gcloud sql databases create expense_agent_db \
  --instance=ap2-expense-db

# Create database user
gcloud sql users create expense_agent_user \
  --instance=ap2-expense-db \
  --password=YOUR_SECURE_USER_PASSWORD

# Get connection name for later use
gcloud sql instances describe ap2-expense-db --format="value(connectionName)"
```

### 5. Set Up Redis (Memory Store)

```bash
# Create Redis instance (optional - can use Cloud Memorystore)
gcloud redis instances create ap2-expense-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_6_x
```

### 6. Create Secrets in Google Secret Manager

```bash
# JWT Secret Key (generate a secure random string)
echo -n "your-super-secure-jwt-secret-key-here" | \
  gcloud secrets create jwt-secret-key --data-file=-

# Google OAuth Client ID
echo -n "your-google-oauth-client-id" | \
  gcloud secrets create google-oauth-client-id --data-file=-

# Google OAuth Client Secret
echo -n "your-google-oauth-client-secret" | \
  gcloud secrets create google-oauth-client-secret --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member="serviceAccount:github-actions-deploy@ap2-expense-agent.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-oauth-client-id \
  --member="serviceAccount:github-actions-deploy@ap2-expense-agent.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-oauth-client-secret \
  --member="serviceAccount:github-actions-deploy@ap2-expense-agent.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 7. Configure GitHub Secrets

Go to your GitHub repository:
**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `GCP_SA_KEY` | Contents of `github-actions-key.json` | Service account credentials |
| `GCP_PROJECT_ID` | `ap2-expense-agent` | Your GCP project ID |
| `DATABASE_URL` | `postgresql://expense_agent_user:PASSWORD@/expense_agent_db?host=/cloudsql/CONNECTION_NAME` | PostgreSQL connection string |
| `REDIS_URL` | `redis://REDIS_IP:6379/0` | Redis connection string |
| `JWT_SECRET_KEY` | Your secure random string | JWT signing key |
| `BACKEND_URL` | `https://ap2-expense-agent-backend-HASH-uc.a.run.app` | Set after first deployment |
| `SENTRY_DSN` | Optional | Error tracking (if using Sentry) |
| `SLACK_WEBHOOK_URL` | Optional | Deployment notifications |

### 8. Enable Automatic Deployment

Uncomment the push trigger in `.github/workflows/deploy.yml`:

```yaml
on:
  push:  # Uncomment these lines
    branches: [ main ]  # Uncomment these lines
  workflow_dispatch:
    ...
```

### 9. Test Manual Deployment

Before enabling automatic deployment, test manually:

1. Go to GitHub repository → **Actions** tab
2. Select **"Deploy to Google Cloud"** workflow
3. Click **"Run workflow"**
4. Select environment: **staging**
5. Click **"Run workflow"** button

### 10. Verify Deployment

After successful deployment:

```bash
# Check backend service
gcloud run services describe ap2-expense-agent-backend --region=us-central1

# Get backend URL
gcloud run services describe ap2-expense-agent-backend \
  --region=us-central1 \
  --format="value(status.url)"

# Test health endpoint
curl https://YOUR-BACKEND-URL/health
```

## Database Migration

The deployment workflow automatically runs database migrations. To run manually:

```bash
# Connect to Cloud SQL proxy
cloud_sql_proxy -instances=CONNECTION_NAME=tcp:5432

# In another terminal, run migrations
cd backend
DATABASE_URL="postgresql://expense_agent_user:PASSWORD@localhost:5432/expense_agent_db" \
  alembic upgrade head
```

## Estimated Monthly Costs

Based on free tier and minimal usage:

- **Cloud Run**: $0-5/month (free tier covers most development)
- **Cloud SQL (db-f1-micro)**: ~$10-15/month
- **Cloud Storage**: <$1/month
- **Redis (Memory Store)**: ~$5-10/month
- **Secret Manager**: <$1/month

**Total**: ~$15-30/month for development/staging

## Scaling to Production

For production deployment:

1. Upgrade Cloud SQL tier: `db-custom-2-4096` (~$80-100/month)
2. Increase Cloud Run instances: `--min-instances=3`
3. Set up Cloud CDN for frontend
4. Enable Cloud Armor for DDoS protection
5. Set up monitoring with Cloud Monitoring
6. Configure alerting policies

## Troubleshooting

### Deployment Fails with Authentication Error
- Verify `GCP_SA_KEY` secret is correctly set in GitHub
- Check service account has necessary permissions

### Database Connection Issues
- Verify Cloud SQL instance is running
- Check DATABASE_URL secret is correct
- Ensure Cloud Run has Cloud SQL connection configured

### 502 Bad Gateway
- Check backend logs: `gcloud run services logs read ap2-expense-agent-backend --region=us-central1`
- Verify environment variables are set correctly
- Check database migrations completed successfully

## Useful Commands

```bash
# View backend logs
gcloud run services logs read ap2-expense-agent-backend --region=us-central1 --limit=50

# View frontend logs
gcloud run services logs read ap2-expense-agent-frontend --region=us-central1 --limit=50

# Update environment variable
gcloud run services update ap2-expense-agent-backend \
  --region=us-central1 \
  --set-env-vars="NEW_VAR=value"

# Roll back to previous revision
gcloud run services update-traffic ap2-expense-agent-backend \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Delete all resources (cleanup)
gcloud run services delete ap2-expense-agent-backend --region=us-central1
gcloud run services delete ap2-expense-agent-frontend --region=us-central1
gcloud sql instances delete ap2-expense-db
gcloud redis instances delete ap2-expense-redis --region=us-central1
```

## Security Best Practices

1. **Never commit** `github-actions-key.json` to git
2. **Rotate secrets** regularly (every 90 days)
3. **Use Secret Manager** for all sensitive values
4. **Enable VPC** for production workloads
5. **Set up Cloud Armor** for DDoS protection
6. **Enable audit logs** for compliance
7. **Use least privilege** for service accounts

## Support

For issues or questions:
- Check [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- Review deployment logs in GitHub Actions
- Check application logs in Google Cloud Console
