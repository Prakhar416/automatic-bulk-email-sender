"""SendGrid email provider."""

import logging
import time
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import requests

from ..models import EmailMessage, SendResult, SendStatus
from ..exceptions import (
    ProviderError,
    AuthenticationError,
    RateLimitError,
    DeliveryError,
)
from .base import BaseEmailProvider

logger = logging.getLogger(__name__)


class SendGridProvider(BaseEmailProvider):
    """SendGrid email provider."""

    def __init__(self, from_email: str, api_key: str):
        """Initialize SendGrid provider.

        Args:
            from_email: Sender email address
            api_key: SendGrid API key
        """
        super().__init__(from_email)
        self.api_key = api_key
        self.client = SendGridAPIClient(api_key)

    def validate_connection(self) -> bool:
        """Validate SendGrid connection.

        Returns:
            True if connection is valid
        """
        try:
            response = self.client.client.api_resources.get()
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"SendGrid connection validation failed: {e}")
            return False

    def send(
        self, message: EmailMessage, correlation_id: str = None
    ) -> SendResult:
        """Send email via SendGrid.

        Args:
            message: Email message to send
            correlation_id: Optional correlation ID for tracking

        Returns:
            SendResult with status and details
        """
        result = SendResult(
            recipient=message.recipient, status=SendStatus.FAILED, correlation_id=correlation_id
        )

        try:
            mail = Mail(
                from_email=self._get_from_email(message),
                to_emails=To(message.recipient),
                subject=message.subject,
            )

            if message.text_body:
                mail.add_content(Content(mime_type="text/plain", value=message.text_body))
            if message.html_body:
                mail.add_content(Content(mime_type="text/html", value=message.html_body))

            if message.reply_to:
                mail.reply_to = Email(message.reply_to)

            # Add metadata if provided
            if message.metadata:
                if "unique_args" not in dir(mail):
                    mail.custom_args = message.metadata
                else:
                    mail.unique_args = message.metadata

            response = self._send_with_retry(mail)

            result.status = SendStatus.SUCCESS
            result.message_id = response.headers.get("X-Message-Id")
            logger.info(
                f"Email sent to {message.recipient} via SendGrid (correlation_id: {correlation_id})"
            )

            return result
        except RateLimitError as e:
            result.status = SendStatus.FAILED
            result.error_reason = f"Rate limited: {str(e)}"
            logger.warning(f"Rate limit exceeded for {message.recipient}: {e}")
            return result
        except DeliveryError as e:
            result.status = SendStatus.FAILED
            result.error_reason = str(e)
            logger.error(f"Delivery error for {message.recipient}: {e}")
            return result
        except Exception as e:
            result.status = SendStatus.FAILED
            result.error_reason = str(e)
            logger.error(f"Error sending email to {message.recipient}: {e}")
            return result

    def _send_with_retry(
        self, mail: Mail, max_retries: int = 3, base_delay: float = 1.0
    ):
        """Send a message with exponential backoff retry.

        Args:
            mail: Mail object to send
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds for exponential backoff

        Returns:
            API response

        Raises:
            RateLimitError: If rate limit is exceeded
            DeliveryError: If delivery fails
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.send(mail)
                if response.status_code in [200, 201, 202]:
                    return response
                else:
                    raise DeliveryError(
                        f"SendGrid returned status {response.status_code}: {response.body}"
                    )
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                last_error = e

                # Check for rate limiting (429)
                if hasattr(e, "response") and e.response and e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limited. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        raise RateLimitError("Rate limit exceeded after retries") from e
                # Temporary server errors
                elif (
                    hasattr(e, "response")
                    and e.response
                    and e.response.status_code in [500, 502, 503]
                ):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Server error {e.response.status_code}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        raise DeliveryError(
                            f"Server error {e.response.status_code} after retries"
                        ) from e
                elif hasattr(e, "response") and e.response and e.response.status_code == 401:
                    raise AuthenticationError("Authentication failed") from e
                else:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Request error. Retrying in {delay}s (attempt {attempt + 1}/{max_retries}): {error_msg}"
                        )
                        time.sleep(delay)
                    else:
                        raise DeliveryError(f"Request failed after {max_retries} attempts: {error_msg}") from e
            except Exception as e:
                raise DeliveryError(f"Unexpected error sending message: {e}") from e

        raise DeliveryError(f"Failed to send message after {max_retries} attempts")
