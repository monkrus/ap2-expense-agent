# AP2 Expense Management - Pricing Structure

**Last Updated**: 2025-12-30
**Status**: Finalized and Active

---

## Pricing Tiers Overview

| Feature | Free | Starter | Professional |
|---------|------|---------|--------------|
| **Monthly Price** | $0 | $29 | $79 |
| **Users** | 2 | 5 | 25 |
| **Expenses/month** | 30 | 50 | 500 |
| **Organizations** | 1 | 3 | 10 |
| **OCR Scans/month** | 30 | 50 | 200 |
| **AP2 Payments/month** | 20* | 100* | 1,000* |
| **AI Categorization** | 0 | 50 | 500 |
| **Data Retention** | 90 days | 1 year | 3 years |
| **Approvals** | ✅ Basic | ✅ Basic | ✅ Multi-level |
| **Export** | ✅ CSV/Excel/PDF | ✅ CSV/Excel/PDF | ✅ CSV/Excel/PDF |
| **Email Notifications** | ✅ | ✅ | ✅ |
| **Support** | Community | Email | Priority + Manager |

**\* Payment processing fees apply: 2.9% + $0.30 per transaction** (Standard Stripe fees passed through to users)

---

## Key Design Decisions

### 1. **Export Available in All Tiers**
- **Rationale**: Export is client-side (ExcelJS, jsPDF) with near-zero cost
- **Benefit**: Builds trust - we don't hold data hostage
- **Competitive advantage**: Most SaaS tools restrict exports to paid tiers
- **User impact**: Free users can submit tax documents, reimbursements, etc.

### 2. **Approval Workflows in All Tiers**
- **Rationale**: Core workflow feature, not a luxury
- **Free tier**: Basic approval (submit → approve/deny)
- **Professional tier**: Multi-level approvals (submit → manager → finance → paid)

### 3. **AP2 Payment Processing Fees Passed Through**
- **Critical**: This is the ONLY sustainable model
- **Standard practice**: Stripe Connect, PayPal, Square all pass fees to users
- **Display**: "Payment processing fees apply (2.9% + $0.30/transaction)"
- **Why**: Without this, you lose money on every transaction

---

## Unit Economics

### Cost Per User (Monthly):

| Cost Component | Free | Starter | Professional |
|----------------|------|---------|--------------|
| OCR Processing | $0.045 | $0.075 | $0.30 |
| Storage | $0.001 | $0.002 | $0.01 |
| Database | $0.05 | $0.10 | $0.20 |
| Email | $0.01 | $0.02 | $0.05 |
| Support | $0 | $1.00 | $5.00 |
| **Infrastructure Total** | **$0.12/user** | **$1.22/user** | **$5.61/user** |
| **AP2 Processing** | **User pays** | **User pays** | **User pays** |

### Profitability Analysis (Per 100 Users):

**Free Tier:**
```
Revenue:    $0
Costs:      $12 (infrastructure only)
Loss:       -$12/month
Per user:   -$0.12/month (acceptable CAC)
```

**Starter Tier:**
```
Revenue:    $2,900
Costs:      $122 (infrastructure only)
Profit:     +$2,778/month
Margin:     95.8%
Per user:   +$27.78/month
```

**Professional Tier:**
```
Revenue:    $7,900
Costs:      $561 (infrastructure only)
Profit:     +$7,339/month
Margin:     92.9%
Per user:   +$73.39/month
```

### Realistic Customer Mix (Target):

Assuming 1,000 Free + 100 Starter + 20 Pro users:

```
Total Revenue:  $4,480/month
  - Free: $0
  - Starter: $2,900 (100 × $29)
  - Pro: $1,580 (20 × $79)

Total Costs:    $1,509/month
  - Free: $120 (1,000 × $0.12)
  - Starter: $122 (100 × $1.22)
  - Pro: $112 (20 × $5.61)
  - Fixed (Cloud): $75

Net Profit:     $2,971/month
Margin:         66.3%
```

**This is sustainable and profitable.**

---

## Tier Differentiation Strategy

### Free Tier: **Acquisition Funnel**
- **Goal**: Hook users on AP2 payment processing (core differentiator)
- **Limits**: Low enough to encourage upgrades (30 expenses, 1 org)
- **Generous**: Full export, basic approvals - build trust
- **Economics**: Small loss ($0.12/user) acceptable for customer acquisition

