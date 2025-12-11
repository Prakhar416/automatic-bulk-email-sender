# Autobulk - Automatic Bulk Email Sender

A powerful Python CLI tool for sending bulk emails with Gmail and SendGrid integration. Features template-based email composition, scheduling capabilities, and comprehensive tracking.

## Features

- **Multi-Provider Support**: Gmail API and SendGrid integration
- **Template System**: Jinja2-based email templates with variables
- **Scheduling**: One-time and cron-based scheduling with APScheduler
- **Configuration**: Flexible YAML/JSON + environment variable configuration
- **Logging**: Structured logging with file rotation and multiple outputs
- **Error Handling**: Comprehensive exception handling with retry mechanisms
- **Database**: SQLAlchemy integration for tracking and persistence

## Prerequisites

- Python 3.8.1 or higher
- Poetry (for dependency management)
- API credentials for Gmail or SendGrid

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd automatic-bulk-email-sender
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Poetry
pip install poetry

# Install project dependencies
poetry install --only main
```

### 3. Verify Installation

```bash
python -m autobulk --help
```

You should see the help output with available commands.

## Configuration

Autobulk supports configuration through multiple sources with the following precedence (highest to lowest):

1. Command-line arguments
2. Environment variables
3. YAML/JSON configuration files
4. .env files
5. Default values

### Quick Start Configuration

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Copy the example configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

3. **Edit the configuration files** with your actual credentials and settings.

### Configuration Files

#### `.env` File
Environment variables for sensitive data like API keys:

```bash
# SendGrid Configuration
AUTOBULK_SENDGRID_API_KEY=your-sendgrid-api-key
AUTOBULK_SENDGRID_FROM_EMAIL=your-email@example.com
AUTOBULK_SENDGRID_FROM_NAME=Your Name

# Database Configuration
AUTOBULK_DATABASE_URL=sqlite:///autobulk.db

# Logging Configuration
AUTOBULK_LOGGING_LEVEL=INFO
AUTOBULK_LOGGING_FILE_PATH=logs/autobulk.log
```

#### `config.yaml` File
Structured configuration for application settings:

```yaml
# Application settings
app_name: autobulk
debug: false

# SendGrid Configuration
sendgrid:
  api_key: your-sendgrid-api-key
  from_email: your-email@example.com
  from_name: Your Name

# Scheduling Configuration
scheduler:
  timezone: UTC
  max_concurrent: 10
  retry_attempts: 3
  retry_delay: 60

# Template Configuration
templates:
  templates_dir: templates
  default_template: default
  cache_templates: true

# Tracking Configuration
tracking:
  base_url: https://your-tracking-domain.com
  enabled: true
  open_tracking: true
  click_tracking: true

# Database Configuration
database:
  url: sqlite:///autobulk.db
  echo: false

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: logs/autobulk.log
  max_file_size: 10485760
  backup_count: 5
  console_output: true
