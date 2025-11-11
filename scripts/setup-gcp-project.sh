#!/bin/bash

###############################################################################
# AP2 Expense Agent - GCP Project Setup Script
#
# This script automates the setup of GCP resources required for deployment.
# Run this script BEFORE deploying the application.
#
# Prerequisites:
# - gcloud CLI installed and configured
# - Appropriate GCP permissions (Owner or equivalent roles)
# - Environment variables set (source .env.deployment first)
###############################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_env_vars() {
    log_info "Checking required environment variables..."

    local required_vars=(
        "GCP_PROJECT_ID"
        "GCP_REGION"
        "GCP_ZONE"
        "SA_NAME"
        "DB_INSTANCE_NAME"
        "DB_NAME"
        "DB_USER"
        "KMS_KEYRING"
        "KMS_KEY"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_error "Please source .env.deployment file or set these variables manually"
        exit 1
    fi

    log_success "All required environment variables are set"
}

# Set the active GCP project
set_project() {
    log_info "Setting active GCP project to: $GCP_PROJECT_ID"
    gcloud config set project "$GCP_PROJECT_ID"
    log_success "Project set successfully"
}

# Enable required GCP APIs
enable_apis() {
    log_info "Enabling required GCP APIs (this may take a few minutes)..."

    local apis=(
        "container.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "cloudkms.googleapis.com"
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "storage-api.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudcommerceprocurement.googleapis.com"
        "compute.googleapis.com"
        "servicenetworking.googleapis.com"
        "vpcaccess.googleapis.com"
    )

    gcloud services enable "${apis[@]}" --project="$GCP_PROJECT_ID"

    log_success "All required APIs enabled"
}

# Create service account
create_service_account() {
    log_info "Creating service account: $SA_NAME"

    # Check if service account already exists
    if gcloud iam service-accounts describe "${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
        --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_warning "Service account already exists, skipping creation"
        return 0
    fi

    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="AP2 Expense Agent Service Account" \
        --description="Service account for AP2 Expense Agent application" \
        --project="$GCP_PROJECT_ID"

    log_success "Service account created"
}

# Grant IAM roles to service account
grant_iam_roles() {
    log_info "Granting IAM roles to service account..."

    local sa_email="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

    local roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/cloudkms.cryptoOperator"
        "roles/storage.objectAdmin"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
        "roles/cloudtrace.agent"
    )

    for role in "${roles[@]}"; do
        log_info "  Granting role: $role"
        gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="$role" \
            --condition=None \
            --quiet
    done

    log_success "IAM roles granted successfully"
}

# Create Cloud SQL instance
create_cloudsql_instance() {
    log_info "Creating Cloud SQL instance: $DB_INSTANCE_NAME"

    # Check if instance already exists
    if gcloud sql instances describe "$DB_INSTANCE_NAME" \
        --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_warning "Cloud SQL instance already exists, skipping creation"
        return 0
    fi

    log_info "Creating PostgreSQL 15 instance (this will take 5-10 minutes)..."

    gcloud sql instances create "$DB_INSTANCE_NAME" \
        --database-version=POSTGRES_15 \
        --tier=db-custom-2-8192 \
        --region="$GCP_REGION" \
        --storage-type=SSD \
        --storage-size=100GB \
        --storage-auto-increase \
        --backup \
        --backup-start-time=03:00 \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=4 \
        --enable-point-in-time-recovery \
        --availability-type=REGIONAL \
        --network=default \
        --project="$GCP_PROJECT_ID"

    log_success "Cloud SQL instance created"
}

