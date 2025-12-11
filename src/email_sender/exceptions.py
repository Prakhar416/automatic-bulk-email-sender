"""Custom exceptions for email sender."""


class EmailSenderError(Exception):
    """Base exception for all email sender errors."""

    pass


class TemplateError(EmailSenderError):
    """Raised when there's an error with template loading or rendering."""

    pass


class ProviderError(EmailSenderError):
    """Raised when there's an error with the email provider."""

    pass


class ValidationError(EmailSenderError):
    """Raised when validation fails."""

    pass


class AuthenticationError(ProviderError):
    """Raised when authentication with the provider fails."""

    pass


class RateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""

    pass


class DeliveryError(ProviderError):
    """Raised when email delivery fails."""

    pass
