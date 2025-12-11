"""Tests for validators."""

import pytest

from email_sender.validators import validate_email_address, validate_recipient_fields


class TestEmailValidator:
    """Tests for email validation."""

    def test_valid_email(self):
        """Test validating a valid email."""
        is_valid, error = validate_email_address("user@example.com")
        assert is_valid is True

    def test_invalid_email_format(self):
        """Test validating invalid email format."""
        is_valid, error = validate_email_address("invalid-email")
        assert is_valid is False

    def test_invalid_email_empty(self):
        """Test validating empty email."""
        is_valid, error = validate_email_address("")
        assert is_valid is False


class TestRecipientFieldValidator:
    """Tests for recipient field validation."""

    def test_all_required_fields_present(self):
        """Test validation when all required fields are present."""
        recipient = {"name": "John", "email": "john@example.com"}
        is_valid, missing = validate_recipient_fields(recipient, ["name", "email"])

        assert is_valid is True
        assert len(missing) == 0

    def test_missing_required_field(self):
        """Test validation with missing required field."""
        recipient = {"name": "John"}
        is_valid, missing = validate_recipient_fields(recipient, ["name", "email"])

        assert is_valid is False
        assert "email" in missing

    def test_none_values_treated_as_missing(self):
        """Test that None values are treated as missing."""
        recipient = {"name": "John", "email": None}
        is_valid, missing = validate_recipient_fields(recipient, ["name", "email"])

        assert is_valid is False
        assert "email" in missing

    def test_optional_fields_not_required(self):
        """Test that optional fields are not required."""
        recipient = {"name": "John"}
        is_valid, missing = validate_recipient_fields(
            recipient, ["name"], ["company"]
        )

        assert is_valid is True
