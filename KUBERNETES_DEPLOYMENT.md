# Kubernetes Deployment Guide - AP2 Expense Agent

Complete guide for deploying AP2 Expense Agent to Google Kubernetes Engine (GKE).

## Prerequisites

### Required Tools

```bash
# Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# kubectl
gcloud components install kubectl

# Docker
# Install from: https://docs.docker.com/get-docker/
```

### Google Cloud Setup

```bash
# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    container.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com \
    sqladmin.googleapis.com \
    servicenetworking.googleapis.com
```

---

## Step 1: Create GKE Cluster

### Option A: Standard Cluster (Recommended for Production)

```bash
gcloud container clusters create ap2-expense-cluster \
    --zone=us-central1-a \
    --num-nodes=3 \
    --machine-type=n1-standard-2 \
    --enable-autoscaling \
    --min-nodes=3 \
    --max-nodes=10 \
    --enable-autorepair \
    --enable-autoupgrade \
    --enable-ip-alias \
    --network=default \
    --subnetwork=default \
    --addons=HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver
```

### Option B: Autopilot Cluster (Managed, Simpler)

```bash
gcloud container clusters create-auto ap2-expense-cluster \
    --region=us-central1
```

---

## Step 2: Configure Cloud SQL (PostgreSQL)

```bash
# Create Cloud SQL instance
gcloud sql instances create ap2-expense-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_SECURE_PASSWORD \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00

# Create database
gcloud sql databases create ap2_expense \
    --instance=ap2-expense-db

# Create database user
gcloud sql users create ap2user \
    --instance=ap2-expense-db \
    --password=YOUR_SECURE_PASSWORD

# Get connection string
gcloud sql instances describe ap2-expense-db --format="value(connectionName)"
# Output: PROJECT_ID:us-central1:ap2-expense-db
```

---

## Step 3: Build and Push Docker Images

### Update Configuration

```bash
# Make scripts executable
chmod +x build-and-push.sh deploy-k8s.sh

# Build and push images
./build-and-push.sh YOUR_PROJECT_ID v1.0.0
```

Or manually:

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Create repository
gcloud artifacts repositories create ap2-expense \
    --repository-format=docker \
    --location=us-central1 \
    --description="AP2 Expense Management Agent"

# Build backend
cd backend
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:v1.0.0 .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:v1.0.0

# Build frontend
cd ../frontend
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend:v1.0.0 .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend:v1.0.0
```

---

## Step 4: Configure Kubernetes Secrets

### Update secrets.yaml

```bash
# Generate JWT secrets
openssl rand -hex 32  # For JWT_SECRET_KEY
openssl rand -hex 32  # For JWT_REFRESH_SECRET_KEY

# Edit secrets.yaml with your actual secrets
nano k8s/secrets.yaml
```

**Required secrets:**
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: JWT signing key
- `JWT_REFRESH_SECRET_KEY`: JWT refresh token key
- `STRIPE_SECRET_KEY`: Stripe API key (optional)

### Use Google Secret Manager (Recommended)

```bash
# Create secrets in Secret Manager
echo -n "postgresql://user:pass@host:5432/db" | \
    gcloud secrets create database-url --data-file=-

# Reference in Kubernetes using External Secrets Operator
# See: https://external-secrets.io/
```

---

## Step 5: Update Kubernetes Manifests

### Replace placeholders in all k8s/*.yaml files:

```bash
# Replace YOUR_PROJECT_ID with your actual project ID
export PROJECT_ID="your-project-id"

# macOS/Linux
find k8s/ -type f -name "*.yaml" -exec sed -i '' "s/YOUR_PROJECT_ID/$PROJECT_ID/g" {} +

# Or manually edit:
# - k8s/backend-deployment.yaml (line 38)
# - k8s/frontend-deployment.yaml (line 38)
# - k8s/serviceaccount.yaml (line 9)
# - k8s/ingress.yaml (update domain)
```

---

## Step 6: Deploy to Kubernetes

### Automated Deployment

```bash
./deploy-k8s.sh YOUR_PROJECT_ID ap2-expense-cluster us-central1-a
```

### Manual Deployment

```bash
# Get cluster credentials
gcloud container clusters get-credentials ap2-expense-cluster \
    --zone=us-central1-a

# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

---

## Step 7: Verify Deployment

### Check Pods

```bash
kubectl get pods -n ap2-expense

# Expected output:
# NAME                        READY   STATUS    RESTARTS   AGE
# backend-xxxxx-xxxxx         1/1     Running   0          2m
# backend-xxxxx-xxxxx         1/1     Running   0          2m
# backend-xxxxx-xxxxx         1/1     Running   0          2m
# frontend-xxxxx-xxxxx        1/1     Running   0          2m
# frontend-xxxxx-xxxxx        1/1     Running   0          2m
```

### Check Services

