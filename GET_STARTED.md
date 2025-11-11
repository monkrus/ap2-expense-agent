# 🚀 Get Started - 5 Minutes to First Deployment

## Choose Your Path

### Path 1: Cloud Run (Fastest - 15 minutes total)
**Best for**: Getting started quickly, proof of concept, low traffic

### Path 2: Google Kubernetes Engine (Production - 45 minutes total)
**Best for**: Production workloads, full control, scalability

### Path 3: Helm on GKE (Enterprise - 45 minutes total)
**Best for**: GitOps workflows, enterprise deployments

---

## Prerequisites (2 minutes)

```bash
# Check you have these installed
gcloud --version    # Google Cloud SDK
docker --version    # Docker
git --version       # Git

# Not installed? See: https://cloud.google.com/sdk/docs/install
```

---

## Step 1: Clone & Configure (3 minutes)

```bash
# Clone repository
git clone https://github.com/monkrus/ap2-expense-agent
cd ap2-expense-agent

# Copy environment template
cp .env.deployment.template .env.deployment

# Edit with your values (REQUIRED)
nano .env.deployment
```

**Minimum required values**:
- `GCP_PROJECT_ID="your-actual-project-id"`
- `APP_DOMAIN="your-domain.com"` (or `"test.example.com"` for testing)
- `NOTIFICATION_EMAIL="your-email@company.com"`

```bash
# Load environment
source .env.deployment
```

---

## Step 2: Validate (1 minute)

```bash
# Check everything is configured correctly
chmod +x scripts/*.sh
./scripts/pre-deployment-check.sh
```

✅ If all checks pass → proceed to Step 3
⚠️ If warnings → review but can proceed
❌ If errors → fix issues and re-run

---

## Step 3A: Deploy to Cloud Run (10 minutes)

```bash
# One command to setup all GCP resources
./scripts/setup-gcp-project.sh

# Build and deploy (takes ~10 minutes)
gcloud builds submit --config=cloudbuild.yaml

# Get URLs
echo "Backend: $(gcloud run services describe ap2-expense-backend --region=us-central1 --format='value(status.url)')"
echo "Frontend: $(gcloud run services describe ap2-expense-frontend --region=us-central1 --format='value(status.url)')"
```

**Done!** Your application is live 🎉

---

## Step 3B: Deploy to GKE (40 minutes)

```bash
# Setup GCP resources (15 minutes)
./scripts/setup-gcp-project.sh

# Create GKE cluster (10 minutes)
./scripts/create-gke-cluster.sh

# Update configuration files
./scripts/update-k8s-configs.sh

# Build and push images (5 minutes)
docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest -f Dockerfile.backend .
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest

docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest -f Dockerfile.frontend .
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest

# Deploy to Kubernetes (5 minutes)
kubectl apply -f k8s/

# Wait for ingress IP (5 minutes)
kubectl get ingress -n ap2-expense -w
```

**Done!** Check status:
```bash
kubectl get pods -n ap2-expense
kubectl get ingress -n ap2-expense
```

---

## Step 4: Verify Deployment (2 minutes)

### Test Health Endpoint

**Cloud Run**:
```bash
BACKEND_URL=$(gcloud run services describe ap2-expense-backend --region=us-central1 --format='value(status.url)')
curl $BACKEND_URL/health
```

**GKE**:
```bash
INGRESS_IP=$(kubectl get ingress ap2-expense-ingress -n ap2-expense -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$INGRESS_IP/api/health
```

**Expected response**:
```json
{"status":"healthy","service":"AP2 Expense Management Agent"}
```

### Test Frontend

Open in browser:
- Cloud Run: Use frontend URL from Step 3A
- GKE: `http://<INGRESS_IP>/`

---

## Step 5: Run Migrations (1 minute)

```bash
# Get backend pod (GKE only)
BACKEND_POD=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -n ap2-expense -- alembic upgrade head

# Or use helper script
./scripts/manage-migrations.sh upgrade
```

---

## Step 6: Create Admin User (1 minute)

```bash
# Register admin user via API
curl -X POST $BACKEND_URL/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "ChangeThisPassword123!",
    "username": "admin",
    "full_name": "Admin User"
  }'

# Promote to admin (GKE)
kubectl exec -it $BACKEND_POD -n ap2-expense -- python -c "
from src.database import SessionLocal
from src.models import User
db = SessionLocal()
user = db.query(User).filter(User.email == 'admin@yourcompany.com').first()
user.role = 'admin'
db.commit()
print('✅ User promoted to admin')
"
```

