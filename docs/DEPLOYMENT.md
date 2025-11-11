# AP2 Expense Agent - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Project Setup](#gcp-project-setup)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Options](#deployment-options)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- `gcloud` CLI (version 400.0.0+)
- `kubectl` (version 1.27+)
- `helm` (version 3.12+)
- `docker` (version 24.0+)
- `git`

### Required GCP APIs

Enable the following APIs in your GCP project:

```bash
gcloud services enable \
  container.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudkms.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  storage-api.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudcommerceprocurement.googleapis.com
```

### Required Permissions

Your GCP user/service account needs:

- `roles/owner` OR the following roles:
  - `roles/container.admin`
  - `roles/cloudsql.admin`
  - `roles/secretmanager.admin`
  - `roles/cloudkms.admin`
  - `roles/storage.admin`
  - `roles/iam.serviceAccountAdmin`
  - `roles/cloudbuild.builds.editor`
  - `roles/run.admin`

---

## GCP Project Setup

### 1. Set Environment Variables

Create a `.env.deployment` file:

```bash
# GCP Configuration
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export GCP_ZONE="us-central1-a"

# Application Configuration
export APP_DOMAIN="your-domain.com"
export APP_NAME="ap2-expense"
export ENVIRONMENT="production"

# Database Configuration
export DB_INSTANCE_NAME="ap2-expense-db"
export DB_NAME="ap2_expense"
export DB_USER="ap2user"

# Service Account
export SA_NAME="ap2-expense-sa"
export SA_EMAIL="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# KMS Configuration
export KMS_KEYRING="ap2-expense-keyring"
export KMS_KEY="ap2-mandate-signing-key"

# Notification Email
export NOTIFICATION_EMAIL="ops@your-company.com"
```

Source the file:

```bash
source .env.deployment
```

### 2. Run Setup Script

Execute the automated setup script:

```bash
./scripts/setup-gcp-project.sh
```

This script will:
- Set the active GCP project
- Enable required APIs
- Create service accounts
- Set up IAM bindings
- Create Cloud SQL instance
- Create KMS keyring and keys
- Create Secret Manager secrets
- Reserve static IP address
- Set up Cloud Storage buckets

---

## Environment Configuration

### 1. Generate Secure Secrets

Generate JWT secrets:

```bash
# JWT Secret Key (32 bytes)
JWT_SECRET=$(openssl rand -hex 32)

# JWT Refresh Secret Key (32 bytes)
JWT_REFRESH_SECRET=$(openssl rand -hex 32)

echo "JWT_SECRET: $JWT_SECRET"
echo "JWT_REFRESH_SECRET: $JWT_REFRESH_SECRET"
```

### 2. Store Secrets in Secret Manager

```bash
# Database password
echo -n "YOUR_SECURE_DB_PASSWORD" | gcloud secrets create database-password \
  --data-file=- \
  --replication-policy="automatic"

# JWT secrets
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key \
  --data-file=- \
  --replication-policy="automatic"

echo -n "$JWT_REFRESH_SECRET" | gcloud secrets create jwt-refresh-secret-key \
  --data-file=- \
  --replication-policy="automatic"

# Stripe keys (if using)
echo -n "sk_live_YOUR_STRIPE_SECRET" | gcloud secrets create stripe-secret-key \
  --data-file=- \
  --replication-policy="automatic"
```

### 3. Grant Service Account Access to Secrets

```bash
for secret in database-password jwt-secret-key jwt-refresh-secret-key stripe-secret-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
done
```

### 4. Configure Database

Create Cloud SQL instance (if not using setup script):

```bash
gcloud sql instances create ${DB_INSTANCE_NAME} \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-8192 \
  --region=${GCP_REGION} \
  --storage-type=SSD \
  --storage-size=100GB \
  --storage-auto-increase \
  --backup \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4 \
  --enable-point-in-time-recovery \
  --availability-type=REGIONAL
```

Create database and user:

```bash
# Set root password
gcloud sql users set-password postgres \
  --instance=${DB_INSTANCE_NAME} \
  --password="YOUR_ROOT_PASSWORD"

# Create application database
gcloud sql databases create ${DB_NAME} \
  --instance=${DB_INSTANCE_NAME}

# Create application user
gcloud sql users create ${DB_USER} \
  --instance=${DB_INSTANCE_NAME} \
  --password="YOUR_SECURE_DB_PASSWORD"
```

---

## Deployment Options

Choose one of the following deployment methods:

### Option 1: Cloud Run (Recommended for getting started)

#### Update cloudbuild.yaml