```bash
kubectl get svc -n ap2-expense

# Expected output:
# NAME               TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
# backend-service    ClusterIP   10.x.x.x       <none>        8000/TCP   2m
# frontend-service   ClusterIP   10.x.x.x       <none>        80/TCP     2m
```

### Check Ingress

```bash
kubectl get ingress -n ap2-expense

# Wait for external IP to be assigned (can take 5-10 minutes)
kubectl get ingress -n ap2-expense -w
```

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n ap2-expense

# Frontend logs
kubectl logs -f deployment/frontend -n ap2-expense

# Get logs from specific pod
kubectl logs <pod-name> -n ap2-expense
```

---

## Step 8: Configure DNS

Once Ingress has an external IP:

```bash
# Get the IP
kubectl get ingress ap2-expense-ingress -n ap2-expense \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Add DNS A record:
- **Name**: `@` or `your-subdomain`
- **Type**: `A`
- **Value**: `<INGRESS_IP>`
- **TTL**: `300` (5 minutes)

---

## Step 9: Configure SSL Certificate

### Option A: Google-Managed Certificate

```bash
# Create managed certificate
cat <<EOF | kubectl apply -f -
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: ap2-expense-cert
  namespace: ap2-expense
spec:
  domains:
    - your-domain.com
    - www.your-domain.com
EOF

# Check certificate status
kubectl describe managedcertificate ap2-expense-cert -n ap2-expense
```

### Option B: Let's Encrypt with cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: gce
EOF
```

---

## Monitoring and Maintenance

### Scale Deployments

```bash
# Manual scaling
kubectl scale deployment backend --replicas=5 -n ap2-expense

# HPA will auto-scale based on CPU/memory
kubectl get hpa -n ap2-expense
```

### Update Deployment

```bash
# Build new version
./build-and-push.sh YOUR_PROJECT_ID v1.1.0

# Update deployment
kubectl set image deployment/backend \
    backend=us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:v1.1.0 \
    -n ap2-expense

# Check rollout status
kubectl rollout status deployment/backend -n ap2-expense

# Rollback if needed
kubectl rollout undo deployment/backend -n ap2-expense
```

### Database Migrations

```bash
# Run migrations manually
kubectl exec -it deployment/backend -n ap2-expense -- \
    alembic upgrade head
```

### Backup and Restore

```bash
# Backup Cloud SQL
gcloud sql backups create --instance=ap2-expense-db

# List backups
gcloud sql backups list --instance=ap2-expense-db

# Restore from backup
gcloud sql backups restore BACKUP_ID \
    --backup-instance=ap2-expense-db \
    --backup-id=BACKUP_ID
```

---

## Troubleshooting

### Pods not starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n ap2-expense

# Common issues:
# - Image pull errors: Check image name and permissions
# - CrashLoopBackOff: Check logs for application errors
# - Pending: Check resource availability
```

### Connection errors

```bash
# Check service endpoints
kubectl get endpoints -n ap2-expense

# Test backend service internally
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n ap2-expense -- \
    curl http://backend-service:8000/health
```

### Database connection issues

```bash
# Check secrets
kubectl get secret ap2-expense-secrets -n ap2-expense -o yaml

# Verify Cloud SQL connection
kubectl exec -it deployment/backend -n ap2-expense -- \
    pg_isready -h <cloudsql-host> -p 5432 -U ap2user
```

---

## Cost Optimization

### Recommendations

1. **Use Preemptible Nodes** (for non-prod):
   ```bash
   --preemptible
   ```

2. **Enable Cluster Autoscaler**:
   ```bash
   --enable-autoscaling --min-nodes=1 --max-nodes=5
   ```

3. **Use Spot VMs** (80% discount):
   ```bash
   --spot
   ```

4. **Right-size resources**:
   - Review metrics: `kubectl top pods -n ap2-expense`
   - Adjust requests/limits in deployment.yaml

---

## Production Checklist

- [ ] Cloud SQL backups automated
- [ ] SSL certificate configured
- [ ] DNS configured
- [ ] Monitoring setup (Cloud Monitoring)
- [ ] Alerting configured
- [ ] Secrets in Secret Manager (not in Git)
- [ ] Network policies configured
- [ ] Resource limits set
- [ ] HPA configured
- [ ] Disaster recovery plan documented
- [ ] Load testing performed
- [ ] Security scanning enabled

---

## Next Steps

1. **Setup Monitoring**: See `MONITORING_SETUP.md`
2. **Configure Billing**: See `BILLING_INTEGRATION.md`
3. **Create Helm Chart**: See `HELM_CHART.md`
4. **Marketplace Listing**: See `MARKETPLACE_READINESS.md`

---

## Support

For issues:
- Check logs: `kubectl logs -f deployment/backend -n ap2-expense`
- Check events: `kubectl get events -n ap2-expense --sort-by='.lastTimestamp'`
- GKE docs: https://cloud.google.com/kubernetes-engine/docs