---

## ✅ You're Done!

### What You Have Now

- ✅ Production-ready deployment on GCP
- ✅ Secure Cloud SQL database with backups
- ✅ All secrets in Secret Manager
- ✅ Monitoring and alerting configured
- ✅ Auto-scaling enabled
- ✅ Disaster recovery ready

### Next Steps

1. **Configure Custom Domain** (optional)
   ```bash
   # For Cloud Run
   gcloud run domain-mappings create \
     --service=ap2-expense-backend \
     --domain=api.your-domain.com \
     --region=us-central1
   ```

2. **Set Up Monitoring**
   - Go to: https://console.cloud.google.com/monitoring
   - Create notification channels
   - Enable alert policies

3. **Test Complete Workflow**
   - Register user
   - Create organization
   - Create expense
   - Upload receipt
   - Generate report

4. **Enable Marketplace Integration** (if selling on GCP Marketplace)
   - See: [`docs/MARKETPLACE_TESTING.md`](docs/MARKETPLACE_TESTING.md)

---

## Common Issues & Quick Fixes

### Issue: "Permission denied"

```bash
# Fix: Grant yourself permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@gmail.com" \
  --role="roles/owner"
```

### Issue: "API not enabled"

```bash
# Fix: Re-run setup script
./scripts/setup-gcp-project.sh
```

### Issue: "Image not found"

```bash
# Fix: Build and push images
gcloud builds submit --config=cloudbuild.yaml
```

### Issue: "Pod not starting"

```bash
# Check logs
kubectl logs -l app.kubernetes.io/component=backend -n ap2-expense

# Common causes:
# - Secrets not accessible → Check Workload Identity
# - Database connection failed → Check Cloud SQL Proxy
# - Image pull error → Check if image exists in GCR
```

---

## Need Help?

### Documentation

- 📚 **Full Guide**: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- ✅ **Checklist**: [`docs/DEPLOYMENT_CHECKLIST.md`](docs/DEPLOYMENT_CHECKLIST.md)
- 🧪 **Testing**: [`docs/MARKETPLACE_TESTING.md`](docs/MARKETPLACE_TESTING.md)
- 📝 **Summary**: [`DEPLOYMENT_COMPLETE.md`](DEPLOYMENT_COMPLETE.md)

### Scripts

All scripts have built-in help:
```bash
./scripts/setup-gcp-project.sh --help
./scripts/manage-migrations.sh --help
./scripts/disaster-recovery.sh --help
```

### Troubleshooting

1. Run pre-deployment check: `./scripts/pre-deployment-check.sh`
2. Check script logs in `/tmp/`
3. Review GCP logs in Cloud Console
4. See troubleshooting sections in documentation

---

## Cleanup (if needed)

### Delete Cloud Run Deployment

```bash
gcloud run services delete ap2-expense-backend --region=us-central1
gcloud run services delete ap2-expense-frontend --region=us-central1
```

### Delete GKE Deployment

```bash
kubectl delete namespace ap2-expense
gcloud container clusters delete ap2-expense-cluster --region=us-central1
```

### Delete All GCP Resources

```bash
# WARNING: This deletes EVERYTHING
./scripts/cleanup-all.sh  # (create this if needed)

# Or manually:
gcloud sql instances delete ap2-expense-db
gsutil -m rm -r gs://$GCP_PROJECT_ID-ap2-expense-*
gcloud kms keyrings list --location=us-central1  # (keyrings can't be deleted)
# etc.
```

---

## Estimated Costs

### Development/Testing

- Cloud Run: **~$5-10/month**
- GKE: **~$150-200/month**

### Production

- Cloud Run: **~$145-230/month**
- GKE: **~$405-655/month**

💡 **Tip**: Use Cloud Run for development, GKE for production

---

## Time Investment

| Task | Cloud Run | GKE |
|------|-----------|-----|
| Setup | 15 min | 45 min |
| Learning | 1 hour | 2-3 hours |
| Ongoing | 1 hour/week | 2-3 hours/week |

---

**Ready? Let's deploy!** 🚀

```bash
source .env.deployment
./scripts/pre-deployment-check.sh
./scripts/setup-gcp-project.sh
gcloud builds submit --config=cloudbuild.yaml
```

---

**Last Updated**: 2025-11-10
**Version**: 1.0
**Next Review**: After first deployment feedback
