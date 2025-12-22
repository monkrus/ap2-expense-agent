#!/bin/bash
# Deploy AP2 Expense Agent to Google Kubernetes Engine
# Usage: ./deploy-k8s.sh [PROJECT_ID] [CLUSTER_NAME] [ZONE]

set -e

# Configuration
PROJECT_ID="${1:-YOUR_PROJECT_ID}"
CLUSTER_NAME="${2:-ap2-expense-cluster}"
ZONE="${3:-us-central1-a}"
NAMESPACE="ap2-expense"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Deploying AP2 Expense Agent to GKE${NC}"
echo -e "Project: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Cluster: ${YELLOW}${CLUSTER_NAME}${NC}"
echo -e "Zone: ${YELLOW}${ZONE}${NC}"
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Please install it first.${NC}"
    exit 1
fi

# Get cluster credentials
echo -e "${GREEN}[1/7] Getting cluster credentials...${NC}"
gcloud container clusters get-credentials ${CLUSTER_NAME} \
    --zone=${ZONE} \
    --project=${PROJECT_ID}

# Create namespace
echo -e "${GREEN}[2/7] Creating namespace...${NC}"
kubectl apply -f k8s/namespace.yaml

# Create ConfigMap
echo -e "${GREEN}[3/7] Creating ConfigMap...${NC}"
kubectl apply -f k8s/configmap.yaml

# Create Secrets (IMPORTANT: Update secrets.yaml first!)
echo -e "${YELLOW}[4/7] Creating Secrets...${NC}"
echo -e "${YELLOW}WARNING: Make sure you've updated k8s/secrets.yaml with actual secrets!${NC}"
read -p "Have you updated secrets.yaml? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${RED}Deployment cancelled. Please update secrets.yaml first.${NC}"
    exit 1
fi
kubectl apply -f k8s/secrets.yaml

# Create ServiceAccount and RBAC
echo -e "${GREEN}[5/7] Creating ServiceAccount and RBAC...${NC}"
kubectl apply -f k8s/serviceaccount.yaml

# Deploy Backend
echo -e "${GREEN}[6/7] Deploying Backend...${NC}"
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Deploy Frontend
echo -e "${GREEN}[6/7] Deploying Frontend...${NC}"
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# Create Ingress
echo -e "${GREEN}[7/7] Creating Ingress...${NC}"
kubectl apply -f k8s/ingress.yaml

# Create Horizontal Pod Autoscalers
echo -e "${GREEN}Creating Horizontal Pod Autoscalers...${NC}"
kubectl apply -f k8s/hpa.yaml

# Wait for deployments to be ready
echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s \
    deployment/backend deployment/frontend -n ${NAMESPACE}

# Show deployment status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Deployment Status:${NC}"
kubectl get pods -n ${NAMESPACE}
echo ""
echo -e "${YELLOW}Services:${NC}"
kubectl get svc -n ${NAMESPACE}
echo ""
echo -e "${YELLOW}Ingress:${NC}"
kubectl get ingress -n ${NAMESPACE}
echo ""
echo -e "Next steps:"
echo -e "1. Wait for Ingress to get external IP: ${YELLOW}kubectl get ingress -n ${NAMESPACE} -w${NC}"
echo -e "2. Configure DNS to point to the Ingress IP"
echo -e "3. Check logs: ${YELLOW}kubectl logs -f deployment/backend -n ${NAMESPACE}${NC}"
echo -e "4. Access the application at your configured domain"
