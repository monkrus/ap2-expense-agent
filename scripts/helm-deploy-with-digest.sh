#!/usr/bin/env bash
set -euo pipefail

# Resolve image digests for backend and frontend and deploy via Helm.

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <PROJECT_ID> <NAMESPACE> [RELEASE=ap2-expense]" >&2
  exit 1
fi

PROJECT_ID="$1"
NAMESPACE="$2"
RELEASE="${3:-ap2-expense}"

BACKEND_REPO="us-central1-docker.pkg.dev/${PROJECT_ID}/ap2-expense/backend"
FRONTEND_REPO="us-central1-docker.pkg.dev/${PROJECT_ID}/ap2-expense/frontend"

if [[ -z "${COMMIT_SHA:-}" ]]; then
  echo "COMMIT_SHA not set; falling back to latest tags may be disallowed." >&2
  exit 1
fi

BACKEND_DIGEST=$(gcloud artifacts docker images describe "${BACKEND_REPO}:${COMMIT_SHA}" --format='get(image_summary.digest)')
FRONTEND_DIGEST=$(gcloud artifacts docker images describe "${FRONTEND_REPO}:${COMMIT_SHA}" --format='get(image_summary.digest)')

helm upgrade --install "${RELEASE}" helm/ap2-expense \
  -n "${NAMESPACE}" --create-namespace \
  --set global.projectId="${PROJECT_ID}" \
  --set images.backend.repository="${BACKEND_REPO}" \
  --set images.backend.digest="${BACKEND_DIGEST}" \
  --set images.frontend.repository="${FRONTEND_REPO}" \
  --set images.frontend.digest="${FRONTEND_DIGEST}"

echo "Deployed ${RELEASE} with backend@${BACKEND_DIGEST} and frontend@${FRONTEND_DIGEST}"

