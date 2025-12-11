"""Mock email provider for testing and preview operations."""

from ..models import EmailMessage, SendResult, SendStatus
from .base import BaseEmailProvider


class MockEmailProvider(BaseEmailProvider):
    """Mock email provider that doesn't actually send emails."""

    def send(self, message: EmailMessage, correlation_id: str = None) -> SendResult:
        """Pretend to send an email.

        Args:
            message: Email message to send
            correlation_id: Optional correlation ID for tracking

        Returns:
            SendResult with success status
        """
        return SendResult(
            recipient=message.recipient,
            status=SendStatus.SUCCESS,
            message_id=f"mock-{correlation_id or 'test'}",
            correlation_id=correlation_id,
        )

    def validate_connection(self) -> bool:
        """Validate connection (always succeeds for mock).

        Returns:
            True
        """
        return True
