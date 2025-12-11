# Email Tracking Service

A comprehensive, lightweight email tracking system for monitoring delivery, opens, clicks, and bounces across bulk email campaigns.

## Features

- **SQLite Database**: Persistent tracking of email lifecycle (queued → sent → opened → clicked/bounced)
- **REST API**: Full-featured API for managing campaigns, messages, and tracking events
- **Tracking Pixel**: 1x1 GIF endpoint to detect email opens with minimal overhead
- **Click Tracking**: URL rewriting to track link clicks with redirect capability
- **Bounce Handling**: Integration with SendGrid webhooks and Gmail DSN parsing
- **CLI Tool**: Command-line interface for campaign management and reporting
- **Web Dashboard**: Real-time metrics visualization with auto-refresh
- **CSV Export**: Export campaign data for external analysis
- **Webhook Support**: Automatic event processing from email service providers
- **Lightweight**: Single SQLite file, minimal dependencies

## Quick Start

```bash
# Installation
pip install -r requirements.txt
pip install -e .

# Start tracking server
python -m tracking.server

# In another terminal, create a campaign
email-tracking-cli campaign create --name "My Campaign"

# View dashboard
# Open http://localhost:5000/dashboard
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[TRACKING_GUIDE.md](TRACKING_GUIDE.md)** - Complete API and configuration reference
- **[INTEGRATION_EXAMPLE.md](INTEGRATION_EXAMPLE.md)** - Integration patterns and code examples

## Architecture

### Database Schema

The system uses SQLite with the following main tables:

- **campaigns**: Campaign metadata and settings
- **messages**: Individual email records with tracking tokens and status
- **message_events**: Detailed event log for each message
- **link_clicks**: Track individual link clicks with URLs
- **bounces**: Bounce details and types

### Core Components

1. **Database Layer** (`tracking/database.py`): SQLite operations with connection pooling
2. **Flask App** (`tracking/app.py`): REST API endpoints and core functionality
3. **Bounce Handler** (`tracking/bounce_handler.py`): Process bounce events from ISPs
4. **Dashboard** (`tracking/dashboard.py`): Web UI with metrics visualization
5. **CLI** (`tracking/cli.py`): Command-line tools for management
6. **Server** (`tracking/server.py`): WSGI-compatible server entry point

## API Overview

### Campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns` - List all campaigns
- `GET /api/campaigns/<id>` - Get campaign with metrics
- `DELETE /api/campaigns/<id>` - Delete campaign
- `GET /api/campaigns/<id>/export` - Export as CSV

### Messages
- `POST /api/messages` - Create message
- `GET /api/messages/<id>` - Get message details
- `POST /api/messages/<id>/sent` - Mark as sent
- `POST /api/messages/<id>/bounce` - Report bounce

### Tracking
- `GET /track/pixel/<token>` - Tracking pixel (embed in email)
- `GET /track/redirect/<token>?url=<url>` - Click tracking redirect

### Webhooks
- `POST /webhooks/sendgrid` - SendGrid event processing
- `POST /webhooks/gmail` - Gmail DSN processing

### Dashboard
- `GET /dashboard` - Web dashboard
- `GET /api/dashboard/summary` - JSON metrics summary

## CLI Commands

```bash
# Campaign management
email-tracking-cli campaign create --name "Newsletter"
email-tracking-cli campaign list
email-tracking-cli campaign show 1
email-tracking-cli campaign delete 1
email-tracking-cli campaign export 1 --output data.csv

# Message management
email-tracking-cli message create --campaign-id 1 --email user@example.com
email-tracking-cli message show 100
email-tracking-cli message mark-sent 100
email-tracking-cli message mark-opened 100
email-tracking-cli message mark-bounced 100 --reason "User unknown"

# Reporting
email-tracking-cli report summary
email-tracking-cli report bounces --limit 50
```

## Integration Example

```python
import uuid
from tracking import Database

db = Database()

# Create campaign
campaign_id = db.create_campaign("Newsletter")

# Create tracked message
token = str(uuid.uuid4())
message_id = db.create_message(
    campaign_id=campaign_id,
    recipient_email="user@example.com",
    tracking_token=token
)

# In email HTML, include:
# <img src="http://tracking.example.com/track/pixel/{token}" />
# <a href="http://tracking.example.com/track/redirect/{token}?url=https://example.com">Link</a>

# After sending
db.update_message_sent(message_id)

# When user opens/clicks, tracking automatically updates via endpoints
# View metrics
metrics = db.get_campaign_metrics(campaign_id)
print(f"Open rate: {metrics['open_rate']}%")
print(f"Click rate: {metrics['click_rate']}%")
```

## Deployment

### Development
```bash
python -m tracking.server
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 'tracking.server:create_tracking_app()'
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "tracking.server"]
```

### Environment Configuration
Create `.env` file:
```env
TRACKING_DB_PATH=tracking.db
TRACKING_HOST=0.0.0.0
TRACKING_PORT=5000
TRACKING_DEBUG=False
PUBLIC_TRACKING_URL=https://tracking.example.com
```

## Monitoring

### Health Check
```bash
curl http://localhost:5000/health
# {"status":"healthy"}
```

### Metrics API
```bash
curl http://localhost:5000/api/dashboard/summary
```

### CLI Reports
```bash
email-tracking-cli report summary
email-tracking-cli report bounces
```

## Database Management

### View Database Size
```bash
ls -lh tracking.db
```

### Query Database Directly
```bash
sqlite3 tracking.db "SELECT COUNT(*) FROM messages;"
```

### Backup
```bash
cp tracking.db tracking.db.backup
```

## Performance Considerations

- **Open Capacity**: Handles millions of tracking pixels per day (1x1 GIF is minimal)
- **Database**: SQLite suitable for most deployments; migrate to PostgreSQL for very high volume
- **Disk I/O**: Batch operations when possible
- **Memory**: Minimal memory usage; automatic cleanup of old data

## Troubleshooting

**Server won't start**: Check port is available (`lsof -i :5000`)

**Tracking not working**: Verify token is in database (`sqlite3 tracking.db "SELECT * FROM messages WHERE tracking_token='...';'`)

**Database locked**: Ensure only one server instance running; remove `.db-wal` and `.db-shm` files if necessary

**Webhooks not processing**: Verify webhook URL is publicly accessible and correct event types enabled

## Testing

```bash
# Run test suite
python test_tracking.py
```

## Project Structure

```
.
├── README.md                    # This file
├── QUICKSTART.md               # Quick start guide
├── TRACKING_GUIDE.md           # Complete documentation
├── INTEGRATION_EXAMPLE.md      # Integration patterns
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore rules
├── test_tracking.py           # Test suite
└── tracking/
    ├── __init__.py            # Package initialization
    ├── database.py            # SQLite database layer
    ├── app.py                 # Flask REST API
    ├── bounce_handler.py      # Bounce processing
    ├── dashboard.py           # Web dashboard
    ├── cli.py                 # CLI commands
    └── server.py              # Server entry point
```

## License

This project is part of the automatic bulk email sender system.

## Contributing

When integrating this service:

1. Generate unique tracking tokens for each message
2. Embed tracking pixels in email body
3. Wrap links with redirect tracking URLs
4. Configure webhooks for bounce handling
5. Monitor metrics via dashboard or API

## Future Enhancements

- PostgreSQL support for high-volume deployments
- Redis caching for faster metrics queries
- Advanced segmentation and A/B testing
- Machine learning for bounce prediction
- Multi-tenant support
- API authentication and rate limiting
- Mobile push notification tracking integration