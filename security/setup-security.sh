#!/bin/bash
# Setup Google Cloud Armor and Kubernetes security for AP2 Expense Agent
# Usage: ./setup-security.sh PROJECT_ID

set -e

PROJECT_ID="${1:-YOUR_PROJECT_ID}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up security for AP2 Expense Agent${NC}"
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo ""

# Set project
gcloud config set project ${PROJECT_ID}

# Step 1: Create Cloud Armor security policy
echo -e "${GREEN}[1/6] Creating Cloud Armor security policy...${NC}"

# Check if policy exists
if gcloud compute security-policies describe ap2-expense-policy &>/dev/null; then
  echo -e "${YELLOW}Security policy already exists, updating...${NC}"
else
  gcloud compute security-policies create ap2-expense-policy \
    --description "AP2 Expense Agent Security Policy - DDoS and WAF protection"
fi

# Add rate limiting rule
echo -e "${GREEN}Adding rate limiting rule...${NC}"
gcloud compute security-policies rules create 2000 \
  --security-policy ap2-expense-policy \
  --action rate-based-ban \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60 \
  --ban-duration-sec 600 \
  --conform-action allow \
  --exceed-action deny-429 \
  --enforce-on-key IP || echo "Rule 2000 already exists"

# Add SQL injection protection
echo -e "${GREEN}Adding SQL injection protection...${NC}"
gcloud compute security-policies rules create 3000 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('sqli-stable')" \
  --action deny-403 || echo "Rule 3000 already exists"

# Add XSS protection
echo -e "${GREEN}Adding XSS protection...${NC}"
gcloud compute security-policies rules create 3100 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('xss-stable')" \
  --action deny-403 || echo "Rule 3100 already exists"

# Add local file inclusion protection
echo -e "${GREEN}Adding LFI protection...${NC}"
gcloud compute security-policies rules create 3200 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('lfi-stable')" \
  --action deny-403 || echo "Rule 3200 already exists"

# Add remote code execution protection
echo -e "${GREEN}Adding RCE protection...${NC}"
gcloud compute security-policies rules create 3300 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('rce-stable')" \
  --action deny-403 || echo "Rule 3300 already exists"

# Add protocol attack protection
echo -e "${GREEN}Adding protocol attack protection...${NC}"
gcloud compute security-policies rules create 3400 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('protocolattack-stable')" \
  --action deny-403 || echo "Rule 3400 already exists"

# Add PHP injection protection
echo -e "${GREEN}Adding PHP injection protection...${NC}"
gcloud compute security-policies rules create 3500 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('php-stable')" \
  --action deny-403 || echo "Rule 3500 already exists"

# Add session fixation protection
echo -e "${GREEN}Adding session fixation protection...${NC}"
gcloud compute security-policies rules create 3600 \
  --security-policy ap2-expense-policy \
  --expression "evaluatePreconfiguredExpr('sessionfixation-stable')" \
  --action deny-403 || echo "Rule 3600 already exists"

# Enable adaptive protection (automatic DDoS detection)
echo -e "${GREEN}Enabling adaptive protection...${NC}"
gcloud compute security-policies update ap2-expense-policy \
  --enable-layer7-ddos-defense \
  --layer7-ddos-defense-rule-visibility=STANDARD || echo "Adaptive protection already enabled"

# Step 2: Apply security policy to backend service
echo -e "${GREEN}[2/6] Applying security policy to backend service...${NC}"
echo -e "${YELLOW}Note: This requires the backend service to be created first${NC}"
echo -e "Run this command after deploying to GKE:${NC}"
echo -e "${YELLOW}gcloud compute backend-services update BACKEND_SERVICE_NAME --security-policy ap2-expense-policy --global${NC}"

# Step 3: Apply Kubernetes network policies
echo -e "${GREEN}[3/6] Applying Kubernetes network policies...${NC}"
kubectl apply -f network-policy.yaml

# Step 4: Apply pod security policy
echo -e "${GREEN}[4/6] Applying pod security policy...${NC}"

# Check Kubernetes version
K8S_VERSION=$(kubectl version --short 2>/dev/null | grep Server | awk '{print $3}' | sed 's/v//') || K8S_VERSION="1.25"
MAJOR=$(echo $K8S_VERSION | cut -d. -f1)
MINOR=$(echo $K8S_VERSION | cut -d. -f2)

if [ "$MAJOR" -eq 1 ] && [ "$MINOR" -ge 25 ]; then
  echo -e "${YELLOW}K8s 1.25+ detected, using Pod Security Standards${NC}"
  kubectl label namespace ap2-expense \
    pod-security.kubernetes.io/enforce=restricted \
    pod-security.kubernetes.io/audit=restricted \
    pod-security.kubernetes.io/warn=restricted \
    --overwrite
else
  echo -e "${YELLOW}K8s <1.25 detected, using PodSecurityPolicy${NC}"
  kubectl apply -f pod-security-policy.yaml
fi

# Step 5: Configure Cloud SQL SSL
echo -e "${GREEN}[5/6] Configuring Cloud SQL SSL...${NC}"
echo -e "${YELLOW}Ensure Cloud SQL requires SSL connections:${NC}"
echo -e "gcloud sql instances patch YOUR_INSTANCE_NAME --require-ssl"

# Step 6: Enable Binary Authorization
echo -e "${GREEN}[6/6] Enabling Binary Authorization...${NC}"
gcloud services enable binaryauthorization.googleapis.com

echo -e "${YELLOW}Creating Binary Authorization policy...${NC}"
cat > /tmp/binauth-policy.yaml <<EOF
globalPolicyEvaluationMode: ENABLE
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
  - projects/${PROJECT_ID}/attestors/prod-attestor
EOF

gcloud container binauthz policy import /tmp/binauth-policy.yaml || echo "Binary Authorization policy already configured"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Security setup completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Summary:"
echo -e "✓ Cloud Armor security policy created with OWASP Top 10 protection"
echo -e "✓ Rate limiting: 100 requests/min per IP"
echo -e "✓ Adaptive DDoS protection enabled"
echo -e "✓ Kubernetes network policies applied"
echo -e "✓ Pod security standards configured"
echo -e "✓ Binary Authorization enabled"
echo ""
echo -e "Manual steps required:"
echo -e "1. ${YELLOW}Apply security policy to backend service after deployment${NC}"
echo -e "2. ${YELLOW}Configure Cloud SQL to require SSL${NC}"
echo -e "3. ${YELLOW}Create attestor for Binary Authorization${NC}"
echo -e "4. ${YELLOW}Test security rules in staging environment${NC}"
echo ""
echo -e "View security policy:"
echo -e "${YELLOW}https://console.cloud.google.com/net-security/securitypolicies/details/ap2-expense-policy?project=${PROJECT_ID}${NC}"
