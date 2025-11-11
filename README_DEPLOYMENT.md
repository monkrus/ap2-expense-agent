# AP2 Expense Agent - Deployment Quick Start

## Overview

This guide provides a quick-start path to deploying the AP2 Expense Agent on Google Cloud Platform. For detailed documentation, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Prerequisites

- GCP Project with billing enabled
- `gcloud` CLI installed and configured
- Domain name (for production) or willingness to use temporary URLs
- 30-60 minutes for initial setup

---

## Deployment Options

Choose the deployment method that best fits your needs:

| Method | Best For | Setup Time | Cost | Scalability |
|--------|----------|------------|------|-------------|
| **Cloud Run** | Quick start, serverless | 15 min | Low (pay per use) | Auto |
| **GKE (Kubernetes)** | Production, control | 45 min | Medium (always on) | Manual/Auto |
| **Helm** | Enterprise, GitOps | 45 min | Medium | Manual/Auto |

---

## Option 1: Cloud Run (Fastest)

### 1. Setup Environment

```bash
# Clone repository
git clone https://github.com/monkrus/ap2-expense-agent
cd ap2-expense-agent

# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Configure gcloud
gcloud config set project $GCP_PROJECT_ID
```

### 2. Run Automated Setup

```bash
# Create .env.deployment file
cat > .env.deployment <<EOF
export GCP_PROJECT_ID="$GCP_PROJECT_ID"
export GCP_REGION="us-central1"
export GCP_ZONE="us-central1-a"
export APP_DOMAIN="temporary.example.com"  # Update later
export APP_NAME="ap2-expense"
export ENVIRONMENT="production"
export DB_INSTANCE_NAME="ap2-expense-db"
export DB_NAME="ap2_expense"
export DB_USER="ap2user"
export SA_NAME="ap2-expense-sa"
export KMS_KEYRING="ap2-expense-keyring"
export KMS_KEY="ap2-mandate-signing-key"
export NOTIFICATION_EMAIL="ops@your-company.com"
EOF

# Source environment
source .env.deployment

# Run setup script (creates all GCP resources)
chmod +x scripts/setup-gcp-project.sh
./scripts/setup-gcp-project.sh
```

**This script will:**
- Enable required GCP APIs
- Create service accounts
- Set up Cloud SQL database
- Configure Cloud KMS
- Create Secret Manager secrets
- Set up Cloud Storage buckets
- Reserve static IP

**Expected time**: 10-15 minutes

### 3. Deploy to Cloud Run

```bash
# Submit build (builds images and deploys)
gcloud builds submit --config=cloudbuild.yaml
```

**Expected time**: 10-15 minutes

### 4. Get Service URLs

```bash
# Backend URL
gcloud run services describe ap2-expense-backend \
  --region=$GCP_REGION \
  --format="value(status.url)"

# Frontend URL
gcloud run services describe ap2-expense-frontend \
  --region=$GCP_REGION \
  --format="value(status.url)"
```

### 5. Test Deployment

```bash
# Test backend health
BACKEND_URL=$(gcloud run services describe ap2-expense-backend --region=$GCP_REGION --format="value(status.url)")
curl $BACKEND_URL/health

# Should return: {"status":"healthy","service":"AP2 Expense Management Agent"}
```

### 6. Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=ap2-expense-backend \
  --domain=api.your-domain.com \
  --region=$GCP_REGION

gcloud run domain-mappings create \
  --service=ap2-expense-frontend \
  --domain=your-domain.com \
  --region=$GCP_REGION
```

---

## Option 2: Google Kubernetes Engine

### 1. Setup Environment (Same as Cloud Run)

```bash
source .env.deployment
./scripts/setup-gcp-project.sh
```

### 2. Create GKE Cluster

```bash
# Create cluster (takes 5-10 minutes)
gcloud container clusters create ap2-expense-cluster \
  --region=$GCP_REGION \
  --num-nodes=1 \
  --machine-type=n2-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --enable-workload-identity \
  --enable-stackdriver-kubernetes

# Get credentials
gcloud container clusters get-credentials ap2-expense-cluster --region=$GCP_REGION
```

### 3. Update Configuration Files

```bash
# Update placeholders with actual values
chmod +x scripts/update-k8s-configs.sh
./scripts/update-k8s-configs.sh
```

### 4. Build and Push Images

```bash
# Build backend
docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest -f Dockerfile.backend .
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest

# Build frontend
docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest -f Dockerfile.frontend .
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest
```

### 5. Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/serviceaccount.yaml

# Set up Workload Identity
gcloud iam service-accounts add-iam-policy-binding \
  ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[ap2-expense/ap2-expense-sa]"

kubectl annotate serviceaccount ap2-expense-sa \
  -n ap2-expense \
  iam.gke.io/gcp-service-account=ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com

# Deploy application
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/billing-cronjob.yaml
```

### 6. Wait for Ingress

