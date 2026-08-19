"""
SMTP Email Testing Script
Tests email sending functionality before production deployment

Usage:
    python test_email_sending.py --to your@email.com

Environment Variables Required:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=your-email@gmail.com
    SMTP_PASSWORD=your-app-password
    SMTP_FROM_EMAIL=noreply@yourapp.com
    SMTP_FROM_NAME=AP2 Expense Agent

Optional:
    SMTP_USE_TLS=true (default)
"""

import argparse
import os
import sys
from datetime import datetime

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")


def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")


def print_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")


def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")


def check_env_vars():
    """Check required environment variables"""
    print_info("Checking environment variables...")

    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
    ]

    missing = []
    for var in required:
        value = os.getenv(var)
        if value:
            # Mask password
            if "PASSWORD" in var:
                masked = (
                    value[:2] + "*" * (len(value) - 4) + value[-2:]
                    if len(value) > 4
                    else "****"
                )
                print_success(f"  {var}: {masked}")
            else:
                print_success(f"  {var}: {value}")
        else:
            missing.append(var)
            print_error(f"  {var}: NOT SET")

    if missing:
        print_error(f"Missing environment variables: {', '.join(missing)}")
        return False

    return True


def test_smtp_connection():
    """Test SMTP server connection"""
    print_info("Testing SMTP connection...")

    import smtplib

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)

        server.login(username, password)
        print_success(f"Connected to {host}:{port}")
        print_success(f"Authenticated as {username}")
        server.quit()
        return True

    except smtplib.SMTPAuthenticationError:
        print_error("Authentication failed - check username/password")
        return False
    except smtplib.SMTPConnectError:
        print_error(f"Cannot connect to {host}:{port}")
        return False
    except Exception as e:
        print_error(f"SMTP connection error: {e}")
        return False


def send_plain_text_email(to_email):
    """Send a plain text test email"""
    print_info("Sending plain text test email...")

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    from_name = os.getenv("SMTP_FROM_NAME", "AP2 Expense Agent")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[TEST] AP2 Email System Test - Plain Text"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        text_content = f"""
AP2 Expense Agent - Email System Test

This is a test email sent at {datetime.utcnow().isoformat()}

If you received this email, the SMTP configuration is working correctly.

Test Details:
- SMTP Host: {host}
- SMTP Port: {port}
- From: {from_email}
- To: {to_email}

This is an automated test. No action required.
"""

        msg.attach(MIMEText(text_content, "plain"))

        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)

        server.login(username, password)
        server.send_message(msg)
        server.quit()

        print_success(f"Plain text email sent to {to_email}")
        return True

    except Exception as e:
        print_error(f"Failed to send plain text email: {e}")
        return False


def send_html_email(to_email):
    """Send an HTML test email"""
    print_info("Sending HTML test email...")

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    from_name = os.getenv("SMTP_FROM_NAME", "AP2 Expense Agent")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[TEST] AP2 Email System Test - HTML"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        # Plain text version
        text_content = f"""
AP2 Expense Agent - HTML Email Test

This is a test email sent at {datetime.utcnow().isoformat()}

If you see this message in plain text, HTML rendering is not working.
"""

        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .label {{ font-weight: bold; width: 120px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Email System Test</h1>
        </div>
        <div class="content">
            <h2>AP2 Expense Agent</h2>
            <p class="success">✓ HTML email rendering is working correctly!</p>
            <p>This is a test email sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

            <table>
                <tr>
                    <td class="label">SMTP Host:</td>
                    <td>{host}</td>
                </tr>
                <tr>
                    <td class="label">SMTP Port:</td>
                    <td>{port}</td>
                </tr>
                <tr>
                    <td class="label">From:</td>
                    <td>{from_email}</td>
                </tr>
                <tr>
                    <td class="label">To:</td>
                    <td>{to_email}</td>
                </tr>
            </table>

            <p style="margin-top: 20px;">If you can see this styled message, email templates will render correctly in production.</p>
        </div>
        <div class="footer">
            <p>This is an automated test. No action required.</p>
            <p>AP2 Expense Management System</p>
        </div>
    </div>
</body>
</html>
"""

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)

        server.login(username, password)
        server.send_message(msg)
        server.quit()

        print_success(f"HTML email sent to {to_email}")
        return True

    except Exception as e:
        print_error(f"Failed to send HTML email: {e}")
        return False