```

## API Credentials Setup

### Gmail API Setup

1. **Enable Gmail API** in your Google Cloud Console
2. **Create service account** or OAuth2 credentials
3. **Configure credentials**:
    ```bash
    # Service account JSON file path
    AUTOBULK_GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json

    # OR OAuth2 credentials
    AUTOBULK_GOOGLE_CLIENT_ID=your-client-id
    AUTOBULK_GOOGLE_CLIENT_SECRET=your-client-secret
    AUTOBULK_GOOGLE_REFRESH_TOKEN=your-refresh-token
    ```

### Google Sheets Setup

Autobulk can read recipient data from Google Sheets, supporting dynamic data management and real-time updates.

#### Prerequisites
- A Google Cloud project with Sheets API enabled
- Service account credentials with Sheets API access
- A shared Google Sheet with recipient data

#### Step 1: Create a Google Cloud Project and Service Account

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project** or select an existing one
3. **Enable the Google Sheets API:**
   - Go to APIs & Services → Library
   - Search for "Google Sheets API"
   - Click Enable

4. **Create Service Account credentials:**
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → Service Account
   - Fill in the service account details
   - Click "Create and Continue"
   - Grant Editor access (or minimal required permissions)
   - Click "Continue"
   - Go to the Service Accounts page
   - Click on your new service account
   - Go to Keys tab
   - Click "Add Key" → "Create new key"
   - Choose JSON format
   - The JSON file will be downloaded automatically

#### Step 2: Share the Google Sheet

1. **Open your Google Sheet** containing recipient data
2. **Share it with the service account email** (found in the JSON key file as `client_email`)
3. **Grant at least "Viewer" permission** (no need for edit access)

#### Step 3: Configure Autobulk

1. **Store the credentials securely:**
    ```bash
    # Option A: Path to credentials file
    AUTOBULK_GOOGLE_CREDENTIALS_PATH=/secure/path/to/service-account.json

    # Option B: JSON string in environment variable
    AUTOBULK_GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...",...}'
    ```

2. **Configure the Sheets settings:**
    ```bash
    # Google Sheet ID (found in the sheet URL)
    AUTOBULK_SHEETS_SPREADSHEET_ID=1abc2def3ghi4jkl5mno6pqr7stu8vwx

    # Range to read (e.g., 'Sheet1' or 'Sheet1!A1:Z1000')
    AUTOBULK_SHEETS_RANGE=Sheet1

    # Required columns (comma-separated or list in YAML)
    AUTOBULK_SHEETS_REQUIRED_COLUMNS=name,email

    # Cache format for auditing (csv, json, or both)
    AUTOBULK_SHEETS_CACHE_FORMAT=both

    # Cache directory
    AUTOBULK_SHEETS_CACHE_DIR=~/.autobulk/cache
    ```

#### Step 4: Format Your Google Sheet

Your Google Sheet should have at least these columns (case-insensitive):
- **name**: Recipient's name (required)
- **email**: Recipient's email address (required)
- Additional columns for custom fields (optional)

Example sheet:
```
| Name          | Email                | Company    | Department |
|---------------|----------------------|------------|------------|
| John Doe      | john@example.com     | Acme       | Sales      |
| Jane Smith    | jane@example.com     | Acme       | Marketing  |
| Bob Johnson   | bob@example.com      | TechCorp   | Engineering|
```

### SendGrid Setup

1. **Create SendGrid account** and get API key
2. **Configure credentials**:
   ```bash
   AUTOBULK_SENDGRID_API_KEY=your-sendgrid-api-key
   AUTOBULK_SENDGRID_FROM_EMAIL=verified-sender@example.com
   ```

## Usage

### Basic Commands

#### Show Help
```bash
python -m autobulk --help
```

#### Version Information
```bash
python -m autobulk version
```

#### Status Check
```bash
python -m autobulk status
python -m autobulk status --debug
```

### Email Operations

#### Send Bulk Emails
```bash
python -m autobulk send \
  --template welcome_email \
  --recipients recipients.csv \
  --provider gmail \
  --dry-run
```

**Parameters:**
- `--template, -t`: Email template name (without extension)
- `--recipients, -r`: Path to CSV file with recipient emails
- `--provider`: Email provider (`gmail` or `sendgrid`)
- `--dry-run`: Preview emails without actually sending
- `--debug`: Enable debug logging

#### Schedule Email Campaigns
```bash
# One-time scheduling
python -m autobulk schedule \
  --template newsletter \
  --recipients subscribers.csv \
  --at "2024-01-15T14:30:00Z"

# Cron-based scheduling
python -m autobulk schedule \
  --template weekly_digest \
  --recipients users.csv \
  --cron "0 9 * * 1" \
  --provider sendgrid
```

**Parameters:**
- `--cron`: Cron expression for recurring schedules
- `--at`: ISO format timestamp for one-time scheduling

#### Test Provider Connection
```bash
python -m autobulk test-connection gmail
python -m autobulk test-connection sendgrid --debug
```

### Recipients Management

#### Sync Recipients from Google Sheets
```bash
# Basic sync with default configuration
python -m autobulk recipients sync

# Sync with specific spreadsheet ID
python -m autobulk recipients sync --spreadsheet-id 1abc2def3ghi4jkl5mno6pqr7stu8vwx

# Preview more rows
python -m autobulk recipients sync --preview 20

# Skip caching
python -m autobulk recipients sync --no-cache

