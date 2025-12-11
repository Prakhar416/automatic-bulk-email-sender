# Architecture

## Overview

The email sender system consists of the following main components:

### Core Components

1. **Template System** (`template.py`)
   - Jinja2-based template loading and rendering
   - Metadata validation (required/optional variables)
   - Template preview without sending

2. **Email Providers** (`providers/`)
   - `base.py`: Abstract base class for providers
   - `gmail.py`: Gmail API integration with OAuth
   - `sendgrid.py`: SendGrid SMTP/API integration
   - `mock.py`: Mock provider for testing/preview

3. **Email Sender** (`sender.py`)
   - High-level abstraction coordinating templates and providers
   - Bulk email sending with validation
   - Test email sending
   - Template preview functionality

4. **Validators** (`validators.py`)
   - Email address validation
   - Recipient field validation

5. **Models** (`models.py`)
   - `EmailMessage`: Email message structure
   - `TemplateMetadata`: Template metadata
   - `SendResult`: Send operation result with status and error tracking
   - `SendStatus`: Send status enumeration

6. **CLI** (`cli.py`)
   - Command-line interface for all operations
   - Commands: list-templates, preview, send-test, send-bulk

## Data Flow

### Template Rendering

```
Template Files (YAML, Jinja2)
    ↓
TemplateLoader (validates, caches metadata)
    ↓
Template Rendering Context
    ↓
Rendered Email (HTML/Text)
    ↓
EmailMessage Object
```

### Email Sending

```
Recipients Data
    ↓
Email Validation (validate-email)
    ↓
Recipient Field Validation
    ↓
Template Rendering
    ↓
EmailMessage Creation
    ↓
Provider.send() (with retries & backoff)
    ↓
SendResult (status, correlation_id, error_reason)
```

### Retry Logic

- Exponential backoff: delay = base_delay * (2 ^ attempt)
- Retries on: Rate limit (429), Temporary server errors (500, 502, 503)
- No retries on: Authentication failures (401), Permanent errors (4xx except 429)

## Configuration

### Template Structure

```
templates/
├── template_name.yaml          # Metadata
├── template_name.jinja2        # HTML template
└── template_name.text.jinja2   # Text template (optional)
```

### Environment Variables

- `GMAIL_CREDENTIALS_FILE`: Path to Google OAuth credentials
- `GMAIL_TOKEN_FILE`: Path to store OAuth token (default: token.pickle)
- `SENDGRID_API_KEY`: SendGrid API key

## Error Handling

Custom exception hierarchy:

```
EmailSenderError
├── TemplateError
├── ValidationError
├── ProviderError
    ├── AuthenticationError
    ├── RateLimitError
    └── DeliveryError
```

All exceptions include:
- Detailed error messages
- Context information (correlation_id, recipient, etc.)
- Proper logging with timestamps

## Correlation IDs

Every email send operation generates a unique correlation ID (UUID) that:
- Uniquely identifies the send attempt
- Is included in logs for tracing
- Is returned in SendResult for tracking

## Testing

Mock provider allows testing without real credentials:
- Used for `preview` command
- Used for template validation
- Returns synthetic message IDs and success status

## Performance Considerations

1. **Template Caching**: Metadata loaded once and cached
2. **Batch Processing**: Bulk sending processes recipients sequentially with logging
3. **Retry Backoff**: Exponential backoff prevents overwhelming servers
4. **Email Validation**: Validates before rendering to save resources
