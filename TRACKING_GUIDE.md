# Email Tracking Service Guide

A comprehensive email tracking system that monitors email delivery, opens, clicks, and bounces with a REST API, CLI tools, and web dashboard.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Tracking Server](#running-the-tracking-server)
5. [API Reference](#api-reference)
6. [CLI Commands](#cli-commands)
7. [Web Dashboard](#web-dashboard)
8. [Bounce Handling](#bounce-handling)
9. [Integration with Email Senders](#integration-with-email-senders)
10. [Monitoring](#monitoring)
11. [Troubleshooting](#troubleshooting)

## Overview

The Email Tracking Service provides:

- **SQLite Database**: Lightweight, file-based tracking of email lifecycle events
- **REST API**: Endpoints for managing campaigns, messages, and tracking events
- **Tracking Pixel**: 1x1 GIF endpoint to detect email opens
- **Redirect Tracking**: URL rewriting to track link clicks
- **Bounce Handling**: Integration with SendGrid webhooks and Gmail DSN parsing
- **CLI Tool**: Command-line interface for managing campaigns and generating reports
- **Web Dashboard**: Real-time metrics visualization
- **CSV Export**: Export campaign data for analysis

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Clone or navigate to the project directory:
```bash
cd /path/to/email-tracking-service
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .  # Install the package in development mode
```

3. Verify installation:
```bash
email-tracking-cli --help
```

## Configuration

Create a `.env` file in the project root to configure the tracking server:

```env
# Database configuration
TRACKING_DB_PATH=tracking.db

# Server configuration
TRACKING_HOST=0.0.0.0
TRACKING_PORT=5000
TRACKING_DEBUG=False

# Optional: webhook secret for validation
SENDGRID_WEBHOOK_SECRET=your_secret_here
```

## Running the Tracking Server

### Start the server

```bash
# Development mode with auto-reload
python -m tracking.server

# Or with specific configuration
TRACKING_PORT=8000 TRACKING_DEBUG=True python -m tracking.server
```

The server will start and display:
```
Starting Email Tracking Server on 0.0.0.0:5000
Dashboard: http://0.0.0.0:5000/dashboard
Health Check: http://0.0.0.0:5000/health
```

### Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 'tracking.server:create_tracking_app()'
```

For nginx reverse proxy configuration:
```nginx
server {
    listen 80;
    server_name tracking.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## API Reference

### Health Check

**GET** `/health`

Check if the tracking server is running.

```bash
curl http://localhost:5000/health
# Returns: {"status":"healthy"}
```

### Campaign Management

#### Create Campaign

**POST** `/api/campaigns`

Create a new campaign to track emails.

```bash
curl -X POST http://localhost:5000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Newsletter Q1 2024",
    "template_id": 1
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Newsletter Q1 2024",
  "created_at": "2024-01-15T10:30:00"
}
```

#### Get Campaign

**GET** `/api/campaigns/<campaign_id>`

Retrieve campaign details and metrics.

```bash
curl http://localhost:5000/api/campaigns/1
```

Response:
```json
{
  "id": 1,
  "name": "Newsletter Q1 2024",
  "template_id": 1,
  "created_at": "2024-01-15T10:30:00",
  "metrics": {
    "total": 1000,
    "queued": 0,
    "sent": 950,
    "opened": 475,
    "clicked": 95,
    "bounced": 45,
    "open_rate": 50.0,
    "click_rate": 10.0,
    "bounce_rate": 4.5,
    "bounce_reasons": {
      "Invalid email": 15,
      "User unknown": 30
    }
  }
}
```

#### List All Campaigns

**GET** `/api/campaigns`

List all campaigns with metrics.

```bash
curl http://localhost:5000/api/campaigns
```

#### Delete Campaign

**DELETE** `/api/campaigns/<campaign_id>`

Delete a campaign and all associated data.

```bash
curl -X DELETE http://localhost:5000/api/campaigns/1
```

### Message Management

#### Create Message

**POST** `/api/messages`

Create a new message record for tracking.

```bash
curl -X POST http://localhost:5000/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": 1,
    "recipient_email": "user@example.com",
    "tracking_token": "uuid-string-here",
    "template_id": 1
  }'
```

Response:
```json
{
  "id": 1234,
  "tracking_token": "uuid-string-here",
  "status": "queued",
  "created_at": "2024-01-15T10:35:00"
}
```

#### Get Message

**GET** `/api/messages/<message_id>`

Get details of a specific message.

```bash
curl http://localhost:5000/api/messages/1234
```

#### Mark Message as Sent

**POST** `/api/messages/<message_id>/sent`

Mark a message as successfully sent.

```bash
curl -X POST http://localhost:5000/api/messages/1234/sent \
  -H "Content-Type: application/json" \
  -d '{
    "sent_at": "2024-01-15T10:36:00"
  }'
```

### Tracking Endpoints

#### Tracking Pixel

**GET** `/track/pixel/<token>`

Returns a 1x1 GIF pixel. Used in email body to track opens.

```html
<img src="http://tracking.example.com/track/pixel/uuid-token" alt="" width="1" height="1" />
```

#### Click Tracking Redirect

**GET** `/track/redirect/<token>?url=<encoded_url>`

Tracks link clicks and redirects to the actual URL.

```html
<a href="http://tracking.example.com/track/redirect/uuid-token?url=https%3A%2F%2Fexample.com">Click here</a>
```

Response:
```json
{
  "redirect": "https://example.com",
  "tracked": true
}
```

#### Report Bounce (Manual)

**POST** `/api/messages/<message_id>/bounce`

Manually report a bounce for a message.

```bash
curl -X POST http://localhost:5000/api/messages/1234/bounce \
  -H "Content-Type: application/json" \
  -d '{
    "bounce_reason": "Invalid email address",
    "bounce_type": "permanent",
    "bounce_subtype": "Permanent",
    "diagnostic_code": "smtp; 550 5.1.1 user unknown"
  }'
```

### Campaign Messages

#### Get Campaign Messages

**GET** `/api/campaigns/<campaign_id>/messages?limit=100&offset=0`

Get messages for a campaign with pagination.

```bash
curl 'http://localhost:5000/api/campaigns/1/messages?limit=20&offset=0'
```

#### Export Campaign Data

**GET** `/api/campaigns/<campaign_id>/export`

Export all campaign messages as CSV file.

```bash
curl http://localhost:5000/api/campaigns/1/export > campaign_data.csv
```

## CLI Commands

The CLI tool provides command-line access to all tracking features.

### Campaign Commands

#### Create a campaign

```bash
email-tracking-cli campaign create --name "Summer Sale 2024" --template-id 5
```

#### List campaigns

```bash
email-tracking-cli campaign list
```

Output:
```
╒════╤════════════════════╤═══════╤══════╤════════╤═════════╤═════════╤═════════╤═══════╤════════╕
│ ID │ Name               │ Total │ Sent │ Opened │ Clicked │ Bounced │ Open %  │ Click │ Bounce │
╞════╪════════════════════╪═══════╪══════╪════════╪═════════╪═════════╪═════════╪═══════╪════════╡
│  1 │ Summer Sale 2024   │  1000 │  950 │    475 │      95 │      45 │ 50.0    │ 10.0  │  4.5   │
╘════╧════════════════════╧═══════╧══════╧════════╧═════════╧═════════╧═════════╧═══════╧════════╛
```

#### Show campaign details

```bash
email-tracking-cli campaign show 1
```

#### Show messages in campaign

```bash
email-tracking-cli campaign messages 1 --limit 10
```

#### Export campaign to CSV

```bash
email-tracking-cli campaign export 1 --output campaign_1.csv
```

#### Delete campaign

```bash
email-tracking-cli campaign delete 1
```

### Message Commands

#### Create message

```bash
email-tracking-cli message create \
  --campaign-id 1 \
  --email user@example.com \
  --token custom-token-123
```

#### Show message details

```bash
email-tracking-cli message show 1234
```

#### Mark as sent

```bash
email-tracking-cli message mark-sent 1234
```

#### Mark as opened

```bash
email-tracking-cli message mark-opened 1234
```

#### Mark as clicked

```bash
email-tracking-cli message mark-clicked 1234
```

#### Mark as bounced

```bash
email-tracking-cli message mark-bounced 1234 --reason "User unknown" --type permanent
```

### Report Commands

#### Summary report

```bash
email-tracking-cli report summary
```

Output:
```
=== Email Tracking Summary ===
Total Campaigns: 5
Total Messages: 5000
Total Sent: 4750
Total Opened: 2375
Total Clicked: 475
Total Bounced: 225

Aggregate Rates:
  Open Rate: 50.0%
  Click Rate: 10.0%
  Bounce Rate: 4.5%
```

#### Bounce report

```bash
email-tracking-cli report bounces --campaign-id 1 --limit 20
```

## Web Dashboard

Access the real-time dashboard at `http://localhost:5000/dashboard`

The dashboard displays:

- **Summary Cards**: Key metrics overview
  - Total campaigns
  - Total emails sent
  - Open rate
  - Click rate
  - Bounce rate

- **Campaign Table**: Detailed per-campaign metrics
  - Campaign name
  - Total messages
  - Status breakdown (sent, opened, clicked, bounced)
  - Engagement rates

Features:
- Auto-refreshes every 30 seconds
- Click campaign names to view details
- Responsive design for mobile and desktop

### JSON API Endpoint

Get dashboard data programmatically:

```bash
curl http://localhost:5000/api/dashboard/summary
```

Response:
```json
{
  "total_campaigns": 5,
  "total_messages": 5000,
  "total_sent": 4750,
  "total_opened": 2375,
  "total_clicked": 475,
  "total_bounced": 225,
  "open_rate": 50.0,
  "click_rate": 10.0,
  "bounce_rate": 4.5
}
```

## Bounce Handling

The tracking service integrates with email service providers to automatically handle bounces.

### SendGrid Webhooks

#### Setup

1. In SendGrid dashboard, go to Settings > Mail Send > Event Webhook
2. Set Webhook URL to: `http://your-domain.com/webhooks/sendgrid`
3. Subscribe to events:
   - Bounce
   - Delivered
   - Open
   - Click

#### Event Processing

The service automatically processes SendGrid events:

```json
{
  "event": "bounce",
  "email": "user@example.com",
  "sg_message_id": "tracking-token",
  "bounce_type": "permanent",
  "reason": "Permanent error: 550 5.1.1 user unknown"
}
```

### Gmail Delivery Status Notifications

For emails sent via Gmail, the service can parse bounce notifications:

#### Manual Processing

```bash
curl -X POST http://localhost:5000/webhooks/gmail \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": 1234,
    "status": "permanent-failure",
    "reason": "User unknown",
    "diagnostic_code": "smtp; 550 5.1.1 user unknown"
  }'
```

### Bounce Recovery Strategies

For temporary bounces, you may want to retry:

```bash
# Check bounce type
email-tracking-cli message show 1234

# If bounce_type is "temporary", retry sending
# If bounce_type is "permanent", remove from list
```

## Integration with Email Senders

### Embedding Tracking Tokens

When sending emails, include unique tracking tokens:

```python
import uuid
from tracking import Database

db = Database()

# Create campaign
campaign_id = db.create_campaign("Weekly Newsletter")

# Create message with tracking token
token = str(uuid.uuid4())
message_id = db.create_message(
    campaign_id=campaign_id,
    recipient_email="user@example.com",
    tracking_token=token
)

# In email HTML body:
tracking_pixel = f'<img src="http://tracking.example.com/track/pixel/{token}" width="1" height="1" />'

# Transform links:
original_url = "https://example.com/offer"
tracking_url = f'http://tracking.example.com/track/redirect/{token}?url={urllib.parse.quote(original_url)}'
```

### Example: Integration with Sender Service

```python
from tracking import Database
import requests

db = Database()

# Create campaign and message
campaign_id = db.create_campaign("Product Launch")
message_id = db.create_message(
    campaign_id=campaign_id,
    recipient_email="customer@example.com",
    tracking_token="unique-token-123"
)

# Send email via SendGrid or similar
response = requests.post('https://api.sendgrid.com/v3/mail/send', ...)

# Mark as sent in tracking DB
db.update_message_sent(message_id)
```

## Monitoring

### Database Health

Check database size:

```bash
ls -lh tracking.db
```

Monitor for performance issues with large databases:

```bash
# Analyze database
sqlite3 tracking.db
sqlite> ANALYZE;
sqlite> .quit

# Get statistics
email-tracking-cli report summary
```

### Log Files

The tracking server logs to console by default. For production, redirect to file:

```bash
TRACKING_DEBUG=False python -m tracking.server > tracking.log 2>&1 &
```

### Health Check Monitoring

Periodically check server health:

```bash
# Simple curl-based monitoring
curl -s http://localhost:5000/health | grep healthy
```

Add to crontab for regular checks:

```bash
*/5 * * * * curl -s http://localhost:5000/health | grep -q healthy || systemctl restart tracking-server
```

### Metrics to Monitor

- **Open Rate**: Should be 30-50% for most campaigns
- **Click Rate**: Typically 5-15% of opens
- **Bounce Rate**: Should be < 2% for healthy lists
- **Database Size**: Monitor for growth

## Troubleshooting

### Tracking pixels not working

1. Verify pixel URL is accessible from outside:
```bash
curl -v http://your-domain.com/track/pixel/token-here
```

2. Check database connectivity:
```bash
email-tracking-cli report summary
```

3. Verify tracking token exists in database:
```bash
sqlite3 tracking.db "SELECT * FROM messages WHERE tracking_token='token-here';"
```

### Bounces not being processed

1. Verify webhook URL is accessible
2. Check webhook configuration in SendGrid dashboard
3. Monitor webhook requests:
```bash
curl -v -X POST http://localhost:5000/webhooks/sendgrid -d '{"test": true}'
```

### Database lock errors

This usually indicates concurrent access issues:

1. Ensure only one server instance is running
2. Check file permissions: `chmod 644 tracking.db`
3. For high-volume scenarios, consider PostgreSQL instead

### High memory usage

If handling many campaigns:

1. Limit message list pagination
2. Implement archival of old campaigns
3. Consider database optimization

## Advanced Configuration

### Rotating Backups

Create daily backups:

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
cp tracking.db tracking.db.backup.$DATE
gzip tracking.db.backup.$DATE
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### Performance Optimization

For large-scale deployments:

1. Migrate to PostgreSQL:
```python
# Modify database.py to use psycopg2
```

2. Add database indexes (automatically created):
```bash
sqlite3 tracking.db
sqlite> CREATE INDEX IF NOT EXISTS idx_messages_campaign_id ON messages(campaign_id);
```

3. Implement caching with Redis (future enhancement)

## Support and Feedback

For issues or feature requests, please refer to the project documentation or contact the development team.