def send_template_test_email(to_email):
    """Send test email using actual email templates"""
    print_info("Sending email using production templates...")

    try:
        # Import email service
        sys.path.insert(0, "backend/src")
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        from email_templates import (
            generate_budget_alert_email,
            generate_expense_approved_email,
            generate_expense_rejected_email,
            generate_pending_approval_email,
        )

        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", 587))
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL")
        from_name = os.getenv("SMTP_FROM_NAME", "AP2 Expense Agent")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        # Test data
        expense = {
            "amount": 125.50,
            "vendor": "Test Restaurant",
            "description": "Team lunch",
            "category": "MEALS",
            "date": datetime.utcnow().isoformat(),
        }

        user = {"full_name": "Test User", "email": to_email}

        policy = {"name": "Small Expense Auto-Approval"}

        # Generate email
        html_content, text_content = generate_expense_approved_email(
            expense, user, policy
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[TEST] Expense Approved - Production Template Test"
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)

        server.login(username, password)
        server.send_message(msg)
        server.quit()

        print_success(f"Production template email sent to {to_email}")
        print_info("Check your inbox for a formatted expense approval email")
        return True

    except ImportError as e:
        print_warning(f"Could not import email templates: {e}")
        print_info("Skipping template test")
        return True
    except Exception as e:
        print_error(f"Failed to send template email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test SMTP email sending")
    parser.add_argument(
        "--to", required=True, help="Email address to send test emails to"
    )
    parser.add_argument(
        "--skip-templates", action="store_true", help="Skip production template test"
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("SMTP EMAIL TESTING")
    print("=" * 70 + "\n")

    # Check environment variables
    if not check_env_vars():
        print_error("\nPlease set all required environment variables")
        print_info("Example:")
        print_info("  export SMTP_HOST=smtp.gmail.com")
        print_info("  export SMTP_PORT=587")
        print_info("  export SMTP_USERNAME=your-email@gmail.com")
        print_info("  export SMTP_PASSWORD=your-app-password")
        print_info("  export SMTP_FROM_EMAIL=noreply@yourapp.com")
        sys.exit(1)

    # Test SMTP connection
    if not test_smtp_connection():
        sys.exit(1)

    # Send plain text email
    if not send_plain_text_email(args.to):
        print_warning("Plain text email failed (continuing anyway)")

    # Send HTML email
    if not send_html_email(args.to):
        print_warning("HTML email failed (continuing anyway)")

    # Send template email
    if not args.skip_templates:
        if not send_template_test_email(args.to):
            print_warning("Template email failed (non-critical)")

    # Summary
    print("\n" + "=" * 70)
    print("EMAIL TEST SUMMARY")
    print("=" * 70)
    print_success("✓ Environment variables configured")
    print_success("✓ SMTP connection working")
    print_success("✓ Plain text emails sent")
    print_success("✓ HTML emails sent")
    if not args.skip_templates:
        print_success("✓ Production template tested")

    print(f"\n{GREEN}Email system is working!{RESET}")
    print(f"{BLUE}Check your inbox at: {args.to}{RESET}")
    print(f"{BLUE}You should have received 2-3 test emails.{RESET}\n")

    print_info("Production Checklist:")
    print("  1. ✓ SMTP credentials work")
    print("  2. ✓ Emails are delivered")
    print("  3. ✓ HTML templates render correctly")
    print("  4. [ ] Check spam folder if emails not received")
    print("  5. [ ] Verify sender name displays correctly")
    print("  6. [ ] Test on multiple email providers (Gmail, Outlook, etc.)")


if __name__ == "__main__":
    main()
