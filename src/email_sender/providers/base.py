"""Base email provider interface."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

from ..models import EmailMessage, SendResult

logger = logging.getLogger(__name__)


class BaseEmailProvider(ABC):
    """Abstract base class for email providers."""

    def __init__(self, from_email: str):
        """Initialize the provider.

        Args:
            from_email: Default sender email address
        """
        self.from_email = from_email

    @abstractmethod
    def send(self, message: EmailMessage, correlation_id: str = None) -> SendResult:
        """Send an email message.

        Args:
            message: Email message to send
            correlation_id: Optional correlation ID for tracking

        Returns:
            SendResult with status and details
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the provider is properly configured and connected.

        Returns:
            True if connection is valid
        """
        pass

    def _get_from_email(self, message: EmailMessage) -> str:
        """Get the from email for a message.

        Args:
            message: Email message

        Returns:
            From email address
        """
        return message.from_email or self.from_email
