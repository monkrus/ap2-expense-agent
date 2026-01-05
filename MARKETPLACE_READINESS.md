# Google Cloud Marketplace Submission Checklist

**Status:** 🟡 ALMOST READY - Need assets & testing

**Updated:** 2026-01-04

---

## ✅ Completed

### Product Implementation
- ✅ Tier limits match specification (Free: $0, Starter: $29, Pro: $99)
- ✅ AP2 Protocol integration working
- ✅ Docker containers built and tested
- ✅ Kubernetes/Helm deployment ready
- ✅ Database migrations working
- ✅ Authentication & authorization (JWT, RBAC)
- ✅ User roles simplified (USER, ADMIN)
- ✅ Billing tier enforcement active
- ✅ Multi-tenancy working (organizations)

### Documentation
- ✅ README.md with setup instructions
- ✅ Terms of Service (`legal/TERMS_OF_SERVICE.md`)
- ✅ Privacy Policy (`legal/PRIVACY_POLICY.md`)
- ✅ API documentation (OpenAPI/Swagger)

### Infrastructure
- ✅ Cloud Build configuration
- ✅ Docker images
- ✅ Kubernetes manifests
- ✅ Helm charts
- ✅ CI/CD pipeline configured

### Security & Compliance
- ✅ 13-layer tier limits protection
- ✅ Git pre-commit hooks
- ✅ Automated testing (28 tests passing)
- ✅ Security headers configured
- ✅ Rate limiting implemented

---

## 🟡 In Progress / Needed

### 1. Marketing Assets (CRITICAL - 2-3 hours)

**Required:**
- [ ] Product logo (512x512 PNG)
- [ ] Product icon (128x128 PNG)
- [ ] Screenshot 1: Dashboard overview
- [ ] Screenshot 2: Expense submission with receipt upload
- [ ] Screenshot 3: Admin approval workflow
- [ ] Screenshot 4: Analytics & reporting
- [ ] Screenshot 5: AP2 payment integration

**Optional but recommended:**
- [ ] Demo video (2-3 minutes)
- [ ] Product overview diagram

**Upload to:**
```bash
gsutil mb gs://ap2-expense-agent-assets
gsutil cp logo-512.png gs://ap2-expense-agent-assets/
gsutil cp icon-128.png gs://ap2-expense-agent-assets/
gsutil cp screenshot-*.png gs://ap2-expense-agent-assets/
gsutil acl ch -u AllUsers:R gs://ap2-expense-agent-assets/*
```

### 2. Support Infrastructure (1-2 hours)

**Choose one approach:**

Option A: Use existing email
```yaml
support:
  email: "your-email@gmail.com"  # Replace with real email
  documentation: "https://github.com/monkrus/ap2-expense-agent"
```

Option B: Set up professional support (recommended for paid product)
```yaml
support:
  email: "support@your-domain.com"
  documentation: "https://docs.your-domain.com"
  slack: "https://your-slack-community.com"  # Optional
```

### 3. GCP Project Setup (30 minutes)

- [ ] Create GCP project for marketplace app
- [ ] Enable required APIs:
  - Cloud Run API
  - Container Registry API
  - Cloud SQL API
  - Secret Manager API
  - Cloud Build API
  - Marketplace API
- [ ] Set up billing account
- [ ] Configure IAM permissions
- [ ] Create service account for deployment

### 4. Deployment Testing (2-3 hours)

- [ ] Deploy to GCP staging environment
- [ ] Test signup flow (Free tier)
- [ ] Test upgrade flow (Free → Starter → Professional)
- [ ] Test downgrade flow
- [ ] Test AP2 payment integration end-to-end
- [ ] Test all tier limits enforcement
- [ ] Load testing (100 concurrent users)
- [ ] Security testing (OWASP top 10)

### 5. Marketplace Integration (1-2 hours)

- [ ] Register as Cloud Marketplace partner
- [ ] Create product listing
- [ ] Configure pricing and billing
- [ ] Set up procurement webhook endpoints
- [ ] Test subscription activation
- [ ] Test subscription cancellation
- [ ] Test subscription upgrade/downgrade

---

## 📋 Tier Configuration Summary

### Free Tier (Development/Testing)
- **Price:** $0/month
- **Organizations:** 1
- **Users:** 2
- **Expenses:** 30/month
- **OCR:** 20/month
- **AI Categorizations:** 0
- **AP2 Transactions:** 20/month
- **Data Retention:** 90 days
- **Features:** Basic expense tracking only