# Create database and user
setup_database() {
    log_info "Setting up database and user..."

    # Generate a secure random password if not provided
    if [ -z "${DB_PASSWORD:-}" ]; then
        log_info "Generating secure database password..."
        DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        export DB_PASSWORD
        log_warning "Database password: $DB_PASSWORD"
        log_warning "Save this password! It will be stored in Secret Manager."
    fi

    # Create database
    log_info "Creating database: $DB_NAME"
    gcloud sql databases create "$DB_NAME" \
        --instance="$DB_INSTANCE_NAME" \
        --project="$GCP_PROJECT_ID" || log_warning "Database may already exist"

    # Create user
    log_info "Creating database user: $DB_USER"
    gcloud sql users create "$DB_USER" \
        --instance="$DB_INSTANCE_NAME" \
        --password="$DB_PASSWORD" \
        --project="$GCP_PROJECT_ID" || log_warning "User may already exist"

    log_success "Database and user configured"
}

# Create KMS keyring and key
setup_kms() {
    log_info "Setting up Cloud KMS for cryptographic signing..."

    # Create keyring
    log_info "Creating KMS keyring: $KMS_KEYRING"
    gcloud kms keyrings create "$KMS_KEYRING" \
        --location="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" 2>/dev/null || log_warning "Keyring may already exist"

    # Create asymmetric signing key
    log_info "Creating KMS signing key: $KMS_KEY"
    gcloud kms keys create "$KMS_KEY" \
        --keyring="$KMS_KEYRING" \
        --location="$GCP_REGION" \
        --purpose=asymmetric-signing \
        --default-algorithm=rsa-sign-pkcs1-4096-sha512 \
        --protection-level=software \
        --project="$GCP_PROJECT_ID" 2>/dev/null || log_warning "Key may already exist"

    # Grant service account access to KMS key
    local sa_email="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
    gcloud kms keys add-iam-policy-binding "$KMS_KEY" \
        --keyring="$KMS_KEYRING" \
        --location="$GCP_REGION" \
        --member="serviceAccount:$sa_email" \
        --role="roles/cloudkms.cryptoOperator" \
        --project="$GCP_PROJECT_ID" \
        --quiet

    log_success "Cloud KMS configured"
}

# Create Secret Manager secrets
setup_secrets() {
    log_info "Setting up Secret Manager secrets..."

    local sa_email="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

    # Function to create or update a secret
    create_secret() {
        local secret_name=$1
        local secret_value=$2

        if gcloud secrets describe "$secret_name" --project="$GCP_PROJECT_ID" &>/dev/null; then
            log_warning "Secret '$secret_name' already exists, adding new version"
            echo -n "$secret_value" | gcloud secrets versions add "$secret_name" \
                --data-file=- \
                --project="$GCP_PROJECT_ID"
        else
            log_info "Creating secret: $secret_name"
            echo -n "$secret_value" | gcloud secrets create "$secret_name" \
                --data-file=- \
                --replication-policy="automatic" \
                --project="$GCP_PROJECT_ID"
        fi

        # Grant service account access
        gcloud secrets add-iam-policy-binding "$secret_name" \
            --member="serviceAccount:$sa_email" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$GCP_PROJECT_ID" \
            --quiet
    }

    # Generate JWT secrets if not provided
    if [ -z "${JWT_SECRET:-}" ]; then
        JWT_SECRET=$(openssl rand -hex 32)
        export JWT_SECRET
        log_info "Generated JWT secret"
    fi

    if [ -z "${JWT_REFRESH_SECRET:-}" ]; then
        JWT_REFRESH_SECRET=$(openssl rand -hex 32)
        export JWT_REFRESH_SECRET
        log_info "Generated JWT refresh secret"
    fi

    # Create secrets
    create_secret "database-password" "$DB_PASSWORD"
    create_secret "jwt-secret-key" "$JWT_SECRET"
    create_secret "jwt-refresh-secret-key" "$JWT_REFRESH_SECRET"

    # Create placeholder for Stripe key (optional)
    if [ -n "${STRIPE_SECRET_KEY:-}" ]; then
        create_secret "stripe-secret-key" "$STRIPE_SECRET_KEY"
    else
        create_secret "stripe-secret-key" "sk_test_placeholder"
        log_warning "Created placeholder Stripe secret - update with real key later"
    fi

    log_success "Secret Manager configured"
}

