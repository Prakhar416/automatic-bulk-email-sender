"""Tests for data models."""

import pytest
from datetime import datetime

from email_sender.models import (
    EmailMessage,
    TemplateMetadata,
    SendResult,
    SendStatus,
)


class TestEmailMessage:
    """Tests for EmailMessage model."""

    def test_create_with_html_body(self):
        """Test creating message with HTML body."""
        msg = EmailMessage(
            recipient="user@example.com",
            subject="Test",
            html_body="<h1>Test</h1>",
        )

        assert msg.recipient == "user@example.com"
        assert msg.html_body == "<h1>Test</h1>"

    def test_create_with_text_body(self):
        """Test creating message with text body."""
        msg = EmailMessage(
            recipient="user@example.com",
            subject="Test",
            text_body="Test",
        )

        assert msg.text_body == "Test"

    def test_create_without_body_raises_error(self):
        """Test that creating message without body raises error."""
        with pytest.raises(ValueError):
            EmailMessage(
                recipient="user@example.com",
                subject="Test",
            )

    def test_message_with_metadata(self):
        """Test creating message with metadata."""
        msg = EmailMessage(
            recipient="user@example.com",
            subject="Test",
            html_body="<h1>Test</h1>",
            metadata={"correlation_id": "123"},
        )

        assert msg.metadata["correlation_id"] == "123"


class TestTemplateMetadata:
    """Tests for TemplateMetadata model."""

    def test_create_metadata(self):
        """Test creating template metadata."""
        metadata = TemplateMetadata(
            name="Welcome",
            subject="Welcome {{ name }}",
            required_variables=["name"],
            optional_variables=["company"],
        )

        assert metadata.name == "Welcome"
        assert "name" in metadata.required_variables
        assert "company" in metadata.optional_variables


class TestSendResult:
    """Tests for SendResult model."""

    def test_successful_send_result(self):
        """Test creating successful send result."""
        result = SendResult(
            recipient="user@example.com",
            status=SendStatus.SUCCESS,
            message_id="abc123",
            correlation_id="uuid-123",
        )

        assert result.status == SendStatus.SUCCESS
        assert result.message_id == "abc123"

    def test_failed_send_result(self):
        """Test creating failed send result."""
        result = SendResult(
            recipient="user@example.com",
            status=SendStatus.FAILED,
            error_reason="Connection timeout",
            correlation_id="uuid-123",
        )

        assert result.status == SendStatus.FAILED
        assert result.error_reason == "Connection timeout"

    def test_send_result_to_dict(self):
        """Test converting send result to dictionary."""
        result = SendResult(
            recipient="user@example.com",
            status=SendStatus.SUCCESS,
            message_id="abc123",
            correlation_id="uuid-123",
        )

        result_dict = result.to_dict()

        assert result_dict["recipient"] == "user@example.com"
        assert result_dict["status"] == "success"
        assert result_dict["message_id"] == "abc123"
        assert result_dict["correlation_id"] == "uuid-123"
