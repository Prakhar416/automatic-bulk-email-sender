"""CLI commands for the email sender."""

import logging
import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from dotenv import load_dotenv
import os

from .sender import EmailSender
from .template import TemplateLoader
from .providers import GmailProvider, SendGridProvider
from .exceptions import EmailSenderError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_env_file(env_file: Optional[str] = None):
    """Load environment variables from .env file."""
    if env_file and Path(env_file).exists():
        load_dotenv(env_file)
    else:
        load_dotenv()


def create_provider(provider_type: str, from_email: str, config: dict, optional: bool = False):
    """Create an email provider based on type.

    Args:
        provider_type: Type of provider (gmail or sendgrid)
        from_email: Sender email address
        config: Provider configuration dictionary
        optional: If True, return a mock provider if real credentials are unavailable

    Returns:
        Provider instance

    Raises:
        EmailSenderError: If provider creation fails
    """
    if provider_type.lower() == "gmail":
        credentials_file = config.get(
            "credentials_file", os.getenv("GMAIL_CREDENTIALS_FILE")
        )
        token_file = config.get("token_file", os.getenv("GMAIL_TOKEN_FILE", "token.pickle"))
        
        # Check if credentials exist
        if optional and not credentials_file and not Path(token_file).exists():
            # Return a mock provider for preview/list operations
            from .providers.mock import MockEmailProvider
            return MockEmailProvider(from_email=from_email)
        
        return GmailProvider(
            from_email=from_email,
            credentials_file=credentials_file,
            token_file=token_file,
        )
    elif provider_type.lower() == "sendgrid":
        api_key = config.get("api_key", os.getenv("SENDGRID_API_KEY"))
        if not api_key and optional:
            # Return a mock provider for preview/list operations
            from .providers.mock import MockEmailProvider
            return MockEmailProvider(from_email=from_email)
        if not api_key:
            raise EmailSenderError(
                "SendGrid API key not provided. Set SENDGRID_API_KEY environment variable or provide api_key in config"
            )
        return SendGridProvider(from_email=from_email, api_key=api_key)
    else:
        raise EmailSenderError(f"Unknown provider type: {provider_type}")


@click.group()
def main():
    """Email sender CLI."""
    pass


@main.command()
@click.option("--template-dir", required=True, help="Path to template directory")
@click.option("--env-file", type=click.Path(exists=True), help=".env file path")
def list_templates(template_dir: str, env_file: Optional[str]):
    """List all available templates."""
    try:
        load_env_file(env_file)

        # Load templates directly without needing a provider
        loader = TemplateLoader(template_dir)

        # List templates
        templates = loader.list_templates()

        if not templates:
            click.echo("No templates found")
            return

        click.echo(f"Available templates ({len(templates)}):")
        for template in templates:
            try:
                metadata = loader.load_metadata(template)
                click.echo(f"  - {template}: {metadata.description or metadata.subject}")
            except Exception as e:
                click.echo(f"  - {template}: (Error loading metadata: {e})")

    except EmailSenderError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--template-dir", required=True, help="Path to template directory")
@click.option("--template", required=True, help="Template name")
@click.option("--provider", default="gmail", help="Email provider (gmail or sendgrid)")
@click.option("--from-email", required=True, help="Sender email address")
@click.option("--sample-data", type=click.Path(exists=True), required=True, help="Sample recipient data (JSON)")
@click.option("--config", type=click.Path(exists=True), help="Config file path (YAML/JSON)")
@click.option("--env-file", type=click.Path(exists=True), help=".env file path")
def preview(
    template_dir: str,
    template: str,
    provider: str,
    from_email: str,
    sample_data: str,
    config: Optional[str],
    env_file: Optional[str],
):
    """Preview a template with sample data."""
    try:
        load_env_file(env_file)

        # Load sample data
        with open(sample_data, "r") as f:
            sample_recipient = json.load(f)

        # Load config if provided
        provider_config = {}
        if config:
            with open(config, "r") as f:
                if config.endswith(".json"):
                    provider_config = json.load(f)
                else:
                    provider_config = yaml.safe_load(f) or {}

        # Create provider (optional=True to allow mock provider for preview)
        email_provider = create_provider(provider, from_email, provider_config, optional=True)

        # Create sender
        sender = EmailSender(template_dir, email_provider)

        # Preview template
        preview_data = sender.preview_template(template, sample_recipient)

        click.echo(f"Template: {preview_data['template_name']}")
        click.echo(f"Subject: {preview_data['subject']}")
        click.echo(f"Required Variables: {', '.join(preview_data['required_variables'])}")
        click.echo(f"Optional Variables: {', '.join(preview_data['optional_variables'])}")
        click.echo("\nHTML Preview:")
        click.echo("-" * 50)
        if preview_data["html_preview"]:
            click.echo(preview_data["html_preview"])
        else:
            click.echo("(No HTML body)")
        click.echo("-" * 50)

        if preview_data["text_preview"]:
            click.echo("\nText Preview:")
            click.echo("-" * 50)
            click.echo(preview_data["text_preview"])
            click.echo("-" * 50)

    except EmailSenderError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--template-dir", required=True, help="Path to template directory")
