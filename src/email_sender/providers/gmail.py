"""Gmail API provider."""

import base64
import logging
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path
import json
import pickle

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models import EmailMessage, SendResult, SendStatus
from ..exceptions import ProviderError, AuthenticationError, RateLimitError, DeliveryError
from .base import BaseEmailProvider

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailProvider(BaseEmailProvider):
    """Gmail API email provider."""

    def __init__(
        self,
        from_email: str,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        """Initialize Gmail provider.

        Args:
            from_email: Sender email address
            credentials_file: Path to credentials.json file
            token_file: Path to store/load OAuth token
        """
        super().__init__(from_email)
        self.credentials_file = credentials_file
        self.token_file = token_file or "token.pickle"
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Gmail API service."""
        try:
            creds = self._get_credentials()
            self.service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Gmail service: {e}") from e

    def _get_credentials(self):
        """Get valid user credentials for Gmail API.

        Returns:
            Valid credentials object
        """
        creds = None

        # Load token from file if it exists
        if Path(self.token_file).exists():
            try:
                with open(self.token_file, "rb") as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")

        # If no valid credentials, create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail OAuth token")
                creds.refresh(Request())
            else:
                if not self.credentials_file:
                    raise AuthenticationError(
                        "No credentials file provided and no valid token cached"
                    )
                if not Path(self.credentials_file).exists():
                    raise AuthenticationError(
                        f"Credentials file not found: {self.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for next run
            with open(self.token_file, "wb") as token:
                pickle.dump(creds, token)

        return creds

    def validate_connection(self) -> bool:
        """Validate Gmail connection.

        Returns:
            True if connection is valid
        """
        try:
            if not self.service:
                return False
            self.service.users().getProfile(userId="me").execute()
            return True
        except Exception as e:
            logger.error(f"Gmail connection validation failed: {e}")
            return False

    def send(
        self, message: EmailMessage, correlation_id: str = None
    ) -> SendResult:
        """Send email via Gmail API.

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
            # Create MIME message
            mime_message = self._create_mime_message(message)

            # Send message with retries
            response = self._send_with_retry(mime_message)

            result.status = SendStatus.SUCCESS
            result.message_id = response.get("id")
            logger.info(
                f"Email sent to {message.recipient} (correlation_id: {correlation_id})"
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

    def _create_mime_message(self, message: EmailMessage) -> str:
        """Create a MIME message.

        Args:
            message: Email message

        Returns:
            Base64 encoded MIME message
        """
        mime_message = MIMEMultipart("alternative")
        mime_message["to"] = message.recipient
        mime_message["from"] = self._get_from_email(message)
        mime_message["subject"] = message.subject

        if message.reply_to:
            mime_message["reply-to"] = message.reply_to

        if message.text_body:
            mime_message.attach(MIMEText(message.text_body, "plain"))
        if message.html_body:
            mime_message.attach(MIMEText(message.html_body, "html"))

        return base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

    def _send_with_retry(
        self, mime_message: str, max_retries: int = 3, base_delay: float = 1.0
    ) -> dict:
        """Send a message with exponential backoff retry.

        Args:
            mime_message: Base64 encoded MIME message
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
                response = (
                    self.service.users()
                    .messages()
                    .send(userId="me", body={"raw": mime_message})
                    .execute()
                )
                return response
            except HttpError as e:
                error_code = e.resp.status
                last_error = e

                if error_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limited. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        raise RateLimitError("Rate limit exceeded after retries") from e
                elif error_code in [500, 502, 503]:  # Temporary server errors
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Server error {error_code}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                    else:
                        raise DeliveryError(
                            f"Server error {error_code} after retries"
                        ) from e
                elif error_code == 401:
                    raise AuthenticationError("Authentication failed") from e
                else:
                    raise DeliveryError(f"Gmail API error {error_code}: {e.content}") from e
            except Exception as e:
                raise DeliveryError(f"Unexpected error sending message: {e}") from e

        raise DeliveryError(f"Failed to send message after {max_retries} attempts")