The updated `cloudbuild.yaml` will include all necessary environment variables and secrets.

#### Deploy

```bash
gcloud builds submit --config=cloudbuild.yaml
```

#### Configure Custom Domain

```bash
# Map domain to Cloud Run service
gcloud run domain-mappings create \
  --service=ap2-expense-backend \
  --domain=api.${APP_DOMAIN} \
  --region=${GCP_REGION}

gcloud run domain-mappings create \
  --service=ap2-expense-frontend \
  --domain=${APP_DOMAIN} \
  --region=${GCP_REGION}
```

### Option 2: Google Kubernetes Engine (GKE)

#### Create GKE Cluster

```bash
gcloud container clusters create ${APP_NAME}-cluster \
  --region=${GCP_REGION} \
  --num-nodes=1 \
  --machine-type=n2-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade \
  --enable-ip-alias \
  --network="default" \
  --subnetwork="default" \
  --workload-pool=${GCP_PROJECT_ID}.svc.id.goog \
  --enable-stackdriver-kubernetes
```

#### Configure kubectl

```bash
gcloud container clusters get-credentials ${APP_NAME}-cluster \
  --region=${GCP_REGION}
```

#### Create Namespace

```bash
kubectl create namespace ap2-expense
kubectl config set-context --current --namespace=ap2-expense
```

#### Set up Workload Identity

```bash
# Create K8s service account
kubectl create serviceaccount ap2-expense-sa \
  --namespace=ap2-expense

# Bind K8s SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[ap2-expense/ap2-expense-sa]"

# Annotate K8s service account
kubectl annotate serviceaccount ap2-expense-sa \
  --namespace=ap2-expense \
  iam.gke.io/gcp-service-account=${SA_EMAIL}
```

#### Deploy with kubectl

```bash
# Update configuration files with actual values
./scripts/update-k8s-configs.sh

# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/billing-cronjob.yaml
```

### Option 3: Helm Chart

#### Update Helm values

```bash
# Copy and customize values
cp helm/ap2-expense/values.yaml helm/ap2-expense/values.production.yaml

# Edit values.production.yaml with your actual values
# Use the helper script:
./scripts/update-helm-values.sh
```

#### Install with Helm

```bash
helm install ap2-expense ./helm/ap2-expense \
  --namespace=ap2-expense \
  --create-namespace \
  --values=helm/ap2-expense/values.production.yaml
```

#### Upgrade Helm Release

```bash
helm upgrade ap2-expense ./helm/ap2-expense \
  --namespace=ap2-expense \
  --values=helm/ap2-expense/values.production.yaml
```

---

## Post-Deployment Verification

### 1. Check Pod Status

```bash
kubectl get pods -n ap2-expense
```

Expected output:
```
NAME                        READY   STATUS    RESTARTS   AGE
backend-xxx-yyy            1/1     Running   0          2m
backend-xxx-zzz            1/1     Running   0          2m
backend-xxx-aaa            1/1     Running   0          2m
frontend-xxx-bbb           1/1     Running   0          2m
frontend-xxx-ccc           1/1     Running   0          2m
```

### 2. Check Services

```bash
kubectl get svc -n ap2-expense
```

### 3. Check Ingress

```bash
kubectl get ingress -n ap2-expense
kubectl describe ingress ap2-expense-ingress -n ap2-expense
```

Wait for the ingress to receive an IP address (may take 5-10 minutes).

### 4. Test Health Endpoints

```bash
# Get the load balancer IP
INGRESS_IP=$(kubectl get ingress ap2-expense-ingress -n ap2-expense -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test backend health
curl http://${INGRESS_IP}/api/health

# Expected: {"status":"healthy","service":"AP2 Expense Management Agent"}
```

### 5. Test Frontend

```bash
curl -I http://${INGRESS_IP}/
```

Expected: HTTP 200 response

### 6. Verify Database Connectivity

```bash
# Exec into backend pod
BACKEND_POD=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

kubectl exec -it ${BACKEND_POD} -n ap2-expense -- python -c "
from src.database import engine
try:
    conn = engine.connect()
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### 7. Run Database Migrations

```bash
# Exec into backend pod
kubectl exec -it ${BACKEND_POD} -n ap2-expense -- alembic upgrade head
```

### 8. Check Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n ap2-expense

# Frontend logs
kubectl logs -f deployment/frontend -n ap2-expense
```

### 9. Verify Monitoring

```bash
# Check if metrics are being scraped
kubectl get servicemonitor -n ap2-expense
```

Visit Cloud Console:
- Monitoring > Dashboards
- Logging > Logs Explorer

