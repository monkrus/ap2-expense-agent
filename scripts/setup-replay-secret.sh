#!/usr/bin/env bash
# Upload Marketplace webhook replay service account key to Secret Manager.

set -euo pipefail

GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
SECRET_NAME="${REPLAY_SECRET_NAME:-marketplace-webhook-replay-key}"
KEY_FILE="${REPLAY_KEY_FILE:-marketplace-api-key.json}"

if [[ -z "${GCP_PROJECT_ID}" ]]; then
  echo "GCP_PROJECT_ID is required" >&2
  exit 1
fi

if [[ ! -f "${KEY_FILE}" ]]; then
  echo "Key file ${KEY_FILE} not found" >&2
  exit 1
fi

if gcloud secrets describe "${SECRET_NAME}" --project "${GCP_PROJECT_ID}" >/dev/null 2>&1; then
  echo "Secret ${SECRET_NAME} exists; adding new version"
else
  echo "Creating secret ${SECRET_NAME}"
  gcloud secrets create "${SECRET_NAME}" --replication-policy=automatic --project "${GCP_PROJECT_ID}"
fi

gcloud secrets versions add "${SECRET_NAME}" --data-file="${KEY_FILE}" --project "${GCP_PROJECT_ID}"

echo "Secret ${SECRET_NAME} updated."
echo "Grant runtime SA access if needed:"
echo "  gcloud secrets add-iam-policy-binding ${SECRET_NAME} --member=\"serviceAccount:ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com\" --role=\"roles/secretmanager.secretAccessor\" --project ${GCP_PROJECT_ID}"