@click.option("--template", required=True, help="Template name")
@click.option("--provider", default="gmail", help="Email provider (gmail or sendgrid)")
@click.option("--from-email", required=True, help="Sender email address")
@click.option("--recipient", required=True, help="Recipient email address")
@click.option("--data", type=click.Path(exists=True), required=True, help="Recipient data (JSON)")
@click.option("--config", type=click.Path(exists=True), help="Config file path (YAML/JSON)")
@click.option("--env-file", type=click.Path(exists=True), help=".env file path")
def send_test(
    template_dir: str,
    template: str,
    provider: str,
    from_email: str,
    recipient: str,
    data: str,
    config: Optional[str],
    env_file: Optional[str],
):
    """Send a test email to a single recipient."""
    try:
        load_env_file(env_file)

        # Load recipient data
        with open(data, "r") as f:
            recipient_data = json.load(f)

        # Load config if provided
        provider_config = {}
        if config:
            with open(config, "r") as f:
                if config.endswith(".json"):
                    provider_config = json.load(f)
                else:
                    provider_config = yaml.safe_load(f) or {}

        # Create provider (optional=True to allow mock provider for testing)
        email_provider = create_provider(provider, from_email, provider_config, optional=True)

        # Validate provider connection
        if not email_provider.validate_connection():
            click.echo("Error: Provider connection validation failed", err=True)
            sys.exit(1)

        # Create sender
        sender = EmailSender(template_dir, email_provider)

        # Send test email
        result = sender.send_test_email(template, recipient, recipient_data)

        click.echo(f"Recipient: {result.recipient}")
        click.echo(f"Status: {result.status.value}")
        if result.message_id:
            click.echo(f"Message ID: {result.message_id}")
        if result.error_reason:
            click.echo(f"Error: {result.error_reason}")
        if result.correlation_id:
            click.echo(f"Correlation ID: {result.correlation_id}")

        sys.exit(0 if result.status.value == "success" else 1)

    except EmailSenderError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--template-dir", required=True, help="Path to template directory")
@click.option("--template", required=True, help="Template name")
@click.option("--provider", default="gmail", help="Email provider (gmail or sendgrid)")
@click.option("--from-email", required=True, help="Sender email address")
@click.option("--recipients", type=click.Path(exists=True), required=True, help="Recipients file (JSON list)")
@click.option("--email-field", default="email", help="Field name for email address")
@click.option("--output", type=click.Path(), help="Output file for results (JSON)")
@click.option("--config", type=click.Path(exists=True), help="Config file path (YAML/JSON)")
@click.option("--env-file", type=click.Path(exists=True), help=".env file path")
def send_bulk(
    template_dir: str,
    template: str,
    provider: str,
    from_email: str,
    recipients: str,
    email_field: str,
    output: Optional[str],
    config: Optional[str],
    env_file: Optional[str],
):
    """Send bulk emails to multiple recipients."""
    try:
        load_env_file(env_file)

        # Load recipients
        with open(recipients, "r") as f:
            recipients_data = json.load(f)

        if not isinstance(recipients_data, list):
            raise ValueError("Recipients file must contain a JSON list")

        click.echo(f"Loaded {len(recipients_data)} recipients")

        # Load config if provided
        provider_config = {}
        if config:
            with open(config, "r") as f:
                if config.endswith(".json"):
                    provider_config = json.load(f)
                else:
                    provider_config = yaml.safe_load(f) or {}

        # Create provider (optional=True to allow mock provider for testing)
        email_provider = create_provider(provider, from_email, provider_config, optional=True)

        # Validate provider connection
        if not email_provider.validate_connection():
            click.echo("Error: Provider connection validation failed", err=True)
            sys.exit(1)

        # Create sender
        sender = EmailSender(template_dir, email_provider)

        # Send bulk emails
        click.echo(f"Sending emails using {provider} provider...")
        results = sender.send_bulk_emails(template, recipients_data, email_field=email_field)

        # Print summary
        successful = sum(1 for r in results if r.status.value == "success")
        failed = sum(1 for r in results if r.status.value == "failed")
        skipped = sum(1 for r in results if r.status.value == "skipped")
        bounced = sum(1 for r in results if r.status.value == "bounced")

        click.echo("\nSend Summary:")
        click.echo(f"  Total: {len(results)}")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Skipped: {skipped}")
        click.echo(f"  Bounced: {bounced}")

        # Output results if requested
        if output:
            results_data = [r.to_dict() for r in results]
            with open(output, "w") as f:
                json.dump(results_data, f, indent=2)
            click.echo(f"\nResults saved to: {output}")

        # Exit with appropriate code
        sys.exit(0 if failed == 0 and bounced == 0 else 1)

    except EmailSenderError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
