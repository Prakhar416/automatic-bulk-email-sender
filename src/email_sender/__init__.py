"""Automatic bulk email sender with Jinja2 templates and multiple provider support."""

__version__ = "0.1.0"

from .exceptions import (
    EmailSenderError,
    TemplateError,
    ProviderError,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    DeliveryError,
)
from .models import EmailMessage, TemplateMetadata, SendResult, SendStatus
from .template import TemplateLoader
from .sender import EmailSender
from .providers import GmailProvider, SendGridProvider
from .validators import validate_email_address, validate_recipient_fields

__all__ = [
    "EmailSenderError",
    "TemplateError",
    "ProviderError",
    "ValidationError",
    "AuthenticationError",
    "RateLimitError",
    "DeliveryError",
    "EmailMessage",
    "TemplateMetadata",
    "SendResult",
    "SendStatus",
    "TemplateLoader",
    "EmailSender",
    "GmailProvider",
    "SendGridProvider",
    "validate_email_address",
    "validate_recipient_fields",
]
