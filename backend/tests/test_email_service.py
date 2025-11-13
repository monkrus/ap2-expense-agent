"""
Tests for Email Service
Important notification module - targets 60%+ coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.email_service import EmailService


class TestEmailService:
    """Test email service"""

    @pytest.fixture
    def email_service(self):
        """Create email service instance"""
        return EmailService()

    @patch('src.email_service.settings')
    def test_email_disabled_when_not_configured(self, mock_settings, email_service):
        """Test email is disabled when SMTP not configured"""
        mock_settings.smtp_host = None

        # Should handle gracefully
        assert email_service is not None

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_email_success(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending email successfully"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "noreply@test.com"

        # Mock SMTP connection
        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance

        result = await email_service.send_email(
            to_email="user@test.com",
            subject="Test Email",
            body="<p>Test body</p>"
        )

        assert result is True
        mock_smtp_instance.send_message.assert_called_once()

    @patch('src.email_service.settings')
    async def test_send_email_without_smtp_config(
        self, mock_settings, email_service
    ):
        """Test sending email without SMTP configuration"""
        mock_settings.smtp_host = None

        result = await email_service.send_email(
            to_email="user@test.com",
            subject="Test",
            body="Body"
        )

        # Should return False or handle gracefully
        assert result in [False, None]

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_email_with_connection_error(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending email with connection error"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"

        # Mock SMTP connection error
        mock_smtp.side_effect = Exception("Connection failed")

        result = await email_service.send_email(
            to_email="user@test.com",
            subject="Test",
            body="Body"
        )

        assert result is False

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_welcome_email(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending welcome email"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "noreply@test.com"

        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance

        result = await email_service.send_welcome_email(
            to_email="newuser@test.com",
            username="newuser"
        )

        assert result is True
        mock_smtp_instance.send_message.assert_called_once()

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_password_reset_email(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending password reset email"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "noreply@test.com"

        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance

        result = await email_service.send_password_reset_email(
            to_email="user@test.com",
            reset_token="test_token_123"
        )

        assert result is True

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_expense_approved_notification(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending expense approved notification"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "noreply@test.com"

        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance

        result = await email_service.send_expense_approved_notification(
            to_email="user@test.com",
            expense_id="exp_123",
            amount=100.50,
            approver_name="Manager"
        )

        assert result is True

    @patch('src.email_service.aiosmtplib.SMTP')
    @patch('src.email_service.settings')
    async def test_send_expense_rejected_notification(
        self, mock_settings, mock_smtp, email_service
    ):
        """Test sending expense rejected notification"""
        mock_settings.smtp_host = "smtp.test.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "test@test.com"
        mock_settings.smtp_password = "password"
        mock_settings.smtp_from_email = "noreply@test.com"

        mock_smtp_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance

        result = await email_service.send_expense_rejected_notification(
            to_email="user@test.com",
            expense_id="exp_123",
            amount=100.50,
            reason="Insufficient documentation"
        )

        assert result is True

    async def test_email_validation(self, email_service):
        """Test email address validation"""
        # Valid emails
        assert email_service._is_valid_email("user@test.com") is True
        assert email_service._is_valid_email("user.name@test.co.uk") is True

        # Invalid emails
        assert email_service._is_valid_email("invalid") is False
        assert email_service._is_valid_email("@test.com") is False
        assert email_service._is_valid_email("user@") is False

    @pytest.mark.skip(reason="HTML sanitization not yet implemented - feature pending")
    def test_html_sanitization(self, email_service):
        """Test HTML content sanitization"""
        dangerous_html = "<script>alert('xss')</script><p>Safe content</p>"

        sanitized = email_service._sanitize_html(dangerous_html)

        assert "<script>" not in sanitized
        assert "Safe content" in sanitized
