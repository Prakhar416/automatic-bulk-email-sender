"""Email validation utilities."""

from typing import Tuple
from email_validator import validate_email, EmailNotValidError

from .exceptions import ValidationError


def validate_email_address(email: str) -> Tuple[bool, str]:
    """Validate an email address.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        valid = validate_email(email, check_deliverability=False)
        return True, valid.normalized
    except EmailNotValidError as e:
        return False, str(e)


def validate_recipient_fields(
    recipient: dict, required_fields: list, optional_fields: list = None
) -> Tuple[bool, list]:
    """Validate that a recipient has all required fields.

    Args:
        recipient: Recipient dictionary
        required_fields: List of required field names
        optional_fields: List of optional field names

    Returns:
        Tuple of (is_valid, missing_fields)
    """
    optional_fields = optional_fields or []
    missing = []

    for field in required_fields:
        if field not in recipient or recipient[field] is None:
            missing.append(field)

    return len(missing) == 0, missing
