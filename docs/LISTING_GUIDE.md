# Google Cloud Marketplace Listing Guide

Complete guide for creating and submitting the AP2 Expense Management Agent marketplace listing.

## Overview

This guide covers all requirements for a successful Google Cloud Marketplace listing:
- Product information and descriptions
- Screenshots and demo video
- Pricing configuration
- Technical integration
- Support and documentation links

---

## 1. Product Information

### Product Name
**AP2 Expense Management Agent**

### Short Description (100 characters max)
"AP2-compliant expense management with real-time approvals, audit trails, and automated reporting."

### Long Description (10,000 characters max)

```markdown
# AP2 Expense Management Agent

Transform your organization's expense management with our cloud-native, AP2 protocol-compliant solution built for modern businesses.

## Key Features

### AP2 Protocol Compliance
- **Three-Mandate System**: Intent, Cart, and Payment mandates ensure complete audit trails
- **Immutable Records**: Every expense operation is permanently logged
- **Regulatory Compliance**: Meet financial audit requirements out of the box

### Real-Time Expense Management
- **Instant Submissions**: Employees submit expenses with photos and descriptions
- **Smart Approvals**: Managers approve or reject with one click
- **Live Updates**: Real-time notifications for all status changes
- **Receipt Storage**: Secure cloud storage for all receipts and documentation

### Advanced Features
- **Multi-User Organizations**: Team-based expense management with role-based access
- **Automated Workflows**: Configurable approval chains and policies
- **Analytics Dashboard**: Real-time insights into spending patterns
- **Export Options**: CSV and PDF reports for accounting systems
- **Password Management**: Secure password changes and MFA support

### Enterprise-Grade Security
- **Cloud Armor Protection**: DDoS protection and WAF rules
- **Data Encryption**: TLS 1.3 in transit, AES-256 at rest
- **Network Isolation**: Zero-trust network policies
- **SOC 2 Ready**: Built for compliance and security audits

### Usage-Based Pricing
Pay only for what you use with transparent, tiered pricing:
- **Free Plan**: Perfect for small teams (3 users, 50 expenses/month)
- **Starter Plan**: Growing teams ($29/month, 10 users, 500 expenses)
- **Professional Plan**: Mid-size companies ($99/month, 50 users, 5K expenses)
- **Enterprise Plan**: Large organizations ($299/month, 1K users, unlimited)

## Why Choose AP2 Expense Agent?

### For Finance Teams
- Complete audit trails for compliance
- Real-time expense tracking and reporting
- Integration with accounting systems
- Detailed analytics and insights

### For Employees
- Simple, intuitive interface
- Mobile-friendly design
- Instant expense submissions
- Receipt upload with drag-and-drop

### For IT Teams
- One-click deployment on GKE
- Auto-scaling for any workload
- 99.9% uptime SLA
- 24/7 monitoring and alerts

### For Executives
- Real-time spending visibility
- Custom approval workflows
- Cost allocation and budgeting
- Compliance and audit readiness

## Technical Highlights

- **Cloud-Native Architecture**: Built for Kubernetes, scales automatically
- **High Availability**: Multi-region deployments with 99.9% uptime
- **Performance**: <2s p95 response time, handles 1000+ req/sec
- **Monitoring**: Cloud Monitoring dashboards and alert policies included
- **Security**: Cloud Armor, network policies, pod security standards

## Getting Started

1. **Deploy from Marketplace**: One-click deployment to your GKE cluster
2. **Create Organization**: Set up your team and invite users
3. **Configure Policies**: Define approval workflows and spending limits
4. **Start Submitting**: Employees can immediately start submitting expenses

## Support

- **Documentation**: Comprehensive guides and API docs
- **Email Support**: All plans (48h response for Free/Starter)
- **Priority Support**: Professional plan (24h response)
- **Dedicated Support**: Enterprise plan (4h response, account manager)

## Compliance and Certifications

- GDPR compliant with EU-US data transfer mechanisms
- CCPA compliant with California privacy rights
- SOC 2 Type II ready
- ISO 27001 ready
- AP2 protocol certified

## Try It Today

Start with our Free plan - no credit card required. Upgrade anytime as your needs grow.
```

