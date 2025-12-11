# Automatic Bulk Email Sender

A Python-based email sender with Jinja2 template support, multiple provider backends (Gmail API and SendGrid), email validation, and comprehensive CLI tools.

## Features

- **Jinja2 Template Engine**: Dynamic email templates with variable substitution
- **Multiple Providers**: Gmail API and SendGrid support
- **Email Validation**: Validates recipient emails before sending
- **Retry Logic**: Exponential backoff retry mechanism for transient failures
- **Rate Limiting**: Handles provider rate limits gracefully
- **Correlation IDs**: Track each email with a unique correlation ID
- **Bulk Sending**: Send emails to multiple recipients
- **Template Preview**: Preview rendered templates before sending
- **Comprehensive Logging**: Detailed logs with correlation IDs

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd automatic-bulk-email-sender
```

2. Install in development mode:
```bash
pip install -e .
```

3. Create an environment file:
```bash
cp examples/.env.example .env
```

## Configuration

### Templates

Templates are stored in a directory with the following structure:

```
templates/
├── welcome.yaml          # Template metadata
├── welcome.jinja2        # HTML template
└── welcome.text.jinja2   # Text template (optional)
```

#### Template Metadata (YAML)

The `.yaml` file defines template metadata:

```yaml
name: Welcome Email
description: Welcome email for new users
subject: "Welcome to {{ company_name }}, {{ first_name }}!"
required_variables:
  - first_name
  - company_name
optional_variables:
  - last_name
  - account_url
has_html: true
has_text: true
```

#### Template Files

HTML template (`template_name.jinja2`):
```jinja2
<html>
  <body>
    <h1>Welcome, {{ first_name }}!</h1>
    {% if last_name %}
      <p>Last name: {{ last_name }}</p>
    {% endif %}
  </body>
</html>
```

Text template (`template_name.text.jinja2`):
```
Welcome, {{ first_name }}!
{% if last_name %}
Last name: {{ last_name }}
{% endif %}
```

### Provider Configuration

#### Gmail API

1. Set up Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials as `credentials.json`

2. Set environment variable:
```bash
export GMAIL_CREDENTIALS_FILE=path/to/credentials.json
export GMAIL_TOKEN_FILE=token.pickle
```

#### SendGrid

1. Get SendGrid API Key from [SendGrid Dashboard](https://app.sendgrid.com/settings/api_keys)

2. Set environment variable:
```bash
export SENDGRID_API_KEY=your_api_key
```

## Usage

### List Available Templates

```bash
email-sender list-templates \
  --template-dir examples \
  --provider gmail \
  --from-email sender@example.com
```

### Preview a Template

```bash
email-sender preview \
  --template-dir examples \
  --template welcome \
  --provider gmail \
  --from-email sender@example.com \
  --sample-data examples/sample_recipient.json
```

### Send a Test Email

```bash
email-sender send-test \
  --template-dir examples \
  --template welcome \
  --provider gmail \
  --from-email sender@example.com \
  --recipient user@example.com \
  --data examples/sample_recipient.json
```

### Send Bulk Emails

```bash
email-sender send-bulk \
  --template-dir examples \
  --template welcome \
  --provider gmail \
  --from-email sender@example.com \
  --recipients examples/recipients.json \
  --email-field email \
  --output results.json
```

### Switch to SendGrid

```bash
email-sender send-bulk \
  --template-dir examples \
  --template welcome \
  --provider sendgrid \
  --from-email sender@example.com \
  --recipients examples/recipients.json \
  --output results.json
```

## API Usage

### Basic Example

```python
from email_sender import EmailSender
from email_sender.providers import GmailProvider

# Create provider
provider = GmailProvider(
    from_email="sender@example.com",
    credentials_file="credentials.json"
)

# Create sender
sender = EmailSender(
    template_dir="./templates",
    provider=provider
)

# Preview template
preview = sender.preview_template(
    "welcome",
    {"first_name": "John", "company_name": "Acme"}
)

# Send test email
result = sender.send_test_email(
    template_name="welcome",
    recipient="user@example.com",
    recipient_data={"first_name": "John", "company_name": "Acme"}
)

# Send bulk emails
results = sender.send_bulk_emails(
    template_name="welcome",
    recipients=[
        {"email": "alice@example.com", "first_name": "Alice", "company_name": "Acme"},
        {"email": "bob@example.com", "first_name": "Bob", "company_name": "Acme"},
    ]
)
```

### SendGrid Example

```python
from email_sender import EmailSender
from email_sender.providers import SendGridProvider

provider = SendGridProvider(
    from_email="sender@example.com",
    api_key="your_sendgrid_api_key"
)

sender = EmailSender(template_dir="./templates", provider=provider)
```

## Response Format

### Send Result

Each send operation returns a `SendResult` object:

```python
{
    "recipient": "user@example.com",
    "status": "success",  # or "failed", "skipped", "bounced"
    "message_id": "abc123...",
    "error_reason": null,
    "timestamp": "2024-01-01T12:00:00",
    "correlation_id": "uuid-string"
}
```

### Bulk Send Output

When using `--output` flag with bulk send:

```json
[
    {
        "recipient": "alice@example.com",
        "status": "success",
        "message_id": "id1",
        "error_reason": null,
        "timestamp": "2024-01-01T12:00:00",
        "correlation_id": "uuid1"
    },
    {
        "recipient": "bob@example.com",
        "status": "success",
        "message_id": "id2",
        "error_reason": null,
        "timestamp": "2024-01-01T12:00:00",
        "correlation_id": "uuid2"
    },
    {
        "recipient": "invalid-email",
        "status": "skipped",
        "message_id": null,
        "error_reason": "Invalid email: The email address is not valid",
        "timestamp": "2024-01-01T12:00:00",
        "correlation_id": "uuid3"
    }
]
```

## Error Handling

The system uses domain-specific exceptions:

- `EmailSenderError`: Base exception
- `TemplateError`: Template loading/rendering errors
- `ValidationError`: Validation failures
- `ProviderError`: Provider-specific errors
- `AuthenticationError`: Authentication failures
- `RateLimitError`: Rate limiting errors
- `DeliveryError`: Delivery failures

All exceptions are properly logged with context information.

## Logging

Logs include:
- Timestamp
- Logger name
- Log level
- Message with context (correlation ID, recipient, etc.)

Configure logging level:

```python
import logging
logging.getLogger("email_sender").setLevel(logging.DEBUG)
```

## Testing

Run tests:

```bash
pytest
```

With coverage:

```bash
pytest --cov=src/email_sender
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

## License

MIT License - See LICENSE file for details
