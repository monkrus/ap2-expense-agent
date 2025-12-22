# CI Helm Deploy: Immutable Tags/Digests and Git SHA

This guide shows how to deploy the Helm chart with immutable image tags or digests from CI.

## Using Git SHA Tags

1. Build and push images tagged with the commit SHA:

```bash
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:$COMMIT_SHA -f Dockerfile.backend .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:$COMMIT_SHA

docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend:$COMMIT_SHA -f Dockerfile.frontend .
docker push us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend:$COMMIT_SHA
```

2. Helm upgrade with `gitSha` (overrides tags in chart):

```bash
helm upgrade --install ap2-expense helm/ap2-expense \
  --namespace ap2-expense --create-namespace \
  --set images.backend.repository=us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend \
  --set images.frontend.repository=us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend \
  --set gitSha=$COMMIT_SHA
```

## Using Digests

1. Resolve digests after pushing:

```bash
BACKEND_DIGEST=$(gcloud artifacts docker images describe us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend:$COMMIT_SHA --format='get(image_summary.digest)')
FRONTEND_DIGEST=$(gcloud artifacts docker images describe us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend:$COMMIT_SHA --format='get(image_summary.digest)')
```

2. Helm upgrade with digests (overrides tag):

```bash
helm upgrade --install ap2-expense helm/ap2-expense \
  --namespace ap2-expense --create-namespace \
  --set images.backend.repository=us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/backend \
  --set images.backend.digest=$BACKEND_DIGEST \
  --set images.frontend.repository=us-central1-docker.pkg.dev/$PROJECT_ID/ap2-expense/frontend \
  --set images.frontend.digest=$FRONTEND_DIGEST
```

Either approach ensures immutable deployments compatible with Marketplace submission.