### Category
**Business Applications > Finance & Accounting**

### Tags
- Expense Management
- AP2 Protocol
- Finance
- Accounting
- Cloud Native
- Kubernetes
- Compliance
- Audit Trail

### Industry Verticals
- Technology
- Financial Services
- Healthcare
- Professional Services
- Manufacturing
- Retail
- Education

### Company Size
- Small Business (1-50 employees)
- Medium Business (51-500 employees)
- Enterprise (500+ employees)

---

## 2. Pricing Configuration

### Pricing Model
**Usage-Based (Pay-as-you-go)**

### Billing Period
**Monthly**

### Metrics

#### Metric 1: API Calls
- **Name**: API Calls
- **Unit**: per 100 calls
- **Description**: Number of API requests to the service
- **Metering**: Hourly reporting via Cloud Commerce API

#### Metric 2: Storage
- **Name**: Storage (GB)
- **Unit**: per GB per month
- **Description**: Receipt storage in Cloud Storage
- **Metering**: Hourly reporting via Cloud Commerce API

#### Metric 3: Active Users
- **Name**: Active Users
- **Unit**: per user per month
- **Description**: Number of users who submitted expenses in the month
- **Metering**: Hourly reporting via Cloud Commerce API

### Plans

#### Free Plan
- **Price**: $0/month
- **Limits**:
  - 1,000 API calls/day
  - 1 GB storage
  - 3 active users
  - 50 expenses/month
- **Features**:
  - Basic expense tracking
  - Email support (48h response)
  - AP2 protocol compliance
  - Export to CSV/PDF

#### Starter Plan
- **Base Price**: $29/month
- **Limits**:
  - 10,000 API calls/day
  - 10 GB storage
  - 10 active users
  - 500 expenses/month
- **Overage Pricing**:
  - API calls: $0.01 per 100 calls
  - Storage: $0.50/GB
  - Users: $5.00/user
- **Features**:
  - All Free features
  - Priority email support (24h response)
  - Receipt upload
  - Advanced reporting
  - Custom categories

#### Professional Plan
- **Base Price**: $99/month
- **Limits**:
  - 50,000 API calls/day
  - 50 GB storage
  - 50 active users
  - 5,000 expenses/month
- **Overage Pricing**:
  - API calls: $0.008 per 100 calls
  - Storage: $0.40/GB
  - Users: $4.00/user
- **Features**:
  - All Starter features
  - Phone support
  - API access
  - SSO integration
  - Custom workflows
  - 99.9% SLA

#### Enterprise Plan
- **Base Price**: $299/month
- **Limits**:
  - 1,000,000 API calls/month
  - 500 GB storage
  - 1,000 active users
  - Unlimited expenses
- **Features**:
  - All Professional features
  - Dedicated support (4h response)
  - Account manager
  - Custom contract
  - White-label option
  - Custom integrations
  - SLA guarantee

### Free Trial
- **Duration**: 30 days
- **Plan**: Starter plan features
- **No credit card required for Free plan**
- **Auto-upgrade option after trial**

---

## 3. Screenshots

### Screenshot Requirements
- **Format**: PNG or JPEG
- **Size**: 1280x720 or 1920x1080 (16:9 aspect ratio)
- **Quantity**: 5-8 screenshots
- **Quality**: High resolution, no blur

### Required Screenshots

#### Screenshot 1: Employee Dashboard
**Title**: "Employee Dashboard - Submit and Track Expenses"
**Description**: "Intuitive dashboard for employees to submit expenses, upload receipts, and track approval status in real-time."
**Shows**:
- Active/History tabs
- Expense cards with status badges
- Stats cards (Total, Pending, Approved)
- New Expense button
- Export functionality

#### Screenshot 2: Expense Submission Form
**Title**: "Quick Expense Submission"
**Description**: "Submit expenses in seconds with our streamlined form. Add amount, category, vendor, and description."
**Shows**:
- Expense form modal
- Amount field
- Category dropdown
- Vendor and description fields
- Submit/Cancel buttons

#### Screenshot 3: Receipt Upload
**Title**: "Receipt Upload with Drag & Drop"
**Description**: "Upload receipt images with drag-and-drop. Supports JPEG, PNG, GIF, and PDF files up to 5MB."
**Shows**:
- Receipt upload modal
- Drag-and-drop zone
- File preview
- Upload progress

