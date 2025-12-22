# AP2 Expense Management Agent - Helm Chart

Official Helm chart for deploying AP2 Expense Management Agent to Kubernetes.

## TL;DR

```bash
helm install my-release ./ap2-expense \
  --set global.projectId=YOUR_PROJECT_ID \
  --set secrets.jwtSecretKey=YOUR_JWT_SECRET \
  --set secrets.jwtRefreshSecretKey=YOUR_REFRESH_SECRET \
  --set secrets.databaseUrl=postgresql://user:pass@host:5432/db
```

## Introduction

This chart deploys AP2 Expense Management Agent on a Kubernetes cluster using the Helm package manager.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PostgreSQL database (Cloud SQL recommended)
- PV provisioner support in the underlying infrastructure (optional)

## Installing the Chart

### Install from local directory

```bash
helm install my-release ./ap2-expense
```

### Install with custom values

```bash
helm install my-release ./ap2-expense -f my-values.yaml
```

### Install with inline values

```bash
helm install my-release ./ap2-expense \
  --set backend.replicaCount=5 \
  --set frontend.replicaCount=3 \
  --set ingress.hosts[0].host=expense.example.com
```

## Uninstalling the Chart

```bash
helm uninstall my-release
```

## Configuration

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.projectId` | Google Cloud Project ID | `YOUR_PROJECT_ID` |
| `global.region` | Google Cloud region | `us-central1` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `images.backend.repository` | Backend image repository | `us-central1-docker.pkg.dev/...` |
| `images.backend.tag` | Backend image tag | `latest` |
| `images.backend.pullPolicy` | Image pull policy | `IfNotPresent` |
| `images.frontend.repository` | Frontend image repository | `us-central1-docker.pkg.dev/...` |
| `images.frontend.tag` | Frontend image tag | `latest` |
| `images.frontend.pullPolicy` | Image pull policy | `IfNotPresent` |

### Backend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.replicaCount` | Number of backend replicas | `3` |
| `backend.resources.requests.cpu` | CPU request | `250m` |
| `backend.resources.requests.memory` | Memory request | `512Mi` |
| `backend.resources.limits.cpu` | CPU limit | `1000m` |
| `backend.resources.limits.memory` | Memory limit | `1Gi` |
| `backend.autoscaling.enabled` | Enable HPA | `true` |
| `backend.autoscaling.minReplicas` | Minimum replicas | `3` |
| `backend.autoscaling.maxReplicas` | Maximum replicas | `20` |

### Frontend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.resources.requests.cpu` | CPU request | `100m` |
| `frontend.resources.requests.memory` | Memory request | `128Mi` |
| `frontend.autoscaling.enabled` | Enable HPA | `true` |
| `frontend.autoscaling.minReplicas` | Minimum replicas | `2` |
| `frontend.autoscaling.maxReplicas` | Maximum replicas | `10` |

### Database Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `database.enabled` | Enable database configuration | `true` |
| `database.type` | Database type | `cloudsql` |
| `database.instanceConnectionName` | Cloud SQL connection name | `PROJECT:REGION:INSTANCE` |
| `database.databaseName` | Database name | `ap2_expense` |
| `database.username` | Database username | `ap2user` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `gce` |
| `ingress.hosts[0].host` | Hostname | `your-domain.com` |
| `tls.enabled` | Enable TLS | `true` |

### Secret Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.jwtSecretKey` | JWT secret key | `""` |
| `secrets.jwtRefreshSecretKey` | JWT refresh secret key | `""` |
| `secrets.databaseUrl` | Database connection string | `""` |
| `secrets.stripeSecretKey` | Stripe API key (optional) | `""` |

## Examples

### Production Deployment

```yaml
# production-values.yaml
global:
  projectId: "my-prod-project"
  region: "us-central1"

backend:
  replicaCount: 5
  autoscaling:
    minReplicas: 5
    maxReplicas: 30
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 2Gi

frontend:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 15

ingress:
  hosts:
    - host: expense.mycompany.com
      paths:
        - path: /api/*
          pathType: ImplementationSpecific
          backend:
            service:
              name: backend
              port: 8000
        - path: /*
          pathType: ImplementationSpecific
          backend:
            service:
              name: frontend
              port: 80

tls:
  managedCertificate:
    domains:
      - expense.mycompany.com
      - www.expense.mycompany.com

secrets:
  jwtSecretKey: "your-production-jwt-secret"
  jwtRefreshSecretKey: "your-production-refresh-secret"
  databaseUrl: "postgresql://user:pass@cloudsql-proxy:5432/ap2_expense"
  stripeSecretKey: "sk_live_..."

monitoring:
  enabled: true
```

Deploy:
```bash
helm install production ./ap2-expense -f production-values.yaml
```

### Development Deployment

```yaml
# dev-values.yaml
backend:
  replicaCount: 1
  autoscaling:
    enabled: false

frontend:
  replicaCount: 1
  autoscaling:
    enabled: false

ingress:
  enabled: false

database:
  instanceConnectionName: "dev-project:us-central1:ap2-dev-db"
```

Deploy:
```bash
helm install dev ./ap2-expense -f dev-values.yaml
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade my-release ./ap2-expense -f new-values.yaml

# Upgrade with new image version
helm upgrade my-release ./ap2-expense \
  --set images.backend.tag=v1.1.0 \
  --set images.frontend.tag=v1.1.0
```

## Rollback

```bash
# Rollback to previous version
helm rollback my-release

# Rollback to specific revision
helm rollback my-release 2
```

## Troubleshooting

### Check deployment status

```bash
helm status my-release
kubectl get pods -n default -l app.kubernetes.io/name=ap2-expense
```

### View logs

```bash
# Backend logs
kubectl logs -f -l app.kubernetes.io/component=backend

# Frontend logs
kubectl logs -f -l app.kubernetes.io/component=frontend
```

### Debug

```bash
# Dry run to see generated manifests
helm install my-release ./ap2-expense --dry-run --debug

# Template only
helm template my-release ./ap2-expense
```

## License

Copyright © 2025 Your Company
