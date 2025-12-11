import json
from typing import Dict, Any, Optional
from .database import Database


class BounceHandler:
    """Handle bounce events from various email services."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def handle_sendgrid_event(self, event: Dict[str, Any]) -> Optional[int]:
        """
        Handle SendGrid webhook events.
        
        Expected event structure:
        {
            "event": "bounce",
            "email": "test@example.com",
            "timestamp": 1234567890,
            "sg_event_id": "...",
            "token": "tracking_token",  # or in custom args
            "message_id": message_id,
            "bounce_type": "permanent" or "temporary",
            "bounce_reason": "Permanent error",
            ...
        }
        """
        event_type = event.get('event', '').lower()
        
        # Handle bounce events
        if event_type == 'bounce':
            return self._handle_sendgrid_bounce(event)
        
        # Handle delivery events
        elif event_type == 'delivered':
            return self._handle_sendgrid_delivered(event)
        
        # Handle open events
        elif event_type == 'open':
            return self._handle_sendgrid_open(event)
        
        # Handle click events
        elif event_type == 'click':
            return self._handle_sendgrid_click(event)
        
        return None
    
    def _handle_sendgrid_bounce(self, event: Dict[str, Any]) -> Optional[int]:
        """Handle SendGrid bounce event."""
        # Try to find message by tracking token
        token = event.get('sg_message_id') or event.get('token')
        email = event.get('email')
        
        message = None
        if token:
            message = self.db.get_message_by_token(token)
        
        if not message and email:
            # If we can't find by token, this is a fallback
            # In production, you'd want proper token mapping
            return None
        
        if message:
            bounce_type = event.get('bounce_type', 'permanent')
            bounce_reason = event.get('reason', 'Unspecified bounce')
            
            self.db.update_message_bounced(
                message['id'],
                bounce_reason=bounce_reason,
                bounce_type=bounce_type
            )
            
            self.db.add_bounce(
                message['id'],
                bounce_type=bounce_type,
                bounce_reason=bounce_reason,
                bounce_subtype=event.get('bounce_subtype'),
                diagnostic_code=event.get('diagnostic_code'),
                source='sendgrid'
            )
            
            return message['id']
        
        return None
    
    def _handle_sendgrid_delivered(self, event: Dict[str, Any]) -> Optional[int]:
        """Handle SendGrid delivered event."""
        token = event.get('sg_message_id') or event.get('token')
        
        if token:
            message = self.db.get_message_by_token(token)
            if message:
                self.db.update_message_sent(message['id'])
                return message['id']
        
        return None
    
    def _handle_sendgrid_open(self, event: Dict[str, Any]) -> Optional[int]:
        """Handle SendGrid open event."""
        token = event.get('sg_message_id') or event.get('token')
        
        if token:
            message = self.db.get_message_by_token(token)
            if message:
                self.db.update_message_opened(message['id'])
                self.db.add_message_event(message['id'], 'opened', json.dumps({
                    'source': 'sendgrid_webhook',
                    'timestamp': event.get('timestamp'),
                    'user_agent': event.get('useragent'),
                    'ip': event.get('ip')
                }))
                return message['id']
        
        return None
    
    def _handle_sendgrid_click(self, event: Dict[str, Any]) -> Optional[int]:
        """Handle SendGrid click event."""
        token = event.get('sg_message_id') or event.get('token')
        url = event.get('url')
        
        if token:
            message = self.db.get_message_by_token(token)
            if message:
                self.db.update_message_clicked(message['id'])
                if url:
                    self.db.track_link_click(
                        message['id'],
                        url,
                        user_agent=event.get('useragent'),
                        ip_address=event.get('ip')
                    )
                self.db.add_message_event(message['id'], 'clicked', json.dumps({
                    'source': 'sendgrid_webhook',
                    'url': url,
                    'timestamp': event.get('timestamp'),
                    'user_agent': event.get('useragent'),
                    'ip': event.get('ip')
                }))
                return message['id']
        
        return None
    
    def handle_gmail_notification(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Handle Gmail delivery status notifications.
        
        Gmail sends delivery status via email headers like:
        Delivery-Status: permanent-failure
        Remote-MTA: smtp.google.com
        Diagnostic-Code: smtp; 550 5.1.1 user unknown
        
        This would typically be parsed from bounce emails.
        The data structure here is custom and depends on how you parse Gmail DSNs.
        """
        message_id = data.get('message_id')
        token = data.get('token')
        
        message = None
        if message_id:
            message = self.db.get_message(message_id)
        elif token:
            message = self.db.get_message_by_token(token)
        
        if not message:
            return None
        
        status = data.get('status', '').lower()
        
        if 'bounce' in status or 'failure' in status or 'failed' in status:
            bounce_type = 'permanent' if 'permanent' in status else 'temporary'
            bounce_reason = data.get('reason', 'Gmail delivery failed')
            
            self.db.update_message_bounced(
                message['id'],
                bounce_reason=bounce_reason,
                bounce_type=bounce_type
            )
            
            self.db.add_bounce(
                message['id'],
                bounce_type=bounce_type,
                bounce_reason=bounce_reason,
                bounce_subtype=data.get('subtype'),
                diagnostic_code=data.get('diagnostic_code'),
                source='gmail'
            )
            
            return message['id']
        
        elif 'delivered' in status or 'success' in status:
            self.db.update_message_sent(message['id'])
            return message['id']
        
        return None
    
    def process_bounce_email(self, bounce_email_data: Dict[str, Any]) -> Optional[int]:
        """
        Process a bounce email (Delivery Status Notification).
        
        This is a generic method for processing DSN emails that might come
        from Gmail, Outlook, or other services.
        """
        # Extract message token from headers or body
        token = (
            bounce_email_data.get('original_token') or
            bounce_email_data.get('x_tracking_token') or
            bounce_email_data.get('message_id')
        )
        
        if not token:
            return None
        
        message = self.db.get_message_by_token(token)
        if not message:
            return None
        
        # Determine bounce type and reason
        bounce_type = bounce_email_data.get('bounce_type', 'permanent')
        bounce_reason = bounce_email_data.get('bounce_reason', 'Unspecified bounce')
        diagnostic_code = bounce_email_data.get('diagnostic_code')
        
        self.db.update_message_bounced(
            message['id'],
            bounce_reason=bounce_reason,
            bounce_type=bounce_type
        )
        
        self.db.add_bounce(
            message['id'],
            bounce_type=bounce_type,
            bounce_reason=bounce_reason,
            bounce_subtype=bounce_email_data.get('bounce_subtype'),
            diagnostic_code=diagnostic_code,
            source='bounce_email'
        )
        
        return message['id']