# Enable debug logging
python -m autobulk recipients sync --debug
```

**Parameters:**
- `--spreadsheet-id, -s`: Google Sheet ID (optional, can be configured in .env)
- `--range, -r`: Range to read (default: "Sheet1")
- `--preview, -p`: Number of rows to preview (default: 5)
- `--cache/--no-cache`: Whether to cache results (default: cache enabled)
- `--debug`: Enable debug logging

**Output:**
- Displays validation errors with row numbers and field names
- Shows preview of fetched recipients
- Caches data to CSV and JSON for auditing
- Reports deduplication statistics

### Template Management
```bash
python -m autobulk templates
```

## Project Structure

```
autobulk/
├── src/
│   └── autobulk/
│       ├── __init__.py           # Package initialization
│       ├── __main__.py           # CLI entry point
│       ├── cli.py                # Click-based CLI commands
│       ├── config.py             # Configuration management
│       ├── logging.py            # Logging utilities
│       ├── exceptions.py         # Exception handling
│       ├── sheets.py             # Google Sheets integration
│       └── recipients_cli.py     # Recipients management CLI
├── tests/
│       └── test_sheets.py        # Unit tests for Sheets integration
├── templates/                    # Email templates directory
├── logs/                        # Log files directory
├── .env.example                 # Environment variables template
├── config.yaml.example          # Configuration template
├── pyproject.toml               # Poetry dependencies
└── README.md                    # This file
```

## Logging

Autobulk provides comprehensive logging capabilities:

- **Console Output**: Colored, human-readable logs
- **File Logging**: Structured JSON logs with rotation
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Third-party Libraries**: Reduced noise from dependencies

### Log Configuration

Configure logging in your config file:

```yaml
logging:
  level: INFO                    # Log level
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: logs/autobulk.log   # Log file path
  max_file_size: 10485760       # 10MB max file size
  backup_count: 5               # Number of backup files
  console_output: true          # Enable console logging
```

## Secrets Management

### Security Best Practices

1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive data
3. **Rotate API keys** regularly
4. **Use minimal permissions** for service accounts
5. **Store credentials securely** in production

### Secrets Storage

```bash
# Environment variables (preferred)
export AUTOBULK_SENDGRID_API_KEY="your-secret-key"

# .env file (for development)
echo "AUTOBULK_SENDGRID_API_KEY=your-secret-key" >> .env

# Cloud secret management (production)
# AWS Secrets Manager, Azure Key Vault, etc.
```

### Redacted Configuration

The example configuration files (`.env.example`, `config.yaml.example`) contain:
- ✅ Valid configuration structure
- ✅ All available options
- ✅ Descriptive comments
- ❌ **NO actual secrets or credentials**

## Development

### Adding New Features

1. **Email Providers**: Extend `src/autobulk/providers/`
2. **Templates**: Add Jinja2 templates to `templates/`
3. **Commands**: Add CLI commands in `src/autobulk/cli.py`
4. **Configuration**: Extend settings in `src/autobulk/config.py`

### Testing

```bash
# Install dev dependencies
poetry install

# Run tests
poetry run pytest

# Type checking
poetry run mypy src/

# Code formatting
poetry run black src/
poetry run isort src/
```

### Logging Integration

Import and use the logging helper in your modules:

```python
from autobulk.logging import get_logger

logger = get_logger(__name__)

# Use structured logging
logger.info("Email sent successfully", extra={
    "email": "user@example.com",
    "template": "welcome",
    "provider": "gmail"
})
```

### Configuration Usage

Access typed settings in your code:

```python
from autobulk.config import load_settings

settings = load_settings()

# Access configuration
api_key = settings.sendgrid.api_key
max_concurrent = settings.scheduler.max_concurrent
log_level = settings.logging.level
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   python -m autobulk --help
   ```

2. **Configuration Errors**
   ```bash
   # Check config syntax
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   
   # Verify environment variables
   python -c "import os; print([k for k in os.environ if k.startswith('AUTOBULK_')])"
   ```

3. **Logging Issues**
   ```bash
   # Check log directory permissions
   ls -la logs/
   
   # Test logging with debug mode
   python -m autobulk status --debug
   ```

4. **API Connection Issues**
   ```bash
   # Test provider connections
   python -m autobulk test-connection gmail
   python -m autobulk test-connection sendgrid
   ```

### Debug Mode

Enable debug logging for detailed information:

```bash
python -m autobulk --debug send --template test --recipients test.csv
```

## Support

For issues and feature requests, please refer to the project repository.

## License

This project is licensed under the MIT License.