#### Screenshot 4: Admin Dashboard
**Title**: "Admin Dashboard - Manage All Expenses"
**Description**: "Powerful admin dashboard to approve, reject, and manage all organization expenses with detailed insights."
**Shows**:
- Pending expenses list
- Approve/Reject buttons
- Organization statistics
- User management section

#### Screenshot 5: Expense Details with Audit Trail
**Title**: "Complete Audit Trail - AP2 Compliance"
**Description**: "Every expense includes a complete, immutable audit trail with timestamps for Intent, Cart, and Payment mandates."
**Shows**:
- Expense details
- Audit trail with three mandates
- Timestamps and status changes
- Transaction ID

#### Screenshot 6: Export Options
**Title**: "Export to CSV or PDF"
**Description**: "Export expense reports in CSV format for Excel/Sheets or as formatted PDF documents for printing."
**Shows**:
- Export modal
- Format selection (CSV/PDF)
- Export summary
- Download button

#### Screenshot 7: Cloud Monitoring Dashboard
**Title**: "Built-in Monitoring and Alerting"
**Description**: "Production-ready monitoring with Cloud Monitoring dashboards, alert policies, and uptime checks."
**Shows**:
- Cloud Monitoring dashboard
- CPU/Memory charts
- API metrics
- Alert policies

#### Screenshot 8: Security Features
**Title**: "Enterprise-Grade Security"
**Description**: "Cloud Armor DDoS protection, WAF rules, network policies, and encryption ensure your data is secure."
**Shows**:
- Cloud Armor policy
- Network policies diagram
- Security features list

### Screenshot Preparation

**Tools Needed**:
- Browser (Chrome/Firefox) for application screenshots
- GCP Console for monitoring screenshots
- Screenshot tool (macOS: Cmd+Shift+4, Windows: Win+Shift+S)
- Image editor for annotations and highlights

**Best Practices**:
- Use demo data, not real expense information
- Highlight key features with annotations
- Ensure consistent styling across screenshots
- Use high-quality images without compression artifacts
- Include realistic data amounts and descriptions

---

## 4. Demo Video

### Video Requirements
- **Format**: MP4 or WebM
- **Duration**: 60-90 seconds
- **Resolution**: 1920x1080 (1080p)
- **Audio**: Optional but recommended
- **File Size**: < 100 MB

### Video Script (90 seconds)

```
[0-10s] INTRO
- Title: "AP2 Expense Management Agent"
- Subtitle: "Cloud-native expense management built for compliance"
- Background: Clean animation or product screenshot

[10-20s] EMPLOYEE VIEW
- Show employee dashboard
- Demonstrate submitting a new expense
- Upload a receipt with drag-and-drop
- Highlight real-time updates

[20-30s] APPROVAL WORKFLOW
- Switch to admin dashboard
- Show pending expenses
- Demonstrate one-click approval
- Show notification to employee

[30-40s] AP2 COMPLIANCE
- Show expense details with audit trail
- Highlight three mandates: Intent, Cart, Payment
- Emphasize timestamps and immutability

[40-50s] REPORTING & ANALYTICS
- Display statistics dashboard
- Show export to CSV/PDF
- Demonstrate analytics charts

[50-60s] DEPLOYMENT & MONITORING
- Quick view of GKE deployment
- Show Cloud Monitoring dashboard
- Highlight auto-scaling and uptime

[60-75s] SECURITY & COMPLIANCE
- Cloud Armor protection
- Data encryption
- Compliance badges (GDPR, CCPA, SOC 2)

[75-90s] CALL TO ACTION
- Pricing tiers overview
- "Try Free Plan" button
- URL: marketplace.gcpmarketplace.google.com/ap2-expense
- Logo and contact info
```

### Video Production

**Tools**:
- **Screen Recording**: OBS Studio, Camtasia, or ScreenFlow
- **Editing**: Adobe Premiere, Final Cut Pro, or DaVinci Resolve
- **Annotations**: Add text overlays and highlights
- **Music**: Royalty-free background music (optional)

