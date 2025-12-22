#!/bin/bash

###############################################################################
# Create GKE Cluster for AP2 Expense Agent
#
# This script creates a production-ready GKE cluster with:
# - Workload Identity
# - Auto-scaling
# - Auto-repair and auto-upgrade
# - Monitoring and logging
# - Network policies
###############################################################################

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check environment variables
check_env_vars() {
    local required_vars=(
        "GCP_PROJECT_ID"
        "GCP_REGION"
        "GKE_CLUSTER_NAME"
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
        exit 1
    fi
}

# Set defaults for optional variables
set_defaults() {
    export GKE_MACHINE_TYPE="${GKE_MACHINE_TYPE:-n2-standard-4}"
    export GKE_NUM_NODES="${GKE_NUM_NODES:-1}"
    export GKE_MIN_NODES="${GKE_MIN_NODES:-1}"
    export GKE_MAX_NODES="${GKE_MAX_NODES:-10}"
    export GKE_RELEASE_CHANNEL="${GKE_RELEASE_CHANNEL:-regular}"
    export GKE_AUTOPILOT="${GKE_AUTOPILOT:-false}"
}

# Create standard GKE cluster
create_standard_cluster() {
    log_info "Creating GKE standard cluster: $GKE_CLUSTER_NAME"

    gcloud container clusters create "$GKE_CLUSTER_NAME" \
        --project="$GCP_PROJECT_ID" \
        --region="$GCP_REGION" \
        --machine-type="$GKE_MACHINE_TYPE" \
        --num-nodes="$GKE_NUM_NODES" \
        --enable-autoscaling \
        --min-nodes="$GKE_MIN_NODES" \
        --max-nodes="$GKE_MAX_NODES" \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-ip-alias \
        --network="default" \
        --subnetwork="default" \
        --enable-stackdriver-kubernetes \
        --enable-cloud-logging \
        --enable-cloud-monitoring \
        --logging=SYSTEM,WORKLOAD \
        --monitoring=SYSTEM \
        --workload-pool="${GCP_PROJECT_ID}.svc.id.goog" \
        --enable-shielded-nodes \
        --shielded-secure-boot \
        --shielded-integrity-monitoring \
        --release-channel="$GKE_RELEASE_CHANNEL" \
        --addons=HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver \
        --enable-network-policy \
        --maintenance-window-start="2025-01-01T03:00:00Z" \
        --maintenance-window-duration=4h \
        --maintenance-window-recurrence="FREQ=WEEKLY;BYDAY=SU"

    log_success "GKE cluster created successfully"
}

# Create autopilot cluster
create_autopilot_cluster() {
    log_info "Creating GKE Autopilot cluster: $GKE_CLUSTER_NAME"

    gcloud container clusters create-auto "$GKE_CLUSTER_NAME" \
        --project="$GCP_PROJECT_ID" \
        --region="$GCP_REGION" \
        --release-channel="$GKE_RELEASE_CHANNEL" \
        --enable-stackdriver-kubernetes \
        --enable-cloud-logging \
        --enable-cloud-monitoring \
        --workload-pool="${GCP_PROJECT_ID}.svc.id.goog" \
        --enable-shielded-nodes

    log_success "GKE Autopilot cluster created successfully"
}

# Get cluster credentials
get_credentials() {
    log_info "Getting cluster credentials..."

    gcloud container clusters get-credentials "$GKE_CLUSTER_NAME" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID"

    log_success "Credentials configured for kubectl"
}

# Verify cluster
verify_cluster() {
    log_info "Verifying cluster..."

    # Check nodes
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    log_info "Nodes running: $node_count"

    # Check system pods
    kubectl get pods -n kube-system

    log_success "Cluster verification complete"
}

# Configure Workload Identity
configure_workload_identity() {
    log_info "Configuring Workload Identity..."

    # Create namespace
    kubectl create namespace ap2-expense --dry-run=client -o yaml | kubectl apply -f -

    # Create Kubernetes service account
    kubectl create serviceaccount ap2-expense-sa \
        --namespace=ap2-expense \
        --dry-run=client -o yaml | kubectl apply -f -

    # Bind K8s SA to GCP SA
    local gcp_sa="ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

    gcloud iam service-accounts add-iam-policy-binding "$gcp_sa" \
        --project="$GCP_PROJECT_ID" \
        --role roles/iam.workloadIdentityUser \
        --member "serviceAccount:${GCP_PROJECT_ID}.svc.id.goog[ap2-expense/ap2-expense-sa]"

    # Annotate K8s service account
    kubectl annotate serviceaccount ap2-expense-sa \
        --namespace=ap2-expense \
        iam.gke.io/gcp-service-account="$gcp_sa" \
        --overwrite

    log_success "Workload Identity configured"
}

# Install metrics server (if not already installed)
install_metrics_server() {
    log_info "Checking metrics server..."

    if kubectl get deployment metrics-server -n kube-system &>/dev/null; then
        log_info "Metrics server already installed"
    else
        log_info "Installing metrics server..."
        kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
        log_success "Metrics server installed"
    fi
}

# Configure cluster-level resources
configure_cluster_resources() {
    log_info "Configuring cluster-level resources..."

    # Create priority classes
    cat <<EOF | kubectl apply -f -
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000
globalDefault: false
description: "High priority for critical workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: medium-priority
value: 500
globalDefault: true
description: "Medium priority for standard workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 100
globalDefault: false
description: "Low priority for batch jobs"
EOF

    log_success "Cluster resources configured"
}

# Configure network policies
configure_network_policies() {
    log_info "Configuring default network policies..."

    # Allow DNS
    cat <<EOF | kubectl apply -f - -n ap2-expense
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
EOF

    log_success "Network policies configured"
}

# Print cluster info
print_cluster_info() {
    log_success "========================================="
    log_success "GKE Cluster Created!"
    log_success "========================================="
    echo ""
    log_info "Cluster name: $GKE_CLUSTER_NAME"
    log_info "Region: $GCP_REGION"
    log_info "Project: $GCP_PROJECT_ID"
    echo ""

    if [ "$GKE_AUTOPILOT" = "true" ]; then
        log_info "Type: Autopilot"
        log_info "Nodes: Auto-managed by GKE"
    else
        log_info "Type: Standard"
        log_info "Machine type: $GKE_MACHINE_TYPE"
        log_info "Nodes: $GKE_NUM_NODES (min: $GKE_MIN_NODES, max: $GKE_MAX_NODES)"
    fi

    echo ""
    log_info "Cluster endpoint:"
    gcloud container clusters describe "$GKE_CLUSTER_NAME" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(endpoint)"

    echo ""
    log_info "Current context:"
    kubectl config current-context

    echo ""
    log_info "Next steps:"
    echo "  1. Update k8s configuration files:"
    echo "     ./scripts/update-k8s-configs.sh"
    echo "  2. Deploy application:"
    echo "     kubectl apply -f k8s/"
    echo "  3. Check deployment status:"
    echo "     kubectl get pods -n ap2-expense"
    echo ""
}

# Cleanup on error
cleanup_on_error() {
    log_error "Error occurred during cluster creation"
    log_warning "To delete partially created cluster, run:"
    echo "  gcloud container clusters delete $GKE_CLUSTER_NAME --region=$GCP_REGION"
}

# Main execution
main() {
    echo ""
    log_info "========================================="
    log_info "Creating GKE Cluster"
    log_info "========================================="
    echo ""

    # Set trap for errors
    trap cleanup_on_error ERR

    check_env_vars
    set_defaults

    # Show configuration
    log_info "Configuration:"
    echo "  Project: $GCP_PROJECT_ID"
    echo "  Region: $GCP_REGION"
    echo "  Cluster: $GKE_CLUSTER_NAME"
    echo "  Type: $([ "$GKE_AUTOPILOT" = "true" ] && echo "Autopilot" || echo "Standard")"
    if [ "$GKE_AUTOPILOT" != "true" ]; then
        echo "  Machine: $GKE_MACHINE_TYPE"
        echo "  Nodes: $GKE_NUM_NODES (autoscale: $GKE_MIN_NODES-$GKE_MAX_NODES)"
    fi
    echo ""

    # Confirm
    read -p "Create cluster with this configuration? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Cluster creation cancelled"
        exit 0
    fi

    # Create cluster
    if [ "$GKE_AUTOPILOT" = "true" ]; then
        create_autopilot_cluster
    else
        create_standard_cluster
    fi

    # Post-creation steps
    get_credentials
    verify_cluster
    configure_workload_identity

    if [ "$GKE_AUTOPILOT" != "true" ]; then
        install_metrics_server
    fi

    configure_cluster_resources
    configure_network_policies

    print_cluster_info
}

main "$@"