### 10. Test API Authentication

```bash
# Register a test user
curl -X POST http://${INGRESS_IP}/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "username": "testuser",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://${INGRESS_IP}/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test@example.com",
    "password": "TestPassword123!"
  }'
```

---

## Troubleshooting

### Pods Not Starting

**Check events:**
```bash
kubectl describe pod <pod-name> -n ap2-expense
```

**Common issues:**
- ImagePullBackOff: Check if images exist in GCR
- CrashLoopBackOff: Check logs for application errors
- Pending: Check resource availability

### Database Connection Issues

**Check Cloud SQL Proxy:**
```bash
kubectl logs <backend-pod> -n ap2-expense -c cloudsql-proxy
```

**Verify service account permissions:**
```bash
gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL}"
```

### Secret Access Issues

**Verify secret exists:**
```bash
gcloud secrets describe jwt-secret-key
```

**Check IAM bindings:**
```bash
gcloud secrets get-iam-policy jwt-secret-key
```

### SSL Certificate Not Provisioning

**Check managed certificate status:**
```bash
kubectl describe managedcertificate ap2-expense-cert -n ap2-expense
```

**DNS verification:**
```bash
dig ${APP_DOMAIN}
dig api.${APP_DOMAIN}
```

### High Memory Usage

**Check resource limits:**
```bash
kubectl top pods -n ap2-expense
```

**Increase limits if needed:**
```bash
kubectl patch deployment backend -n ap2-expense -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

### Marketplace Integration Issues

**Check billing cronjob:**
```bash
kubectl get cronjob billing-usage-reporter -n ap2-expense
kubectl get jobs -n ap2-expense
```

**Check cronjob logs:**
```bash
LATEST_JOB=$(kubectl get jobs -n ap2-expense -l app.kubernetes.io/component=billing --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl logs job/${LATEST_JOB} -n ap2-expense
```

---

## Rollback Procedures

### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/backend -n ap2-expense

# Rollback to previous version
kubectl rollout undo deployment/backend -n ap2-expense

# Rollback to specific revision
kubectl rollout undo deployment/backend -n ap2-expense --to-revision=2
```

### Helm Rollback

```bash
# View release history
helm history ap2-expense -n ap2-expense

# Rollback to previous release
helm rollback ap2-expense -n ap2-expense

# Rollback to specific revision
helm rollback ap2-expense 2 -n ap2-expense
```

### Cloud Run Rollback

```bash
# List revisions
gcloud run revisions list --service=ap2-expense-backend --region=${GCP_REGION}

# Rollback to specific revision
gcloud run services update-traffic ap2-expense-backend \
  --to-revisions=<revision-name>=100 \
  --region=${GCP_REGION}
```

---

## Maintenance Tasks

### Update Application

```bash
# Update image tags in deployment
kubectl set image deployment/backend backend=gcr.io/${GCP_PROJECT_ID}/ap2-expense-backend:v1.1.0 -n ap2-expense

# Watch rollout
kubectl rollout status deployment/backend -n ap2-expense
```

### Scale Manually

```bash
# Scale backend
kubectl scale deployment/backend --replicas=5 -n ap2-expense

# Scale frontend
kubectl scale deployment/frontend --replicas=3 -n ap2-expense
```

### Database Maintenance

```bash
# Create manual backup
gcloud sql backups create \
  --instance=${DB_INSTANCE_NAME}

# List backups
gcloud sql backups list --instance=${DB_INSTANCE_NAME}

# Restore from backup
gcloud sql backups restore <backup-id> \
  --backup-instance=${DB_INSTANCE_NAME} \
  --backup-instance=${DB_INSTANCE_NAME}
```

### Rotate Secrets

```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# Update Secret Manager
echo -n "$NEW_SECRET" | gcloud secrets versions add jwt-secret-key --data-file=-

# Restart pods to pick up new secret
kubectl rollout restart deployment/backend -n ap2-expense
```

---

## Security Considerations

1. **Never commit secrets** to version control
2. **Use Secret Manager** for all sensitive data
3. **Enable VPC Service Controls** for production
4. **Implement Binary Authorization** for image verification
5. **Regular security scans** of containers
6. **Keep dependencies updated** (Dependabot/Renovate)
7. **Implement secrets rotation** every 90 days
8. **Enable audit logging** for all GCP resources
9. **Use private GKE clusters** for enhanced security
10. **Implement network policies** to restrict pod communication

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/monkrus/ap2-expense-agent/issues
- Documentation: https://docs.ap2expense.com
- Email: support@ap2expense.com
