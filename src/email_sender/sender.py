"""Main email sender abstraction."""

import logging
import uuid
from typing import List, Dict, Optional, Any
from pathlib import Path

from .models import EmailMessage, SendResult, SendStatus, TemplateMetadata
from .template import TemplateLoader
from .validators import validate_email_address, validate_recipient_fields
from .providers.base import BaseEmailProvider
from .exceptions import ValidationError, TemplateError

logger = logging.getLogger(__name__)


class EmailSender:
    """High-level email sender that coordinates templates and providers."""

    def __init__(
        self,
        template_dir: str,
        provider: BaseEmailProvider,
        skip_invalid_emails: bool = True,
        skip_invalid_recipients: bool = True,
    ):
        """Initialize the email sender.

        Args:
            template_dir: Path to template directory
            provider: Email provider instance
            skip_invalid_emails: Skip recipients with invalid email addresses
            skip_invalid_recipients: Skip recipients with missing required fields
        """
        self.template_dir = template_dir
        self.provider = provider
        self.skip_invalid_emails = skip_invalid_emails
        self.skip_invalid_recipients = skip_invalid_recipients
        self.template_loader = TemplateLoader(template_dir)

    def validate_provider(self) -> bool:
        """Validate that the provider is properly configured.

        Returns:
            True if provider is valid
        """
        return self.provider.validate_connection()

    def preview_template(
        self, template_name: str, sample_recipient: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Preview a template with sample recipient data.

        Args:
            template_name: Name of the template
            sample_recipient: Sample recipient data for rendering

        Returns:
            Dictionary with preview information
        """
        try:
            metadata = self.template_loader.load_metadata(template_name)

            # Validate that sample has required variables
            missing = []
            for var in metadata.required_variables:
                if var not in sample_recipient:
                    missing.append(var)

            if missing:
                raise ValidationError(
                    f"Sample recipient missing required variables: {missing}"
                )

            # Render the template
            html_body, text_body = self.template_loader.render_template(
                template_name, sample_recipient
            )

            return {
                "template_name": template_name,
                "subject": metadata.subject,
                "html_preview": html_body[:500] if html_body else None,
                "text_preview": text_body[:500] if text_body else None,
                "required_variables": metadata.required_variables,
                "optional_variables": metadata.optional_variables,
            }
        except (TemplateError, ValidationError) as e:
            raise
        except Exception as e:
            raise TemplateError(f"Error previewing template: {e}") from e

    def send_test_email(
        self, template_name: str, recipient: str, recipient_data: Dict[str, Any]
    ) -> SendResult:
        """Send a test email to a single recipient.

        Args:
            template_name: Name of the template
            recipient: Recipient email address
            recipient_data: Recipient-specific data for template rendering

        Returns:
            SendResult with status and details
        """
        correlation_id = str(uuid.uuid4())

        # Validate email address
        is_valid, _ = validate_email_address(recipient)
        if not is_valid:
            result = SendResult(
                recipient=recipient,
                status=SendStatus.SKIPPED,
                error_reason=f"Invalid email address: {_}",
                correlation_id=correlation_id,
            )
            logger.warning(f"Skipping invalid email {recipient}: {_}")
            return result

        try:
            metadata = self.template_loader.load_metadata(template_name)

            # Validate recipient has required fields
            is_valid, missing = validate_recipient_fields(
                recipient_data, metadata.required_variables, metadata.optional_variables
            )
            if not is_valid:
                result = SendResult(
                    recipient=recipient,
                    status=SendStatus.SKIPPED,
                    error_reason=f"Missing required fields: {missing}",
                    correlation_id=correlation_id,
                )
                logger.warning(f"Skipping recipient {recipient}: missing {missing}")
                return result

            # Render template
            html_body, text_body = self.template_loader.render_template(
                template_name, recipient_data
            )

            # Create and send message
            message = EmailMessage(
                recipient=recipient,
                subject=metadata.subject,
                html_body=html_body,
                text_body=text_body,
            )

            result = self.provider.send(message, correlation_id=correlation_id)
            return result

        except (TemplateError, ValidationError) as e:
            result = SendResult(
                recipient=recipient,
                status=SendStatus.FAILED,
                error_reason=str(e),
                correlation_id=correlation_id,
            )
            logger.error(f"Error sending test email to {recipient}: {e}")
            return result
        except Exception as e:
            result = SendResult(
                recipient=recipient,
                status=SendStatus.FAILED,
                error_reason=str(e),
                correlation_id=correlation_id,
            )
            logger.error(f"Unexpected error sending test email to {recipient}: {e}")
            return result

    def send_bulk_emails(
        self,
        template_name: str,
        recipients: List[Dict[str, Any]],
        email_field: str = "email",
    ) -> List[SendResult]:
        """Send bulk emails to multiple recipients.

        Args:
            template_name: Name of the template
            recipients: List of recipient data dictionaries
            email_field: Field name containing email address in recipient data

        Returns:
            List of SendResult objects
        """
        results = []

        # Validate template and recipient structure
        try:
            metadata = self.template_loader.load_metadata(template_name)
        except TemplateError as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            raise

        for i, recipient_data in enumerate(recipients):
            try:
                if email_field not in recipient_data:
                    result = SendResult(
                        recipient="",
                        status=SendStatus.SKIPPED,
                        error_reason=f"Email field '{email_field}' not found in recipient data",
                        correlation_id=str(uuid.uuid4()),
                    )
                    results.append(result)
                    continue

                email = recipient_data[email_field]

                # Validate email
                is_valid, error_msg = validate_email_address(email)
                if not is_valid:
                    result = SendResult(
                        recipient=email,
                        status=SendStatus.SKIPPED if self.skip_invalid_emails else SendStatus.FAILED,
                        error_reason=f"Invalid email: {error_msg}",
                        correlation_id=str(uuid.uuid4()),
                    )
                    results.append(result)
                    logger.warning(f"Skipping invalid email {email}: {error_msg}")
                    continue

                # Validate recipient has required fields
                is_valid, missing = validate_recipient_fields(
                    recipient_data,
                    metadata.required_variables,
                    metadata.optional_variables,
                )
                if not is_valid:
                    result = SendResult(
                        recipient=email,
                        status=SendStatus.SKIPPED if self.skip_invalid_recipients else SendStatus.FAILED,
                        error_reason=f"Missing required fields: {missing}",
                        correlation_id=str(uuid.uuid4()),
                    )
                    results.append(result)
                    logger.warning(f"Skipping recipient {email}: missing {missing}")
                    continue

                # Send email
                result = self.send_test_email(
                    template_name, email, recipient_data
                )
                results.append(result)
                logger.info(
                    f"Processed recipient {i + 1}/{len(recipients)}: {email} - {result.status.value}"
                )

            except Exception as e:
                result = SendResult(
                    recipient=recipient_data.get(email_field, "unknown"),
                    status=SendStatus.FAILED,
                    error_reason=str(e),
                    correlation_id=str(uuid.uuid4()),
                )
                results.append(result)
                logger.error(f"Error processing recipient {i + 1}: {e}")

        return results
