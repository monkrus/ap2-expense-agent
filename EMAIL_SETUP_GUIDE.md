# Email Setup Guide

Organization invitation emails are currently **not being sent** because SMTP is not configured with real credentials.

## Current Status

Your `.env` file has placeholder values:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

## How to Enable Email Sending

### Option 1: Gmail (Recommended for Development)

1. **Use a Gmail Account** (or create a new one for your app)

2. **Enable 2-Step Verification** (if not already enabled)
   - Go to: https://myaccount.google.com/security
   - Click "2-Step Verification" and follow the setup

3. **Create an App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" as the app
   - Select "Other (Custom name)" as the device, name it "AP2 Expense Agent"
   - Google will generate a 16-character password like: `xxxx xxxx xxxx xxxx`
   - **Copy this password** (you won't see it again)

4. **Update Your `.env` File**
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-actual-email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   SMTP_FROM_EMAIL=your-actual-email@gmail.com
   ```

5. **Restart the Backend**
   - Stop the backend server (Ctrl+C)
   - Start it again: `uvicorn src.api:app --reload --host 0.0.0.0 --port 8000`

### Option 2: SendGrid (Recommended for Production)

1. **Create a SendGrid Account**
   - Sign up at: https://sendgrid.com
   - Free tier: 100 emails/day

2. **Create an API Key**
   - Go to Settings → API Keys → Create API Key
   - Give it "Full Access" permission
   - Copy the API key

3. **Update Your `.env` File**
   ```env
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   SMTP_FROM_EMAIL=noreply@yourdomain.com
   ```

4. **Verify Your Sender Email**
   - In SendGrid, go to Settings → Sender Authentication
   - Verify either a single sender or your domain

5. **Restart the Backend**

### Option 3: Other SMTP Providers

Popular alternatives:
- **Mailgun**: https://www.mailgun.com
- **Amazon SES**: https://aws.amazon.com/ses/
- **Postmark**: https://postmarkapp.com

Configuration is similar - you'll need:
- SMTP server address
- Port (usually 587 or 465)
- Username (often your email or API key)
- Password (or API key)

## Testing Email Functionality

After configuring SMTP:

1. **Invite a Member to an Organization**
   - Log in as admin
   - Go to Organizations → Select an org → Members tab
   - Click "Invite Member"
   - Enter an email address
   - Click "Send Invitation"

2. **Check the Backend Logs**
   - You should see: `Email sent successfully to user@example.com`
   - If there's an error, it will show: `Failed to send email to user@example.com: [error message]`

3. **Check the Recipient's Inbox**
   - The email subject will be: "You've been invited to join [Organization Name]"
   - It contains an "Accept Invitation" button with a unique token

## Troubleshooting

### "Email not configured" Warning

If you see this in the logs:
```
Email not configured. Email would have been sent to: user@example.com
```

**Solution**: Your `.env` file still has placeholder values. Follow the setup steps above.

### "Authentication failed" Error

**Common causes**:
- Wrong username or password
- For Gmail: Not using an App Password (regular password won't work)
- For Gmail: 2-Step Verification not enabled

### "SMTP connection refused"

**Common causes**:
- Wrong SMTP server address
- Wrong port number
- Firewall blocking outgoing connections

### Emails Going to Spam

**Solutions**:
- Use a verified sender email address
- Add SPF and DKIM records to your domain
- For production, use a dedicated email service (SendGrid, Mailgun, etc.)

## Production Deployment

For Google Cloud Marketplace deployment:

1. **Use SendGrid or another dedicated email service** (not Gmail)

2. **Set environment variables in Cloud Run**:
   ```bash
   gcloud run services update ap2-expense-agent \
     --set-env-vars="SMTP_SERVER=smtp.sendgrid.net" \
     --set-env-vars="SMTP_PORT=587" \
     --set-env-vars="SMTP_USERNAME=apikey" \
     --set-env-vars="SMTP_PASSWORD=your-key-here" \
     --set-env-vars="SMTP_FROM_EMAIL=noreply@yourdomain.com"
   ```

3. **Or use Secret Manager** (recommended for sensitive data):
   ```bash
   # Store the password
   echo -n "your-smtp-password" | gcloud secrets create smtp-password --data-file=-

   # Grant Cloud Run access
   gcloud secrets add-iam-policy-binding smtp-password \
     --member="serviceAccount:YOUR-SERVICE-ACCOUNT@PROJECT.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   # Update Cloud Run to use the secret
   gcloud run services update ap2-expense-agent \
     --set-secrets="SMTP_PASSWORD=smtp-password:latest"
   ```

## Email Templates

The system sends these automated emails:

1. **Organization Invitation** (`send_organization_invitation_email`)
   - Sent when: Admin invites a member to an organization
   - Contains: Accept invitation link (expires in 7 days)

2. **Email Verification** (`send_verification_email`)
   - Sent when: User registers a new account
   - Contains: Email verification link

3. **Password Reset** (`send_password_reset_email`)
   - Sent when: User requests password reset
   - Contains: Password reset link (expires in 1 hour)

4. **GCP Marketplace Welcome** (`send_gcp_welcome_email`)
   - Sent when: New customer purchases from GCP Marketplace
   - Contains: Temporary password, login link, setup instructions

All templates are located in: `backend/src/email_service.py`

## Development Mode

For development/testing without real emails:

1. **Leave SMTP settings empty** in `.env`:
   ```env
   SMTP_SERVER=
   SMTP_USERNAME=
   SMTP_PASSWORD=
   ```

2. **Check the backend logs** - invitation details will be logged:
   ```
   Email not configured. Email would have been sent to: test@example.com
   Subject: You've been invited to join Acme Corp
   ```

3. **Manually copy the invitation token** from the database:
   ```sql
   SELECT token FROM organization_invitations WHERE email = 'test@example.com';
   ```

4. **Accept the invitation** by visiting:
   ```
   http://localhost:5173/invitations/accept/TOKEN_HERE
   ```

## Fixed Issues

✅ **Config mismatch fixed**: Added `smtp_from_email` to config.py (was missing)
✅ **Environment variables aligned**: `.env.example` now uses correct variable names
✅ **Silent failure documented**: Emails fail silently when SMTP not configured

## Next Steps

1. Choose an email provider (Gmail for dev, SendGrid for production)
2. Follow the setup steps above
3. Update your `.env` file with real credentials
4. Restart the backend
5. Test by inviting a member to an organization
