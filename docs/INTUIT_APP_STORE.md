# Intuit App Store Submission Guide

This document covers the requirements and configuration needed to list AP2 Expense Management Agent on the [Intuit App Store](https://apps.intuit.com/).

## Prerequisites

1. **Intuit Developer Account** - Register at https://developer.intuit.com
2. **App Created** in the Intuit Developer Portal with QuickBooks Online API scopes
3. **Stripe Account** - For subscription billing (not through Intuit billing)
4. **Production Deployment** - HTTPS-enabled backend reachable from the internet

## Intuit Developer Portal Configuration

### App Settings

| Field | Value |
|-------|-------|
| App Name | AP2 Expense Management |
| Redirect URI (dev) | `http://localhost:8000/api/v1/quickbooks/callback` |
| Redirect URI (prod) | `https://YOUR_BACKEND_URL/api/v1/quickbooks/callback` |
| Disconnect URI | `https://YOUR_BACKEND_URL/api/v1/quickbooks/webhook/disconnect` |
| Launch URL | `https://YOUR_FRONTEND_URL/integrations` |

### Required OAuth2 Scopes

- `com.intuit.quickbooks.accounting` - Read/write QuickBooks company data

### Environment Variables

Set these in your `.env` or production secrets:

```
QUICKBOOKS_CLIENT_ID=<from Intuit Developer Portal>
QUICKBOOKS_CLIENT_SECRET=<from Intuit Developer Portal>
QUICKBOOKS_REDIRECT_URI=https://YOUR_BACKEND_URL/api/v1/quickbooks/callback
QUICKBOOKS_ENVIRONMENT=production
```

## Intuit App Store Requirements Checklist

### Technical Requirements

- [x] **OAuth2 Authorization Code flow** - `GET /api/v1/quickbooks/connect`
- [x] **Token refresh** - Handled in `qb_sync.py:_ensure_fresh_token()`
- [x] **Disconnect handler** - `POST /api/v1/quickbooks/webhook/disconnect`
- [x] **CSRF protection** - State parameter in OAuth flow with server-side validation
- [x] **Token encryption** - Access/refresh tokens encrypted at rest via `token_encryption.py`
- [x] **HTTPS enforced** - HSTS headers in production
- [x] **Error handling** - Graceful handling of expired tokens, API errors

### User Experience Requirements

- [x] **Connect button** - Frontend QuickBooks connect UI
- [x] **Connection status** - `GET /api/v1/quickbooks/status`
- [x] **Disconnect button** - `DELETE /api/v1/quickbooks/disconnect`
- [x] **Sync trigger** - `POST /api/v1/quickbooks/sync`
- [x] **Account mapping** - Map expense categories to QB chart of accounts
- [x] **Vendor mapping** - Map vendors to QB vendor list

### Legal & Compliance

- [x] **Privacy Policy** - Available at `legal/PRIVACY_POLICY.md`
- [x] **Terms of Service** - Available at `legal/TERMS_OF_SERVICE.md`
- [x] **Data handling disclosure** - Tokens encrypted, data scoped per organization
- [ ] **Hosted privacy policy URL** - Deploy to `https://YOUR_DOMAIN/privacy`
- [ ] **Hosted ToS URL** - Deploy to `https://YOUR_DOMAIN/terms`
- [ ] **Support contact** - Email and/or phone for app users

### App Store Listing Assets

- [ ] **App icon** - 200x200px PNG
- [ ] **Screenshots** - At least 3 screenshots of the integration in use
- [ ] **Description** - Short (120 chars) and long description
- [ ] **Category** - "Expense Management" or "Accounting"
- [ ] **Pricing** - Free to install (billing via Stripe, not Intuit)

## API Endpoints for QuickBooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/quickbooks/connect` | GET | Start OAuth2 flow, returns authorization URL |
| `/api/v1/quickbooks/callback` | GET | OAuth2 callback, exchanges code for tokens |
| `/api/v1/quickbooks/disconnect` | DELETE | Disconnect QuickBooks from org |
| `/api/v1/quickbooks/status` | GET | Connection and sync status |
| `/api/v1/quickbooks/sync` | POST | Trigger expense sync to QuickBooks |
| `/api/v1/quickbooks/accounts` | GET | Get QB chart of accounts for mapping |
| `/api/v1/quickbooks/vendors` | GET | Get QB vendor list |
| `/api/v1/quickbooks/webhook/disconnect` | POST | Handle Intuit-initiated disconnect |

## What Gets Synced

When a user triggers sync, approved expenses are pushed to QuickBooks Online as purchases/bills:

- **Amount** -> Bill/Purchase amount
- **Vendor** -> Mapped to QB Vendor (or created)
- **Category** -> Mapped to QB Expense Account
- **Date** -> Transaction date
- **Description** -> Memo field
- **Receipt** -> Attachment (if available)

## Testing the Integration

### Sandbox Testing

1. Set `QUICKBOOKS_ENVIRONMENT=sandbox` in `.env`
2. Use your Intuit Developer sandbox company
3. Connect via the frontend QuickBooks integration page
4. Create test expenses and trigger sync
5. Verify data appears in the sandbox QB company

### Production Testing

1. Switch to `QUICKBOOKS_ENVIRONMENT=production`
2. Update redirect URI to production URL in Intuit Developer Portal
3. Test full OAuth flow with a real QuickBooks Online account
4. Verify sync creates correct transactions

## Submission Process

1. Complete all checklist items above
2. In the Intuit Developer Portal, go to your app > "App Store Listing"
3. Fill in listing details, upload assets
4. Submit for review
5. Intuit reviews the app (typically 2-4 weeks)
6. Address any feedback from the review team
7. App goes live on the Intuit App Store
