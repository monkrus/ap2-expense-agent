# Google Cloud Marketplace Integration Testing Guide

## Overview

This guide outlines how to validate the Google Cloud Marketplace integration for AP2 Expense Agent using Pub/Sub push with Google-signed OIDC, entitlement events, and usage reporting.

---

## Table of Contents

1. Prerequisites
2. Test Environment Setup
3. Entitlement Flow Testing (Pub/Sub push)
4. Usage Reporting Testing
5. Troubleshooting

---

## Prerequisites

- GCP project with Marketplace APIs enabled
- Pub/Sub and Cloud Build permissions
- Deployed backend with `GCP_WEBHOOK_AUDIENCE` configured
- Access to Cloud Logging

Environment variables:

```bash
export GCP_PROJECT_ID="your-project-id"
export API_BASE_URL="https://your-domain.com/api"
export TEST_ENTITLEMENT_ID="test-ent-12345"
export TEST_ACCOUNT_ID="test-acct-67890"
```

---

## Test Environment Setup

### 1. Enable Test Mode

Set backend config to staging values and enable usage reporting.

### 2. Configure Webhook Endpoint (OIDC / Pub/Sub)

Use Pub/Sub push with Google-signed OIDC tokens:

1. Create a Pub/Sub topic and push subscription to:
   `https://your-domain.com/api/webhooks/gcp/events`
2. Enable OIDC token on the subscription with audience set to the same URL.
3. Set `GCP_WEBHOOK_AUDIENCE` to this URL on the backend.
4. In production, OIDC is required; HMAC is allowed only in development.

### 3. Create Test Organization

Use your existing admin APIs to create a test org and user.

---

## Entitlement Flow Testing (Pub/Sub push)

Publish decoded payloads below to your Pub/Sub topic. The push subscription will deliver events to `/api/webhooks/gcp/events`.

### Test 1: New Entitlement Creation (acknowledge)

```json
{
  "eventType": "ENTITLEMENT_CREATE",
  "entitlement": {"id": "ent_test_123", "state": "ACTIVE", "plan": "professional"}
}
```

Expected: HTTP 200 and `{ "status": "acknowledged" }` (provisioning handled in onboarding flow).

### Test 2: Entitlement Update (Tier Change)

```json
{
  "eventType": "ENTITLEMENT_PLAN_CHANGE",
  "entitlementId": "ent_test_123",
  "oldPlan": "professional",
  "newPlan": "enterprise",
  "effectiveTime": "2025-11-10T11:00:00Z"
}
```

Expected: Tier updated, limits increased, billing event logged.

### Test 3: Entitlement Cancellation

```json
{
  "eventType": "ENTITLEMENT_UPDATE",
  "entitlement": {"id": "ent_test_123", "state": "CANCELLED"},
  "reason": "customer_requested",
  "effectiveTime": "2025-11-10T12:00:00Z"
}
```

Expected: Subscription status `cancelled`, org access restricted after grace period, email sent, billing event logged.

---

## Usage Reporting Testing

1. Generate usage by creating expenses, AI categorizations, and AP2 transactions.
2. Trigger the hourly reporting job or call the `/api/webhooks/gcp/report-usage` if enabled.
3. Verify logs show successful entitlement usage reports to Consumer Procurement API.

---

## Troubleshooting

- Ensure `Authorization: Bearer <OIDC>` header present; audience must match `GCP_WEBHOOK_AUDIENCE`.
- In development only, `X-Goog-Signature` HMAC can be used when `GCP_WEBHOOK_SECRET` is set.
- Check Cloud Logging for webhook errors and usage reporting responses.
