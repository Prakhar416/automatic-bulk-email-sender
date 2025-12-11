# Email Tracking Service - Quick Start Guide

Get up and running with the email tracking service in 5 minutes.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

## Start the Tracking Server

```bash
# Terminal 1 - Start the server
python -m tracking.server

# You should see:
# Starting Email Tracking Server on 0.0.0.0:5000
# Dashboard: http://0.0.0.0:5000/dashboard
```

## Create Your First Campaign

```bash
# Terminal 2 - Create a campaign
email-tracking-cli campaign create --name "My First Campaign"

# Output: Campaign created with ID: 1
```

## Create Messages to Track

```bash
# Create a message
email-tracking-cli message create \
  --campaign-id 1 \
  --email user@example.com

# Output:
# Message created with ID: 1
# Tracking token: <uuid-here>
```

## View the Dashboard

Open your browser and navigate to:
```
http://localhost:5000/dashboard
```

You'll see a real-time dashboard with metrics.

## Track Email Events via API

### Mark as Sent
```bash
curl -X POST http://localhost:5000/api/messages/1/sent
```

### Open Tracking (Pixel)
```bash
# The pixel URL to embed in email HTML:
# <img src="http://localhost:5000/track/pixel/TOKEN" width="1" height="1" />

curl "http://localhost:5000/track/pixel/YOUR_TOKEN"
```

### Click Tracking
```bash
# Redirect URL to wrap links:
# http://localhost:5000/track/redirect/TOKEN?url=https%3A%2F%2Fexample.com

curl "http://localhost:5000/track/redirect/YOUR_TOKEN?url=https%3A%2F%2Fexample.com"
```

### Report a Bounce
```bash
curl -X POST http://localhost:5000/api/messages/1/bounce \
  -H "Content-Type: application/json" \
  -d '{
    "bounce_reason": "User unknown",
    "bounce_type": "permanent"
  }'
```

## View Campaign Statistics

### Via CLI
```bash
email-tracking-cli campaign show 1
```

### Via API
```bash
curl http://localhost:5000/api/campaigns/1
```

### Get Summary Report
```bash
email-tracking-cli report summary
```

## Export Campaign Data

```bash
# Export to CSV
email-tracking-cli campaign export 1 --output campaign_data.csv
```

## Common Workflows

### Workflow 1: Tracking an Email Campaign

```bash
# 1. Create campaign
CAMPAIGN_ID=$(email-tracking-cli campaign create --name "Promo" | grep ID | awk '{print $NF}')

# 2. Create message with tracking token
TOKEN=$(uuidgen)
MESSAGE_ID=$(email-tracking-cli message create \
  --campaign-id $CAMPAIGN_ID \
  --email customer@example.com \
  --token $TOKEN | grep ID | awk '{print $NF}')

# 3. Send email with tracking:
# - Body includes: <img src="http://tracking.example.com/track/pixel/$TOKEN" />
# - Links wrapped: http://tracking.example.com/track/redirect/$TOKEN?url=<URL>

# 4. Mark as sent
curl -X POST http://localhost:5000/api/messages/$MESSAGE_ID/sent

# 5. Check metrics
email-tracking-cli campaign show $CAMPAIGN_ID
```

### Workflow 2: Handling Bounces from SendGrid

```bash
# 1. Set webhook in SendGrid dashboard:
#    URL: http://your-server.com/webhooks/sendgrid
#    Events: bounce, delivered, open, click

# 2. SendGrid will automatically POST bounce events
#    Service processes them and updates message status

# 3. View bounce report
email-tracking-cli report bounces --campaign-id 1
```

### Workflow 3: Real-time Dashboard Monitoring

```bash
# 1. Open dashboard in browser
# http://localhost:5000/dashboard

# 2. Dashboard auto-refreshes every 30 seconds

# 3. Monitor key metrics:
# - Open Rate
# - Click Rate  
# - Bounce Rate
```

## Database Management

### View all campaigns
```bash
email-tracking-cli campaign list
```

### View all messages in campaign
```bash
email-tracking-cli campaign messages 1 --limit 50
```

### Delete campaign (and all messages)
```bash
email-tracking-cli campaign delete 1
```

### Check database
```bash
# Size
ls -lh tracking.db

# Direct SQL query
sqlite3 tracking.db "SELECT COUNT(*) FROM messages;"
```

## Testing the Endpoints

### Health Check
```bash
curl http://localhost:5000/health
# {"status":"healthy"}
```

### List Campaigns
```bash
curl http://localhost:5000/api/campaigns
# Returns JSON array of campaigns with metrics
```

### Get Campaign Details
```bash
curl http://localhost:5000/api/campaigns/1
# Returns detailed campaign with metrics
```

### Get Campaign Messages
```bash
curl 'http://localhost:5000/api/campaigns/1/messages?limit=10'
# Returns list of messages with pagination
```

### Get Dashboard Summary
```bash
curl http://localhost:5000/api/dashboard/summary
# Returns JSON with overall metrics
```

## Configuration

Create a `.env` file to customize settings:

```env
# Database
TRACKING_DB_PATH=tracking.db

# Server
TRACKING_HOST=0.0.0.0
TRACKING_PORT=5000
TRACKING_DEBUG=False
```

## Next Steps

1. **Integrate with Email Sender**: Update your email sending code to include tracking tokens
2. **Setup Webhooks**: Configure SendGrid/Gmail webhooks for bounce handling
3. **Deploy**: Run on production server with Gunicorn or similar
4. **Monitor**: Set up regular health checks and metric monitoring

## Troubleshooting

### Server won't start
```bash
# Check port is available
lsof -i :5000

# Use different port
TRACKING_PORT=8000 python -m tracking.server
```

### Database locked
```bash
# Check for running processes
ps aux | grep tracking

# Remove stale lock file if needed
rm tracking.db-wal tracking.db-shm 2>/dev/null
```

### Import errors
```bash
# Reinstall package
pip install -e .

# Check Python version
python --version  # Should be 3.8+
```

## More Information

For detailed documentation, see:
- `TRACKING_GUIDE.md` - Complete API and configuration reference
- `README.md` - Project overview

## Example: Complete Flow

```bash
#!/bin/bash
# Example script to demonstrate tracking flow

# 1. Create campaign
echo "Creating campaign..."
CAMPAIGN_ID=1
email-tracking-cli campaign create --name "Example Campaign" || true

# 2. Create test message
echo "Creating message..."
TOKEN=$(python -c "import uuid; print(str(uuid.uuid4()))")
MESSAGE_ID=1
email-tracking-cli message create \
  --campaign-id $CAMPAIGN_ID \
  --email test@example.com \
  --token $TOKEN || true

# 3. Simulate sending
echo "Marking as sent..."
curl -X POST http://localhost:5000/api/messages/$MESSAGE_ID/sent

# 4. Simulate open
echo "Simulating open..."
curl "http://localhost:5000/track/pixel/$TOKEN"

# 5. Simulate click
echo "Simulating click..."
curl "http://localhost:5000/track/redirect/$TOKEN?url=https://example.com"

# 6. View results
echo -e "\n\nCampaign metrics:"
email-tracking-cli campaign show $CAMPAIGN_ID
```

Save as `test_tracking.sh` and run:
```bash
chmod +x test_tracking.sh
./test_tracking.sh
```

Happy tracking! 📧📊