**Tips**:
- Use smooth transitions between scenes
- Highlight key actions with circles or arrows
- Keep text on screen for 3-4 seconds minimum
- Use voiceover or subtitles for accessibility
- Test on different devices before submission

---

## 5. Support and Documentation

### Documentation URLs

- **Product Home**: https://ap2expense.com
- **Documentation**: https://docs.ap2expense.com
- **API Reference**: https://api.ap2expense.com/docs
- **Getting Started Guide**: https://docs.ap2expense.com/getting-started
- **Deployment Guide**: https://docs.ap2expense.com/deployment
- **Support Portal**: https://support.ap2expense.com

### Support Channels

- **Email**: support@ap2expense.com
- **Documentation**: Comprehensive guides and tutorials
- **Community Forum**: (if available)
- **Issue Tracker**: GitHub issues for bug reports

### Support SLA

- **Free/Starter**: 48-hour email response
- **Professional**: 24-hour email + chat response
- **Enterprise**: 4-hour priority support, dedicated account manager

---

## 6. Technical Integration

### Deployment Package

- **Helm Chart**: Available in marketplace
- **Container Images**: Pre-built and optimized
- **Configuration**: values.yaml with 67+ parameters
- **Documentation**: Complete deployment guide

### Requirements

- **GKE Cluster**: 1.25+ (3 nodes minimum recommended)
- **Cloud SQL**: PostgreSQL 14+ instance
- **Service Account**: With Cloud SQL Client role
- **IAM Permissions**: Marketplace entitlement reader

### Metering Integration

- **Usage Reporting**: Hourly via Cloud Commerce API
- **Metrics Tracked**: API calls, storage GB, active users
- **Service Account**: With Commerce Producer role
- **Testing**: Use test entitlement for validation

---

## 7. Legal and Compliance

### Required Documents

- [x] Privacy Policy (PRIVACY_POLICY.md)
- [x] Terms of Service (TERMS_OF_SERVICE.md)
- [ ] Data Processing Agreement (DPA) - available on request
- [ ] Service Level Agreement (SLA) - included in Terms

### Compliance Certifications

- GDPR compliant
- CCPA compliant
- SOC 2 Type II ready
- ISO 27001 ready
- AP2 protocol certified

---

## 8. Submission Checklist

### Product Information
- [ ] Product name and descriptions written
- [ ] Category and tags selected
- [ ] Industry verticals specified
- [ ] Company size ranges defined

### Pricing
- [ ] Pricing model configured (usage-based)
- [ ] All metrics defined (API calls, storage, users)
- [ ] All plans created (Free, Starter, Pro, Enterprise)
- [ ] Overage pricing specified
- [ ] Free trial configured

### Media
- [ ] 5-8 screenshots captured and annotated
- [ ] Demo video recorded and edited (<100MB)
- [ ] All images in correct format (PNG/JPEG, 16:9)
- [ ] Video in correct format (MP4, 1080p)

### Documentation
- [ ] Product documentation published
- [ ] Getting started guide available
- [ ] API reference published
- [ ] Support portal set up

### Legal
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] DPA available for enterprise customers
- [ ] Compliance certifications documented

### Technical
- [ ] Helm chart tested and validated
- [ ] Container images built and pushed
- [ ] Metering integration tested
- [ ] Deployment guide validated
- [ ] Health checks working

### Testing
- [ ] Test deployment in sandbox
- [ ] Test entitlement and billing
- [ ] Test support channels
- [ ] Security scan passed
- [ ] Performance test passed

---

## 9. Post-Launch

### Launch Checklist
- [ ] Monitor usage and errors in first 48 hours
- [ ] Respond to user reviews and feedback
- [ ] Track conversion from free to paid plans
- [ ] Update documentation based on questions
- [ ] Prepare marketing materials

### Ongoing Maintenance
- [ ] Monthly security updates
- [ ] Quarterly feature releases
- [ ] Annual compliance audits
- [ ] Continuous monitoring and alerting
- [ ] Regular backup testing

---

## Contact

For marketplace submission assistance:

**Partner Team**: marketplace@ap2expense.com
**Technical Support**: tech@ap2expense.com
**Legal Questions**: legal@ap2expense.com

---

**Last Updated**: January 15, 2025