### Starter Tier: **SMB Sweet Spot**
- **Target**: 3-10 person companies
- **Value**: AI categorization saves manual work
- **Limit pressure**: 50 expenses fills up quickly for growing teams
- **Economics**: Highly profitable ($27.78/user margin)

### Professional Tier: **Enterprise-lite**
- **Target**: 15-50 person companies
- **Value**: Multi-level approvals, 10 organizations, 3-year retention
- **Support**: Dedicated account manager (justifies price)
- **Economics**: Very profitable ($73.39/user margin)

---

## What We Intentionally DON'T Have (Yet)

These features are mentioned in seed data but not implemented:
- ❌ Dashboard analytics/charts
- ❌ Advanced reporting
- ❌ Public API access
- ❌ Bulk operations UI

**Strategy**: Launch with honest, deliverable features. Add these as differentiators for future "Business" tier at $149/month.

---

## Overage Pricing (If You Enable Metering)

Currently set but not enforced:

**Starter Tier:**
- Additional user: $5.00/month
- Additional expense: $0.50 each
- Additional AP2 transaction: $0.10 each
- Additional AI categorization: $0.05 each
- Additional OCR scan: $0.02 each

**Professional Tier:**
- Additional user: $4.00/month
- Additional expense: $0.30 each
- Additional AP2 transaction: $0.08 each
- Additional AI categorization: $0.04 each
- Additional OCR scan: $0.015 each

**Recommendation**: Don't enforce overages initially. Use as "soft limits" and prompt users to upgrade.

---

## Competitive Positioning

### vs Expensify
- **Expensify**: $5/user/month (minimum 2 users = $10/month)
- **Us**: $0 Free tier (2 users), $29 Starter (5 users)
- **Advantage**: Lower entry barrier, AP2 built-in

### vs Concur
- **Concur**: Enterprise-only, $8-12/user/month
- **Us**: $79/month for 25 users = $3.16/user
- **Advantage**: Much cheaper, simpler onboarding

### vs QuickBooks Online
- **QBO**: $30/month (1 user) + $5/additional user
- **Us**: $29/month (5 users)
- **Advantage**: Better value, dedicated expense focus

---

## Future Pricing Considerations

### Potential "Business" Tier ($149/month):
- 100 users
- Unlimited organizations
- Dashboard analytics
- Public API access
- Custom integrations
- SSO/SAML
- 7-year data retention
- 24/7 phone support

### Potential Add-ons:
- White-label branding: +$50/month
- Custom approval logic: +$30/month
- Audit log export: +$20/month

---

## Implementation Notes

### Database Schema:
- Tier limits stored in `billing_tiers.limits` (JSON field)
- Enforcement in `backend/src/billing/limit_enforcer.py`
- Metering in `backend/src/billing/usage_tracker.py`

### Frontend Display:
- Pricing page: `frontend/src/pages/PricingPlans.jsx`
- Feature cards should highlight the AP2 fee pass-through
- Recommended: Add FAQ: "Why do I pay processing fees?"

### Stripe Integration:
- Free tier: No subscription (just usage tracking)
- Starter/Pro: Monthly recurring subscription
- AP2 fees: Stripe Connect - fees automatically passed through

---

## Recommendation for Launch

**Phase 1 (MVP Launch):**
- ✅ Free, Starter, Professional tiers
- ✅ Soft limits (warn users when approaching)
- ✅ Clear AP2 fee disclosure
- ✅ Manual upgrade process (contact sales)

**Phase 2 (3 months post-launch):**
- Enable self-service upgrades/downgrades
- Add overage billing
- Implement usage dashboard
- Add "Business" tier if demand exists

**Phase 3 (6 months post-launch):**
- Annual billing discount (save 20%)
- Add-on marketplace
- Enterprise tier ($299+/month, custom pricing)

---

## Key Success Metrics

Track these to optimize pricing:

1. **Conversion Rate**: Free → Starter (target: 8-12%)
2. **Expansion Rate**: Starter → Pro (target: 15-25%)
3. **Churn Rate**: <5%/month
4. **ARPU** (Average Revenue Per User): Target $4-6/month across all users
5. **CAC Payback**: <3 months

---

## Questions/Decisions Needed

- [ ] Enable overage billing? (Recommend: Not yet)
- [ ] Annual billing discount? (Recommend: 20% off = 2 months free)
- [ ] Trial period for paid tiers? (Recommend: 14 days)
- [ ] Hard limits or soft warnings? (Recommend: Soft initially)
- [ ] Self-service upgrades? (Recommend: Phase 2)

---

**This pricing structure is production-ready and sustainable.**
