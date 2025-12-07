#!/usr/bin/env bash
# Provision Cloud Run Job and Cloud Scheduler trigger for DLQ depth checks.
# Requires gcloud auth; ensure project/region are set.

set -euo pipefail

GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE="${DLQ_IMAGE:-gcr.io/${GCP_PROJECT_ID}/ap2-backend:latest}"
JOB_NAME="${DLQ_JOB_NAME:-dlq-checker}"
RUNTIME_SA="${RUNTIME_SA:-ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com}"
SCHEDULER_SA="${SCHEDULER_SA:-cloud-scheduler-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com}"
THRESHOLD="${DLQ_THRESHOLD:-0}"

if [[ -z "${GCP_PROJECT_ID}" ]]; then
  echo "GCP_PROJECT_ID is required" >&2
  exit 1
fi

echo "Creating/Updating Cloud Run Job ${JOB_NAME} in ${GCP_PROJECT_ID}/${GCP_REGION}"
if gcloud run jobs describe "${JOB_NAME}" --region "${GCP_REGION}" --project "${GCP_PROJECT_ID}" >/dev/null 2>&1; then
  ACTION=update
else
  ACTION=create
fi

gcloud run jobs ${ACTION} "${JOB_NAME}" \
  --image="${IMAGE}" \
  --region="${GCP_REGION}" \
  --command="python" \
  --args="scripts/check_dlq_counts.py","--threshold","${THRESHOLD}" \
  --service-account="${RUNTIME_SA}" \
  --max-retries=0 \
  --project "${GCP_PROJECT_ID}"

# Cloud Run Job execution endpoint for Scheduler to trigger
RUN_URI="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${JOB_NAME}:run"

echo "Creating/Updating Cloud Scheduler job dlq-check (*/5 minutes)"
if gcloud scheduler jobs describe dlq-check --project "${GCP_PROJECT_ID}" >/dev/null 2>&1; then
  SJ_ACTION=update
else
  SJ_ACTION=create
fi

gcloud scheduler jobs ${SJ_ACTION} http dlq-check \
  --schedule="*/5 * * * *" \
  --uri="${RUN_URI}" \
  --http-method=POST \
  --oidc-service-account-email="${SCHEDULER_SA}" \
  --project "${GCP_PROJECT_ID}"

echo "DLQ monitoring job configured. Add monitoring/alerts on dlq-check failures."
