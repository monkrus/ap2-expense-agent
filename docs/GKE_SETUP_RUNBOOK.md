# GKE Setup Runbook: Pub/Sub OIDC, Secret Manager CSI, Cloud SQL

This runbook describes enabling Pub/Sub push with Google-signed OIDC tokens, wiring Secret Manager CSI, and configuring Cloud SQL connector on GKE for AP2 Expense.

## 1) Pub/Sub Push with OIDC -> `/api/webhooks/gcp/events`

- Create topic and push subscription:

```bash
gcloud pubsub topics create ap2-marketplace-events --project $PROJECT_ID
gcloud pubsub subscriptions create ap2-marketplace-sub \
  --topic ap2-marketplace-events \
  --push-endpoint=https://YOUR_DOMAIN/api/webhooks/gcp/events \
  --push-auth-service-account=pubsub-push@$PROJECT_ID.iam.gserviceaccount.com \
  --push-auth-token-audience=https://YOUR_DOMAIN/api/webhooks/gcp/events \
  --project $PROJECT_ID
```

- Set backend env `GCP_WEBHOOK_AUDIENCE` to the push endpoint URL.
- Ensure the service account has `roles/iam.serviceAccountTokenCreator` to mint OIDC tokens.

## 2) Secret Manager CSI driver

- Enable the GKE add-on or install the CSI driver.
- Create `SecretProviderClass` (see `k8s/secretmanager-csi.yaml`).
- Mount CSI volume and/or use synced K8s secret `ap2-expense-secrets-gsm` in the backend Deployment.
- Grant Workload Identity service account permission to access GSM secrets:

```bash
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member=serviceAccount:ap2-expense@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project $PROJECT_ID
```

Repeat for other secrets used.

## 3) Cloud SQL connector v2

- Add sidecar `gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.x` with args:
  `--structured-logs --port=5432 --address=0.0.0.0 PROJECT:REGION:INSTANCE`.
- Connect with `postgresql://USER:PASSWORD@127.0.0.1:5432/DB?sslmode=disable`.
- Prefer Workload Identity; use SA key mount only if required (see comments in `k8s/backend-deployment.yaml`).

## 4) Ingress and TLS

- Use GCE ingress with managed certificate per `helm/ap2-expense/values.yaml` or templates.
- Validate HTTPS end-to-end before enabling Pub/Sub push.

## 5) Validation Checklist

- `/health` returns 200.
- `/api/webhooks/gcp/health` returns 200.
- Pub/Sub push to `/api/webhooks/gcp/events` returns 200 for test events.
- Logs include `logging.googleapis.com/trace` with correct `traceId`/`spanId`.
- `/metrics` exposes Prometheus metrics; HPA targets are met under load.

