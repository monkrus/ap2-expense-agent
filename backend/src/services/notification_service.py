"""
Email notification service for expense management system.
Sends notifications for expense lifecycle events.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from datetime import datetime
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email notifications."""

    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.from_email
        self.enabled = settings.notifications_enabled

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (fallback)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Notifications disabled. Would have sent: {subject} to {to_email}")
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Add plain text version
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def notify_expense_submitted(
        self,
        expense_id: str,
        employee_name: str,
        employee_email: str,
        amount: float,
        category: str,
        description: str
    ) -> bool:
        """Notify employee that their expense was submitted."""
        subject = f"Expense Submitted: {expense_id}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5;">Expense Submitted Successfully</h2>
                <p>Hi {employee_name},</p>
                <p>Your expense has been submitted and is awaiting approval.</p>

                <div style="background-color: #F3F4F6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Expense ID:</strong> {expense_id}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                    <p style="margin: 5px 0;"><strong>Category:</strong> {category}</p>
                    <p style="margin: 5px 0;"><strong>Description:</strong> {description}</p>
                </div>

                <p>You'll receive another email once your expense has been reviewed.</p>

                <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
                    Powered by AP2 Expense Management
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Expense Submitted Successfully

        Hi {employee_name},

        Your expense has been submitted and is awaiting approval.

        Expense ID: {expense_id}
        Amount: ${amount:.2f}
        Category: {category}
        Description: {description}

        You'll receive another email once your expense has been reviewed.

        Powered by AP2 Expense Management
        """

        return self._send_email(employee_email, subject, html_body, text_body)

    def notify_expense_approved(
        self,
        expense_id: str,
        employee_name: str,
        employee_email: str,
        amount: float,
        approved_by: str,
        transaction_id: str
    ) -> bool:
        """Notify employee that their expense was approved."""
        subject = f"✅ Expense Approved: {expense_id}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #10B981; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0;">✅ Expense Approved!</h2>
                </div>

                <p>Hi {employee_name},</p>
                <p>Great news! Your expense has been approved.</p>

                <div style="background-color: #F3F4F6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Expense ID:</strong> {expense_id}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                    <p style="margin: 5px 0;"><strong>Approved By:</strong> {approved_by}</p>
                    <p style="margin: 5px 0;"><strong>Transaction ID:</strong> {transaction_id}</p>
                </div>

                <p>Payment is being processed via the AP2 protocol. You'll receive reimbursement according to your company's payment schedule.</p>

                <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
                    Powered by AP2 Expense Management
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Expense Approved!

        Hi {employee_name},

        Great news! Your expense has been approved.

        Expense ID: {expense_id}
        Amount: ${amount:.2f}
        Approved By: {approved_by}
        Transaction ID: {transaction_id}

        Payment is being processed via the AP2 protocol.

        Powered by AP2 Expense Management
        """

        return self._send_email(employee_email, subject, html_body, text_body)

    def notify_expense_rejected(
        self,
        expense_id: str,
        employee_name: str,
        employee_email: str,
        amount: float,
        rejected_by: str,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """Notify employee that their expense was rejected."""
        subject = f"❌ Expense Rejected: {expense_id}"

        reason_html = ""
        reason_text = ""
        if rejection_reason:
            reason_html = f"""
            <div style="background-color: #FEE2E2; padding: 15px; border-radius: 8px; border-left: 4px solid #EF4444; margin: 20px 0;">
                <p style="margin: 0;"><strong>Rejection Reason:</strong></p>
                <p style="margin: 10px 0 0 0;">{rejection_reason}</p>
            </div>
            """
            reason_text = f"\nRejection Reason: {rejection_reason}\n"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #EF4444; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0;">❌ Expense Rejected</h2>
                </div>

                <p>Hi {employee_name},</p>
                <p>Your expense has been rejected by {rejected_by}.</p>

                <div style="background-color: #F3F4F6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Expense ID:</strong> {expense_id}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                    <p style="margin: 5px 0;"><strong>Rejected By:</strong> {rejected_by}</p>
                </div>

                {reason_html}

                <p>If you have questions about this rejection, please contact your manager or the finance team.</p>

                <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
                    Powered by AP2 Expense Management
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Expense Rejected

        Hi {employee_name},

        Your expense has been rejected by {rejected_by}.

        Expense ID: {expense_id}
        Amount: ${amount:.2f}
        Rejected By: {rejected_by}
        {reason_text}

        If you have questions, please contact your manager or finance team.

        Powered by AP2 Expense Management
        """

        return self._send_email(employee_email, subject, html_body, text_body)

    def notify_manager_new_expense(
        self,
        expense_id: str,
        employee_name: str,
        employee_email: str,
        manager_email: str,
        amount: float,
        category: str,
        description: str
    ) -> bool:
        """Notify manager of a new expense awaiting approval."""
        subject = f"🔔 New Expense Awaiting Approval: {expense_id}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #F59E0B; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0;">🔔 New Expense Awaiting Approval</h2>
                </div>

                <p>A new expense has been submitted and requires your review.</p>

                <div style="background-color: #F3F4F6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Employee:</strong> {employee_name} ({employee_email})</p>
                    <p style="margin: 5px 0;"><strong>Expense ID:</strong> {expense_id}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                    <p style="margin: 5px 0;"><strong>Category:</strong> {category}</p>
                    <p style="margin: 5px 0;"><strong>Description:</strong> {description}</p>
                </div>

                <p>Please log in to the expense management system to review and approve or reject this expense.</p>

                <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
                    Powered by AP2 Expense Management
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        New Expense Awaiting Approval

        A new expense has been submitted and requires your review.

        Employee: {employee_name} ({employee_email})
        Expense ID: {expense_id}
        Amount: ${amount:.2f}
        Category: {category}
        Description: {description}

        Please log in to the expense management system to review this expense.

        Powered by AP2 Expense Management
        """

        return self._send_email(manager_email, subject, html_body, text_body)

    def notify_comment_added(
        self,
        expense_id: str,
        recipient_name: str,
        recipient_email: str,
        commenter_name: str,
        comment_text: str,
        amount: float
    ) -> bool:
        """Notify when a comment is added to an expense."""
        subject = f"💬 New Comment on Expense: {expense_id}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #6366F1; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0;">💬 New Comment Added</h2>
                </div>

                <p>Hi {recipient_name},</p>
                <p>{commenter_name} added a comment to expense {expense_id}:</p>

                <div style="background-color: #EEF2FF; padding: 15px; border-radius: 8px; border-left: 4px solid #6366F1; margin: 20px 0;">
                    <p style="margin: 0; font-style: italic;">"{comment_text}"</p>
                </div>

                <div style="background-color: #F3F4F6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Expense ID:</strong> {expense_id}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                </div>

                <p>Please log in to the expense management system to view and respond.</p>

                <p style="color: #6B7280; font-size: 12px; margin-top: 30px;">
                    Powered by AP2 Expense Management
                </p>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        New Comment Added

        Hi {recipient_name},

        {commenter_name} added a comment to expense {expense_id}:

        "{comment_text}"

        Expense ID: {expense_id}
        Amount: ${amount:.2f}

        Please log in to view and respond.

        Powered by AP2 Expense Management
        """

        return self._send_email(recipient_email, subject, html_body, text_body)


# Singleton instance
notification_service = NotificationService()
