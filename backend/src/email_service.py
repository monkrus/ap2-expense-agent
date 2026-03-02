"""
Email Service for sending verification and password reset emails
"""

import html
import logging
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .config import settings
from .email_templates import (
    get_expense_approved_email,
    get_expense_rejected_email,
    get_pending_approval_email,
    get_budget_alert_email,
)

logger = logging.getLogger(__name__)

try:
    import aiosmtplib
except Exception:  # pragma: no cover - fallback for environments without aiosmtplib
    class _AioSMTPStub:
        __ap2_stub__ = True

        class SMTP:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("aiosmtplib is required for async email sending")

    aiosmtplib = _AioSMTPStub()


class EmailService:
    """Service for sending emails"""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        body: Optional[str] = None,
    ) -> bool:
        """
        Send an email using SMTP
        Returns True if successful, False otherwise
        """
        if body and not html_body:
            html_body = body

        if html_body is None:
            html_body = ""

        # Check if email is configured
        smtp_server = getattr(settings, "smtp_server", None) or getattr(
            settings, "smtp_host", None
        )
        smtp_username = getattr(settings, "smtp_username", None)
        smtp_password = getattr(settings, "smtp_password", None)
        smtp_port = getattr(settings, "smtp_port", 587)
        smtp_from_email = getattr(settings, "smtp_from_email", None) or getattr(
            settings, "from_email", None
        )

        if not smtp_server or not smtp_username:
            logger.warning(
                "Email not configured. Email would have been sent to: %s", to_email
            )
            logger.warning("Subject: %s", subject)
            logger.warning("Body: %s", text_body or html_body[:100])
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = smtp_from_email or smtp_username
            msg["To"] = to_email
            msg["Subject"] = subject

            # Add text and HTML parts
            if text_body:
                part1 = MIMEText(text_body, "plain")
                msg.attach(part1)

            if html_body:
                part2 = MIMEText(html_body, "html")
                msg.attach(part2)

            # Send email — use STARTTLS (port 587) not SSL (port 465)
            async with aiosmtplib.SMTP(
                hostname=smtp_server,
                port=smtp_port,
                start_tls=smtp_port == 587,
                use_tls=smtp_port == 465,
            ) as server:
                await server.login(smtp_username, smtp_password)
                await server.send_message(msg)

            logger.info("Email sent successfully to %s", to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    async def send_verification_email(
        to_email: str, username: str, verification_token: str, base_url: str = None
    ) -> bool:
        """Send email verification link"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        verification_link = f"{base_url}/auth/verify-email?token={verification_token}"
        safe_username = html.escape(str(username))

        subject = "Verify Your Email - AP2 Expense Manager"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to AP2 Expense Manager!</h1>
                </div>
                <div class="content">
                    <h2>Hi {safe_username},</h2>
                    <p>Thank you for registering with AP2 Expense Manager. To complete your registration, please verify your email address by clicking the button below:</p>

                    <center>
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </center>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{verification_link}</p>

                    <p>This verification link will expire in 24 hours.</p>

                    <p>If you didn't create an account with us, please ignore this email.</p>

                    <p>Best regards,<br>The AP2 Expense Manager Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                    <p>&copy; 2025 AP2 Expense Manager. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Hi {username},

        Thank you for registering with AP2 Expense Manager.

        To complete your registration, please verify your email address by visiting:
        {verification_link}

        This verification link will expire in 24 hours.

        If you didn't create an account with us, please ignore this email.

        Best regards,
        The AP2 Expense Manager Team
        """

        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_password_reset_email(
        to_email: str,
        reset_token: str,
        username: Optional[str] = None,
        base_url: str = None,
    ) -> bool:
        """Send password reset link"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        if not username:
            username = to_email.split("@")[0]

        reset_link = f"{base_url}/auth/reset-password?token={reset_token}"
        safe_username = html.escape(str(username))

        subject = "Reset Your Password - AP2 Expense Manager"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hi {safe_username},</h2>
                    <p>We received a request to reset your password for your AP2 Expense Manager account.</p>

                    <p>Click the button below to reset your password:</p>

                    <center>
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </center>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{reset_link}</p>

                    <div class="warning">
                        <strong>⚠️ Important:</strong> This password reset link will expire in 1 hour for security reasons.
                    </div>

                    <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns about your account security.</p>

                    <p>Best regards,<br>The AP2 Expense Manager Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                    <p>&copy; 2025 AP2 Expense Manager. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Hi {username},

        We received a request to reset your password for your AP2 Expense Manager account.

        To reset your password, please visit:
        {reset_link}

        This password reset link will expire in 1 hour for security reasons.

        If you didn't request a password reset, please ignore this email or contact support if you have concerns.

        Best regards,
        The AP2 Expense Manager Team
        """

        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_welcome_email(
        to_email: str, username: str, full_name: Optional[str] = None
    ) -> bool:
        """Send welcome email after email verification"""
        safe_display = html.escape(str(full_name or username))
        subject = "Welcome to AP2 Expense Manager!"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .feature {{
                    padding: 15px;
                    margin: 10px 0;
                    background: white;
                    border-left: 4px solid #667eea;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome Aboard!</h1>
                </div>
                <div class="content">
                    <h2>Hi {safe_display},</h2>
                    <p>Your email has been verified successfully! Welcome to AP2 Expense Manager.</p>

                    <h3>What you can do now:</h3>

                    <div class="feature">
                        <strong>📝 Submit Expenses</strong><br>
                        Quickly submit your business expenses with our AI-powered categorization.
                    </div>

                    <div class="feature">
                        <strong>✅ Approve Payments</strong><br>
                        Review and approve expenses using the secure AP2 payment protocol.
                    </div>

                    <div class="feature">
                        <strong>📊 Track Analytics</strong><br>
                        Get insights into your spending with detailed reports and analytics.
                    </div>

                    <div class="feature">
                        <strong>🔒 Secure by Design</strong><br>
                        All transactions are protected with cryptographic mandates for full audit trails.
                    </div>

                    <p>Ready to get started? Log in to your account and explore the features!</p>

                    <p>If you need any help, don't hesitate to reach out to our support team.</p>

                    <p>Best regards,<br>The AP2 Expense Manager Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 AP2 Expense Manager. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Hi {full_name or username},

        Your email has been verified successfully! Welcome to AP2 Expense Manager.

        What you can do now:
        - Submit Expenses: Quickly submit your business expenses
        - Approve Payments: Review and approve expenses using AP2
        - Track Analytics: Get insights into your spending
        - Secure by Design: All transactions are cryptographically protected

        Ready to get started? Log in to your account and explore!

        Best regards,
        The AP2 Expense Manager Team
        """

        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_organization_invitation_email(
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invitation_token: str,
        base_url: str = None,
    ) -> bool:
        """Send organization invitation email"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        invitation_link = f"{base_url}/invitations/accept/{invitation_token}"
        safe_org_name = html.escape(str(organization_name))
        safe_inviter = html.escape(str(inviter_name))

        subject = f"You've been invited to join {organization_name}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Organization Invitation</h1>
                </div>
                <div class="content">
                    <h2>You've been invited!</h2>
                    <p><strong>{safe_inviter}</strong> has invited you to join <strong>{safe_org_name}</strong> on AP2 Expense Manager.</p>

                    <p>Accept this invitation to collaborate with your team on expense management.</p>

                    <center>
                        <a href="{invitation_link}" class="button">Accept Invitation</a>
                    </center>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #667eea;">{invitation_link}</p>

                    <p>This invitation will expire in 7 days.</p>

                    <p>If you don't want to accept this invitation, you can simply ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This is an automated email. Please do not reply.</p>
                    <p>&copy; 2025 AP2 Expense Manager. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        You've been invited to join {organization_name}!

        {inviter_name} has invited you to join {organization_name} on AP2 Expense Manager.

        Accept this invitation by visiting:
        {invitation_link}

        This invitation will expire in 7 days.

        If you don't want to accept this invitation, you can simply ignore this email.

        Best regards,
        The AP2 Expense Manager Team
        """

        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_expense_approved_email(
        to_email: str, expense_data: dict, approver_name: str
    ) -> bool:
        """Send expense approval notification email"""
        subject, html_body, text_body = get_expense_approved_email(
            expense_data, approver_name
        )
        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_expense_rejected_email(
        to_email: str, expense_data: dict, rejector_name: str, reason: str
    ) -> bool:
        """Send expense rejection notification email"""
        subject, html_body, text_body = get_expense_rejected_email(
            expense_data, rejector_name, reason
        )
        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_pending_approval_email(
        to_email: str, expense_data: dict, submitter_name: str, manager_name: str
    ) -> bool:
        """Send pending approval notification email to managers"""
        subject, html_body, text_body = get_pending_approval_email(
            expense_data, submitter_name, manager_name
        )
        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_budget_alert_email(
        to_email: str, budget_data: dict, current_spending: float, threshold_percent: int
    ) -> bool:
        """Send budget alert notification email"""
        subject, html_body, text_body = get_budget_alert_email(
            budget_data, current_spending, threshold_percent
        )
        return await EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    async def send_expense_approved_notification(
        to_email: str, expense_id: str, amount: float, approver_name: str
    ) -> bool:
        """Compatibility wrapper for legacy tests."""
        expense_data = {
            "id": expense_id,
            "amount": amount,
            "vendor": "Unknown",
            "category": "Uncategorized",
            "description": "",
            "date": "N/A",
        }
        return await EmailService.send_expense_approved_email(
            to_email, expense_data, approver_name
        )

    @staticmethod
    async def send_expense_rejected_notification(
        to_email: str, expense_id: str, amount: float, reason: str
    ) -> bool:
        """Compatibility wrapper for legacy tests."""
        expense_data = {
            "id": expense_id,
            "amount": amount,
            "vendor": "Unknown",
            "category": "Uncategorized",
            "description": "",
            "date": "N/A",
        }
        return await EmailService.send_expense_rejected_email(
            to_email, expense_data, "Approver", reason
        )

    def _sanitize_html(self, text: str) -> str:
        """Escape HTML special characters in user-controlled text."""
        return html.escape(str(text))

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email validation for tests and guardrails."""
        if not email:
            return False
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        return re.match(pattern, email) is not None