```bash
# Watch ingress (takes 5-10 minutes to provision)
kubectl get ingress -n ap2-expense -w

# Get IP when ready
kubectl get ingress ap2-expense-ingress -n ap2-expense \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 7. Test Deployment

```bash
INGRESS_IP=$(kubectl get ingress ap2-expense-ingress -n ap2-expense -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health
curl http://${INGRESS_IP}/api/health

# Test frontend
curl -I http://${INGRESS_IP}/
```

---

## Option 3: Helm Chart

### 1. Setup (Same as GKE steps 1-2)

```bash
source .env.deployment
./scripts/setup-gcp-project.sh
# Create GKE cluster (see Option 2, step 2)
```

### 2. Update Helm Values

```bash
# Create production values
cp helm/ap2-expense/values.yaml helm/ap2-expense/values.production.yaml

# Update with script
./scripts/update-helm-values.sh
```

### 3. Install with Helm

```bash
# Install
helm install ap2-expense ./helm/ap2-expense \
  --namespace=ap2-expense \
  --create-namespace \
  --values=helm/ap2-expense/values.production.yaml

# Watch rollout
kubectl get pods -n ap2-expense -w
```

### 4. Verify Deployment

```bash
# Check status
helm status ap2-expense -n ap2-expense

# Test application
kubectl port-forward -n ap2-expense svc/backend-service 8000:8000 &
curl http://localhost:8000/health
```

---

## Post-Deployment Steps

### 1. Run Database Migrations

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -n ap2-expense -- alembic upgrade head
```

### 2. Create Admin User

```bash
# Register admin user
curl -X POST https://your-domain.com/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@your-company.com",
    "password": "SecurePassword123!",
    "username": "admin",
    "full_name": "Admin User"
  }'

# Promote to admin (via database)
kubectl exec -it $BACKEND_POD -n ap2-expense -- python -c "
from src.database import SessionLocal
from src.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'admin@your-company.com').first()
user.role = 'admin'
db.commit()
print('User promoted to admin')
"
```

### 3. Configure Monitoring

```bash
# Deploy alert policies
gcloud alpha monitoring policies create --policy-from-file=monitoring/alerts/alert-policies.yaml

# Create notification channel (do this manually in console)
# Then update alert policies with channel ID
```

### 4. Test Complete Workflow

```bash
# Set API URL
export API_URL="https://your-domain.com/api"

# 1. Register user
curl -X POST $API_URL/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","username":"testuser"}'

# 2. Login
TOKEN=$(curl -X POST $API_URL/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"Test123!"}' \
  | jq -r '.access_token')

# 3. Create organization
ORG_ID=$(curl -X POST $API_URL/v1/organizations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Org"}' \
  | jq -r '.id')

# 4. Create expense
curl -X POST $API_URL/v1/expenses \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Id: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "category": "travel",
    "description": "Test expense",
    "date": "2025-11-10"
  }'

echo "✅ Complete workflow test passed!"
```

---

## Troubleshooting

### Cloud SQL Connection Issues

```bash
# Check Cloud SQL Proxy logs (K8s)
kubectl logs -l app.kubernetes.io/component=backend -n ap2-expense -c cloudsql-proxy

# Test connection
kubectl exec -it $BACKEND_POD -n ap2-expense -- python -c "
from src.database import engine
conn = engine.connect()
print('✅ Connected')
conn.close()
"
```

### Secret Access Issues

```bash
# Verify service account has access
gcloud secrets get-iam-policy jwt-secret-key

# Grant access if needed
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member="serviceAccount:ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Pod Not Starting

```bash
# Check events
kubectl describe pod $BACKEND_POD -n ap2-expense

# Check logs
kubectl logs $BACKEND_POD -n ap2-expense

# Common issues:
# - ImagePullBackOff: Image doesn't exist in GCR
# - CrashLoopBackOff: Application error, check logs
# - Pending: Insufficient resources or PVC issues
```

---

## Scaling

### Manual Scaling (K8s)

```bash
# Scale backend
kubectl scale deployment/backend --replicas=5 -n ap2-expense

# Scale frontend
kubectl scale deployment/frontend --replicas=3 -n ap2-expense
```

### Auto-scaling (Already configured via HPA)

```bash
# Check HPA status
kubectl get hpa -n ap2-expense

# Metrics
kubectl top pods -n ap2-expense
```

---

## Maintenance

### Backup Database

```bash
./scripts/backup-database.sh create
```

### Update Application

```bash
# Kubernetes
kubectl set image deployment/backend backend=gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:v1.1.0 -n ap2-expense
kubectl rollout status deployment/backend -n ap2-expense

# Cloud Run
gcloud builds submit --config=cloudbuild.yaml
```

### View Logs

```bash
# Kubernetes
kubectl logs -f deployment/backend -n ap2-expense

# Cloud Run
gcloud run services logs read ap2-expense-backend --region=$GCP_REGION
```

---

## Cost Estimation

### Cloud Run (Smallest deployment)

- Backend: ~$30-50/month (always-on 1 instance)
- Frontend: ~$10-20/month (always-on 1 instance)
- Cloud SQL: ~$100-150/month (db-custom-2-8192)
- Cloud Storage: ~$5-10/month
- **Total: ~$145-230/month**

### GKE (Production deployment)

- GKE Cluster: ~$75/month (control plane)
- Nodes: ~$200-400/month (n2-standard-4 × 2-4 nodes)
- Cloud SQL: ~$100-150/month
- Load Balancer: ~$20/month
- Cloud Storage: ~$10/month
- **Total: ~$405-655/month**

*Costs vary based on usage, region, and configuration*

---

## Next Steps

1. ✅ Application deployed
2. ☐ Configure custom domain
3. ☐ Set up monitoring alerts
4. ☐ Enable Google Cloud Marketplace integration
5. ☐ Configure backups and disaster recovery
6. ☐ Conduct security review
7. ☐ Load testing
8. ☐ Launch!

---

## Documentation

- **Full Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Deployment Checklist**: [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)
- **Marketplace Testing**: [docs/MARKETPLACE_TESTING.md](docs/MARKETPLACE_TESTING.md)
- **Architecture Overview**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (TODO)

---

## Support

- **Issues**: https://github.com/monkrus/ap2-expense-agent/issues
- **Discussions**: https://github.com/monkrus/ap2-expense-agent/discussions
- **Email**: support@ap2expense.com

---

## License

[Your License Here]

---

**Last Updated**: 2025-11-10
**Version**: 1.0.0