### Starter Plan (Marketplace)
- **Price:** $29/month
- **Organizations:** 3
- **Users:** 10
- **Expenses:** 100/month
- **OCR:** 100/month
- **AI Categorizations:** 50/month
- **AP2 Transactions:** 100/month
- **Data Retention:** 1 year
- **Features:** Approval workflows, advanced analytics

### Professional Plan (Marketplace) ⭐ RECOMMENDED
- **Price:** $99/month
- **Organizations:** 10
- **Users:** 50
- **Expenses:** 500/month
- **OCR:** Unlimited
- **AI Categorizations:** 200/month
- **AP2 Transactions:** Unlimited
- **Data Retention:** 3 years
- **Features:** Everything + API access

---

## 🚀 Quick Start to Submit

### Step 1: Create Screenshots (30 min)
```bash
# Start app locally
cd frontend && npm run dev &
cd backend && ./venv/Scripts/python.exe -m uvicorn src.api:app --reload &

# Login and take 5 screenshots using browser dev tools or screenshot tool
# Save as: screenshot-1.png, screenshot-2.png, etc.
```

### Step 2: Create Logo/Icon (30 min)
Use Canva, Figma, or any design tool:
- Logo: 512x512, PNG, transparent background
- Icon: 128x128, PNG, transparent background
- Theme: Professional, tech-focused, finance-related

### Step 3: Upload Assets (10 min)
```bash
# Create bucket
gcloud config set project YOUR_PROJECT_ID
gsutil mb gs://ap2-expense-agent-assets

# Upload files
gsutil cp logo-512.png gs://ap2-expense-agent-assets/
gsutil cp icon-128.png gs://ap2-expense-agent-assets/
gsutil cp screenshot-*.png gs://ap2-expense-agent-assets/

# Make public
gsutil iam ch allUsers:objectViewer gs://ap2-expense-agent-assets
```

### Step 4: Deploy to GCP (1 hour)
```bash
# Build and push containers
gcloud builds submit --config=cloudbuild.yaml

# Deploy to Cloud Run
kubectl apply -f k8s/

# Test endpoints
curl https://your-app-url.run.app/health
```

### Step 5: Submit to Marketplace (30 min)
1. Go to: https://console.cloud.google.com/marketplace/partners
2. Create new product listing
3. Fill in product details from `marketplace/gcp-marketplace-manifest.yaml`
4. Upload assets
5. Configure pricing (Starter $29, Professional $99)
6. Set up procurement integration
7. Submit for review

---

## ⚠️ Critical Notes

### Free Tier Strategy
- **NOT listed in marketplace** (GCP doesn't support $0 tiers)
- Users can sign up on your website/app directly
- 14-day trial gives Starter plan features
- After trial, downgrades to Free automatically (unless they subscribe)

### Support Requirements
- **Must have working support email** before submission
- Response time SLA: 48 hours for paid tiers
- Set up auto-responder if using personal email

### Legal Requirements
- ✅ Terms of Service reviewed and published
- ✅ Privacy Policy reviewed and published
- ⚠️  GDPR compliance statement needed (if serving EU)
- ⚠️  Data processing agreement template needed

### Testing Checklist Before Submit
- [ ] All 28 automated tests passing
- [ ] Manual E2E test completed
- [ ] Payment flow tested (test mode)
- [ ] All tier limits enforced correctly
- [ ] No console errors in frontend
- [ ] No critical warnings in backend logs
- [ ] SSL certificate working
- [ ] Custom domain configured (optional)

---

## 📞 Next Steps

**Immediate (Today):**
1. Create 5 screenshots of your app
2. Design logo and icon
3. Upload assets to GCS bucket
4. Set up support email

**This Week:**
1. Deploy to GCP staging
2. Complete E2E testing
3. Create marketplace listing (draft)
4. Review legal docs

**Before Launch:**
1. Submit marketplace listing for review (3-5 days approval)
2. Set up monitoring and alerts
3. Prepare launch announcement
4. Create user onboarding documentation

---

## 🎯 Estimated Timeline

- **Today:** Assets creation (3-4 hours)
- **Tomorrow:** GCP deployment and testing (4-6 hours)
- **Day 3:** Marketplace submission and review start
- **Day 5-10:** Google review and approval
- **Day 11:** LAUNCH! 🚀

---

**Current Blockers:**
1. Need to create 5 screenshots
2. Need to create logo/icon
3. Need to set up support email
4. Need to deploy to GCP for testing

**Ready to deploy:**
- Backend code ✅
- Frontend code ✅
- Database migrations ✅
- Kubernetes configs ✅
- Billing integration ✅
