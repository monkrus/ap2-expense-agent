#!/bin/bash

# Google Cloud Setup Script for AP2 Expense Agent
# Project ID: ap2-expense-agent

set -e

PROJECT_ID="ap2-expense-agent"
REGION="us-central1"
SERVICE_ACCOUNT_NAME="github-actions-deploy"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up Google Cloud project: $PROJECT_ID"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required Google Cloud APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com

echo "APIs enabled successfully!"

# Create service account for GitHub Actions
echo "Creating service account for GitHub Actions deployment..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="GitHub Actions Deployment Service Account" \
  --description="Service account used by GitHub Actions to deploy to Cloud Run"

# Grant necessary roles to service account
echo "Granting IAM roles to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.admin"

# Create and download service account key
echo "Creating service account key..."
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
echo "Service Account Key saved to: github-actions-key.json"
echo ""
echo "NEXT STEPS:"
echo "1. Copy the contents of github-actions-key.json"
echo "2. Go to GitHub repository Settings > Secrets and variables > Actions"
echo "3. Add the following secrets:"
echo "   - GCP_SA_KEY: (paste the entire contents of github-actions-key.json)"
echo "   - GCP_PROJECT_ID: $PROJECT_ID"
echo "   - JWT_SECRET_KEY: (generate a secure random string)"
echo "   - DATABASE_URL: (your PostgreSQL connection string)"
echo ""
echo "4. IMPORTANT: Delete github-actions-key.json after copying to GitHub"
echo "   rm github-actions-key.json"
echo ""
