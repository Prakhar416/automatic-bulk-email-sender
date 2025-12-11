# Integration Examples

This guide shows how to integrate the Email Tracking Service with your email sending application.

## Table of Contents

1. [Basic Integration](#basic-integration)
2. [SendGrid Integration](#sendgrid-integration)
3. [Flask Application Integration](#flask-application-integration)
4. [Command-line Integration](#command-line-integration)

## Basic Integration

### Simple Python Integration

```python
import uuid
from tracking import Database

# Initialize tracking database
db = Database('tracking.db')

def send_tracked_email(campaign_name, recipient_email, email_html):
    """Send an email with tracking enabled."""
    
    # Create campaign if it doesn't exist
    campaign = db.get_campaign(1)  # or create new one
    if not campaign:
        campaign_id = db.create_campaign(campaign_name)
    else:
        campaign_id = campaign['id']
    
    # Generate unique tracking token
    tracking_token = str(uuid.uuid4())
    
    # Create message record in tracking database
    message_id = db.create_message(
        campaign_id=campaign_id,
        recipient_email=recipient_email,
        tracking_token=tracking_token
    )
    
    # Modify email HTML to include tracking
    tracking_pixel = f'<img src="http://tracking.example.com/track/pixel/{tracking_token}" width="1" height="1" style="display:none;" />'
    email_html_with_tracking = email_html + tracking_pixel
    
    # Replace links with tracked versions
    import re
    import urllib.parse
    
    def replace_links(match):
        url = match.group(1)
        encoded_url = urllib.parse.quote(url, safe='/:')
        tracking_url = f'http://tracking.example.com/track/redirect/{tracking_token}?url={encoded_url}'
        return f'href="{tracking_url}"'
    
    email_html_with_tracking = re.sub(
        r'href=["\']([^"\']+)["\']',
        replace_links,
        email_html_with_tracking
    )
    
    # Send email via your email service
    # send_via_your_service(recipient_email, subject, email_html_with_tracking)
    
    # Mark as sent in tracking DB
    db.update_message_sent(message_id)
    
    return tracking_token, message_id
```

## SendGrid Integration

### Full SendGrid Integration Example

```python
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import uuid
from tracking import Database

class SendGridTrackingClient:
    def __init__(self, sendgrid_api_key, tracking_server_url):
        self.sg = sendgrid.SendGridAPIClient(sendgrid_api_key)
        self.tracking_url = tracking_server_url
        self.db = Database()
    
    def send_tracked_email(self, campaign_name, to_email, subject, html_content):
        """Send email with SendGrid and tracking."""
        
        # Create campaign
        campaign_id = self.db.create_campaign(campaign_name)
        
        # Generate tracking token
        tracking_token = str(uuid.uuid4())
        
        # Create message record
        message_id = self.db.create_message(
            campaign_id=campaign_id,
            recipient_email=to_email,
            tracking_token=tracking_token
        )
        
        # Prepare HTML with tracking
        tracking_html = self._add_tracking_to_html(
            html_content,
            tracking_token
        )
        
        # Create and send email
        from_email = Email("noreply@example.com")
        to = To(to_email)
        mail = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
            html_content=tracking_html
        )
        
        # Add custom args for webhook tracking
        mail.custom_args = {
            "tracking_token": tracking_token,
            "message_id": str(message_id),
            "campaign_id": str(campaign_id)
        }
        
        try:
            response = self.sg.send(mail)
            
            # Mark as sent
            self.db.update_message_sent(message_id)
            
            return {
                'status': 'sent',
                'message_id': message_id,
                'tracking_token': tracking_token,
                'sendgrid_status': response.status_code
            }
        
        except Exception as e:
            # Record error
            self.db.db.execute(
                "UPDATE messages SET error_message = ? WHERE id = ?",
                (str(e), message_id)
            )
            raise
    
    def _add_tracking_to_html(self, html, token):
        """Add tracking pixel and link redirects to HTML."""
        import re
        import urllib.parse
        
        # Add tracking pixel before closing body tag
        tracking_pixel = f'''<img src="{self.tracking_url}/track/pixel/{token}" width="1" height="1" style="display:none;" alt="" />'''
        
        html = html.replace('</body>', f'{tracking_pixel}</body>')
        
        # Replace links
        def replace_link(match):
            url = match.group(1)
            if url.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                return match.group(0)  # Don't track these
            
            encoded_url = urllib.parse.quote(url, safe='/:?=&')
            tracking_url = f'{self.tracking_url}/track/redirect/{token}?url={encoded_url}'
            return f'href="{tracking_url}"'
        
        html = re.sub(r'href=["\']([^"\']+)["\']', replace_link, html)
        
        return html


# Usage example
if __name__ == '__main__':
    client = SendGridTrackingClient(
        sendgrid_api_key='YOUR_SENDGRID_API_KEY',
        tracking_server_url='https://tracking.example.com'
    )
    
    result = client.send_tracked_email(
        campaign_name='Newsletter Jan 2024',
        to_email='user@example.com',
        subject='Monthly Newsletter',
        html_content='''
        <html>
            <body>
                <h1>January Newsletter</h1>
                <p>Check out our latest updates:</p>
                <a href="https://example.com/updates">Read more</a>
            </body>
        </html>
        '''
    )
    
    print(f"Email sent! Tracking token: {result['tracking_token']}")
```

## Flask Application Integration

### Integrate with Your Flask App

```python
from flask import Flask, render_template, request
from tracking import Database, create_app
import uuid

app = Flask(__name__)

# Create tracking app
tracking_app = create_app('tracking.db')

# Initialize database
db = Database('tracking.db')

@app.route('/campaigns/create', methods=['POST'])
def create_campaign():
    """Create a new campaign for email sending."""
    data = request.json
    campaign_id = db.create_campaign(data['name'], data.get('template_id'))
    return {'campaign_id': campaign_id}


@app.route('/emails/send', methods=['POST'])
def send_email():
    """Send email with tracking."""
    data = request.json
    campaign_id = data['campaign_id']
    recipient_email = data['email']
    subject = data['subject']
    html_content = data['html']
    
    # Create tracking token
    tracking_token = str(uuid.uuid4())
    
    # Create message in tracking DB
    message_id = db.create_message(
        campaign_id=campaign_id,
        recipient_email=recipient_email,
        tracking_token=tracking_token
    )
    
    # Add tracking to HTML
    html_with_tracking = _add_tracking(html_content, tracking_token)
    
    # Send email (implement with your email service)
    # send_email_service(recipient_email, subject, html_with_tracking)
    
    # Mark as sent
    db.update_message_sent(message_id)
    
    return {
        'message_id': message_id,
        'tracking_token': tracking_token,
        'status': 'sent'
    }


@app.route('/campaigns/<int:campaign_id>/metrics', methods=['GET'])
def get_campaign_metrics(campaign_id):
    """Get campaign metrics."""
    metrics = db.get_campaign_metrics(campaign_id)
    return metrics


def _add_tracking(html, token):
    """Add tracking to HTML content."""
    import re
    import urllib.parse
    
    tracking_pixel = f'<img src="/track/pixel/{token}" width="1" height="1" style="display:none;" />'
    html = html.replace('</body>', f'{tracking_pixel}</body>')
    
    def replace_link(match):
        url = match.group(1)
        if url.startswith(('mailto:', 'tel:')):
            return match.group(0)
        encoded_url = urllib.parse.quote(url, safe='/:?=&')
        return f'href="/track/redirect/{token}?url={encoded_url}"'
    
    html = re.sub(r'href=["\']([^"\']+)["\']', replace_link, html)
    return html


if __name__ == '__main__':
    app.run(debug=True)
```

## Command-line Integration

### Batch Processing Script

```python
#!/usr/bin/env python
"""Batch email sending with tracking."""

import sys
import csv
import uuid
import argparse
from tracking import Database


def send_batch_emails(csv_file, campaign_name, dry_run=False):
    """Send emails from CSV with tracking."""
    
    db = Database()
    
    # Create campaign
    campaign_id = db.create_campaign(campaign_name)
    print(f"Campaign created: {campaign_id}")
    
    sent_count = 0
    error_count = 0
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                recipient_email = row['email']
                token = str(uuid.uuid4())
                
                # Create message
                message_id = db.create_message(
                    campaign_id=campaign_id,
                    recipient_email=recipient_email,
                    tracking_token=token
                )
                
                if dry_run:
                    print(f"[DRY RUN] Would send to {recipient_email} (token: {token})")
                else:
                    # Send email (implement your logic)
                    # send_email(recipient_email, ...)
                    
                    db.update_message_sent(message_id)
                    print(f"✓ Sent to {recipient_email}")
                
                sent_count += 1
            
            except Exception as e:
                print(f"✗ Error with {row.get('email', 'unknown')}: {e}")
                error_count += 1
    
    print(f"\nSummary:")
    print(f"  Sent: {sent_count}")
    print(f"  Errors: {error_count}")
    print(f"  Campaign ID: {campaign_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send batch emails with tracking')
    parser.add_argument('csv_file', help='CSV file with emails')
    parser.add_argument('--campaign', required=True, help='Campaign name')
    parser.add_argument('--dry-run', action='store_true', help='Test without sending')
    
    args = parser.parse_args()
    
    send_batch_emails(args.csv_file, args.campaign, args.dry_run)
```

Usage:
```bash
python batch_send.py recipients.csv --campaign "Spring Promo" --dry-run
```

CSV format (recipients.csv):
```
email,name,product
user1@example.com,John Doe,Product A
user2@example.com,Jane Smith,Product B
```

## Webhook Processing

### Handle SendGrid Webhooks

```python
from flask import Flask, request, jsonify
from tracking import Database, BounceHandler

app = Flask(__name__)
db = Database()
bounce_handler = BounceHandler(db)


@app.route('/webhooks/sendgrid', methods=['POST'])
def sendgrid_webhook():
    """Process SendGrid webhook events."""
    
    events = request.get_json()
    
    if not isinstance(events, list):
        events = [events]
    
    processed = 0
    for event in events:
        try:
            bounce_handler.handle_sendgrid_event(event)
            processed += 1
        except Exception as e:
            print(f"Error processing event: {e}")
    
    return jsonify({'processed': processed}), 200
```

### Example Event Processing

```python
# When SendGrid sends an event like:
{
    "event": "bounce",
    "email": "user@example.com",
    "sg_message_id": "YOUR_TRACKING_TOKEN",
    "timestamp": 1234567890,
    "bounce_type": "permanent",
    "reason": "Permanent error: 550 5.1.1 user unknown",
    "custom_args": {
        "tracking_token": "YOUR_TRACKING_TOKEN",
        "message_id": "1234"
    }
}

# The service automatically:
# 1. Finds the message using the token
# 2. Updates message status to 'bounced'
# 3. Records bounce details in database
# 4. Logs the event
```

## Monitoring Integration

### Real-time Metrics

```python
# Get current metrics
db = Database()
campaign = db.get_campaign(1)
metrics = db.get_campaign_metrics(1)

print(f"Campaign: {campaign['name']}")
print(f"Total sent: {metrics['sent']}")
print(f"Open rate: {metrics['open_rate']}%")
print(f"Click rate: {metrics['click_rate']}%")
print(f"Bounce rate: {metrics['bounce_rate']}%")
```

### Export Data

```python
# Export campaign data
csv_data = db.export_campaign_to_csv(campaign_id)

with open(f'campaign_{campaign_id}_export.csv', 'w') as f:
    f.write(csv_data)

print(f"Exported campaign {campaign_id}")
```

## Error Handling

```python
from tracking import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

def send_email_with_tracking(recipient, subject, html):
    try:
        # Create campaign and message
        campaign_id = db.create_campaign('Test')
        token = str(uuid.uuid4())
        message_id = db.create_message(campaign_id, recipient, token)
        
        # Send email
        # send_email(recipient, subject, add_tracking(html, token))
        
        db.update_message_sent(message_id)
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        # Update message with error
        try:
            cursor = db.db.cursor()
            cursor.execute(
                "UPDATE messages SET error_message = ? WHERE id = ?",
                (str(e), message_id)
            )
            db.db.commit()
        except:
            pass
        raise
```

## Advanced: Custom Tracking Fields

```python
def create_message_with_metadata(campaign_id, recipient_email, tracking_token, metadata=None):
    """Create message with custom metadata."""
    db = Database()
    
    message_id = db.create_message(
        campaign_id=campaign_id,
        recipient_email=recipient_email,
        tracking_token=tracking_token
    )
    
    # Store metadata as JSON event
    if metadata:
        import json
        db.add_message_event(
            message_id,
            'metadata',
            json.dumps(metadata)
        )
    
    return message_id

# Usage
metadata = {
    'customer_id': 12345,
    'segment': 'premium',
    'product': 'Product A',
    'utm_source': 'newsletter'
}

message_id = create_message_with_metadata(
    campaign_id=1,
    recipient_email='user@example.com',
    tracking_token=str(uuid.uuid4()),
    metadata=metadata
)
```

These integration examples cover the most common use cases. Adapt them to your specific email sending infrastructure.
