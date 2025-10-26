"""
Email Service for sending verification and password reset emails
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP
        Returns True if successful, False otherwise
        """
        # Check if email is configured
        if not settings.smtp_server or not settings.smtp_username:
            logger.warning("Email not configured. Email would have been sent to: %s", to_email)
            logger.warning("Subject: %s", subject)
            logger.warning("Body: %s", text_body or html_body[:100])
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.smtp_from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add text and HTML parts
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)

            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)

            logger.info("Email sent successfully to %s", to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def send_verification_email(
        to_email: str,
        username: str,
        verification_token: str,
        base_url: str = None
    ) -> bool:
        """Send email verification link"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        verification_link = f"{base_url}/auth/verify-email?token={verification_token}"

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
                    <h2>Hi {username},</h2>
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

        return EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    def send_password_reset_email(
        to_email: str,
        username: str,
        reset_token: str,
        base_url: str = None
    ) -> bool:
        """Send password reset link"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        reset_link = f"{base_url}/auth/reset-password?token={reset_token}"

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
                    <h2>Hi {username},</h2>
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

        return EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    def send_welcome_email(
        to_email: str,
        username: str,
        full_name: str
    ) -> bool:
        """Send welcome email after email verification"""
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
                    <h2>Hi {full_name or username},</h2>
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

        return EmailService.send_email(to_email, subject, html_body, text_body)

    @staticmethod
    def send_organization_invitation_email(
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invitation_token: str,
        base_url: str = None
    ) -> bool:
        """Send organization invitation email"""
        if not base_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        invitation_link = f"{base_url}/invitations/accept?token={invitation_token}"

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
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on AP2 Expense Manager.</p>

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

        return EmailService.send_email(to_email, subject, html_body, text_body)