# Create Cloud Storage buckets
setup_storage() {
    log_info "Setting up Cloud Storage buckets..."

    local bucket_name="${GCP_PROJECT_ID}-ap2-expense-receipts"

    # Create receipts bucket
    if gsutil ls -b "gs://$bucket_name" &>/dev/null; then
        log_warning "Bucket already exists: $bucket_name"
    else
        log_info "Creating bucket: $bucket_name"
        gsutil mb -p "$GCP_PROJECT_ID" -l "$GCP_REGION" -b on "gs://$bucket_name"

        # Set lifecycle policy to delete old files after 365 days
        cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle.json "gs://$bucket_name"
        rm /tmp/lifecycle.json

        # Grant service account access
        local sa_email="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
        gsutil iam ch "serviceAccount:$sa_email:objectAdmin" "gs://$bucket_name"
    fi

    log_success "Cloud Storage configured"
}

# Reserve static IP address
reserve_static_ip() {
    log_info "Reserving static IP address for ingress..."

    local ip_name="ap2-expense-ip"

    if gcloud compute addresses describe "$ip_name" \
        --global \
        --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_warning "Static IP already exists"
        local ip_address=$(gcloud compute addresses describe "$ip_name" --global --project="$GCP_PROJECT_ID" --format="value(address)")
        log_info "Static IP address: $ip_address"
    else
        gcloud compute addresses create "$ip_name" \
            --global \
            --ip-version=IPV4 \
            --project="$GCP_PROJECT_ID"

        local ip_address=$(gcloud compute addresses describe "$ip_name" --global --project="$GCP_PROJECT_ID" --format="value(address)")
        log_success "Static IP reserved: $ip_address"
        log_warning "Configure your DNS to point to: $ip_address"
    fi
}

# Create notification channel for alerts
setup_monitoring() {
    log_info "Setting up monitoring and alerting..."

    local notification_email="${NOTIFICATION_EMAIL:-ops@example.com}"

    log_info "Creating email notification channel for: $notification_email"

    # Note: This requires the monitoring API and proper formatting
    # Users should manually create notification channels via console or update alert yamls
    log_warning "Please create notification channels manually in Cloud Console:"
    log_warning "  1. Go to Monitoring > Alerting > Notification channels"
    log_warning "  2. Create an email channel for: $notification_email"
    log_warning "  3. Update monitoring/alerts/alert-policies.yaml with the channel ID"
}

# Print summary
print_summary() {
    echo ""
    log_success "========================================="
    log_success "GCP Project Setup Complete!"
    log_success "========================================="
    echo ""
    log_info "Project: $GCP_PROJECT_ID"
    log_info "Region: $GCP_REGION"
    log_info "Service Account: ${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
    log_info "Cloud SQL Instance: $DB_INSTANCE_NAME"
    log_info "Database: $DB_NAME"
    log_info "Database User: $DB_USER"
    echo ""
    log_warning "IMPORTANT: Save these credentials securely!"
    log_warning "Database Password: $DB_PASSWORD"
    log_warning "JWT Secret: $JWT_SECRET"
    log_warning "JWT Refresh Secret: $JWT_REFRESH_SECRET"
    echo ""
    log_info "Next steps:"
    echo "  1. Update configuration files with:"
    echo "     ./scripts/update-k8s-configs.sh"
    echo "  2. Create GKE cluster (if using Kubernetes):"
    echo "     ./scripts/create-gke-cluster.sh"
    echo "  3. Deploy application:"
    echo "     kubectl apply -f k8s/"
    echo "     OR"
    echo "     gcloud builds submit --config=cloudbuild.yaml"
    echo ""
}

# Main execution
main() {
    echo ""
    log_info "========================================="
    log_info "AP2 Expense Agent - GCP Project Setup"
    log_info "========================================="
    echo ""

    check_env_vars
    set_project
    enable_apis
    create_service_account
    grant_iam_roles
    create_cloudsql_instance
    setup_database
    setup_kms
    setup_secrets
    setup_storage
    reserve_static_ip
    setup_monitoring
    print_summary
}

# Run main function
main "$@"
