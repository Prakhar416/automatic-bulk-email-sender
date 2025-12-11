"""Tests for email sender."""

import pytest
from unittest.mock import Mock, patch

from email_sender.sender import EmailSender
from email_sender.models import SendStatus
from email_sender.exceptions import ValidationError, TemplateError


class TestEmailSender:
    """Tests for EmailSender."""

    def test_preview_template(self, sample_template):
        """Test previewing a template."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        preview = sender.preview_template("test", {"name": "John", "company": "Acme"})

        assert preview["template_name"] == "test"
        assert "John" in preview["html_preview"]

    def test_preview_template_missing_required_variable(self, sample_template):
        """Test preview with missing required variable."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        with pytest.raises(ValidationError):
            sender.preview_template("test", {"company": "Acme"})

    def test_send_test_email(self, sample_template):
        """Test sending a test email."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        result = sender.send_test_email(
            "test",
            "user@example.com",
            {"name": "John", "company": "Acme"},
        )

        assert result.recipient == "user@example.com"
        assert result.status == SendStatus.SUCCESS

    def test_send_test_email_invalid_email(self, sample_template):
        """Test sending test email with invalid email."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        result = sender.send_test_email(
            "test",
            "invalid-email",
            {"name": "John", "company": "Acme"},
        )

        assert result.status == SendStatus.SKIPPED
        assert "Invalid email" in result.error_reason

    def test_send_test_email_missing_field(self, sample_template):
        """Test sending test email with missing required field."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        result = sender.send_test_email(
            "test",
            "user@example.com",
            {"company": "Acme"},  # missing 'name'
        )

        assert result.status == SendStatus.SKIPPED
        assert "Missing required fields" in result.error_reason

    def test_send_bulk_emails(self, sample_template, sample_recipients):
        """Test sending bulk emails."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        results = sender.send_bulk_emails("test", sample_recipients)

        assert len(results) == len(sample_recipients)
        # First two should succeed, third should be skipped (invalid email)
        assert results[0].status == SendStatus.SUCCESS
        assert results[1].status == SendStatus.SUCCESS
        assert results[2].status == SendStatus.SKIPPED

    def test_validate_provider(self, sample_template):
        """Test provider validation."""
        from email_sender.providers.mock import MockEmailProvider

        provider = MockEmailProvider("sender@example.com")
        sender = EmailSender(str(sample_template), provider)

        assert sender.validate_provider() is True
