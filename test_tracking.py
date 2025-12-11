#!/usr/bin/env python
"""
Test script for email tracking service.
Verifies all major components work correctly.
"""

import os
import json
import uuid
import tempfile
import sys
from tracking.database import Database
from tracking.app import create_app
from tracking.bounce_handler import BounceHandler


def test_database():
    """Test database operations."""
    print("Testing Database...")
    
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        
        # Test campaign creation
        campaign_id = db.create_campaign("Test Campaign", template_id=1)
        assert campaign_id > 0, "Campaign creation failed"
        
        # Test campaign retrieval
        campaign = db.get_campaign(campaign_id)
        assert campaign is not None, "Campaign retrieval failed"
        assert campaign['name'] == "Test Campaign"
        
        # Test message creation
        token = str(uuid.uuid4())
        message_id = db.create_message(
            campaign_id=campaign_id,
            recipient_email="test@example.com",
            tracking_token=token
        )
        assert message_id > 0, "Message creation failed"
        
        # Test message retrieval
        message = db.get_message(message_id)
        assert message is not None, "Message retrieval failed"
        assert message['tracking_token'] == token
        
        # Test message by token
        message_by_token = db.get_message_by_token(token)
        assert message_by_token is not None, "Message retrieval by token failed"
        
        # Test status updates
        db.update_message_sent(message_id)
        message = db.get_message(message_id)
        assert message['status'] == 'sent', "Sent status update failed"
        
        db.update_message_opened(message_id)
        message = db.get_message(message_id)
        assert message['status'] == 'opened', "Opened status update failed"
        
        # Create new message for click test
        token2 = str(uuid.uuid4())
        message_id2 = db.create_message(
            campaign_id=campaign_id,
            recipient_email="test2@example.com",
            tracking_token=token2
        )
        db.update_message_sent(message_id2)
        
        db.update_message_clicked(message_id2)
        message2 = db.get_message(message_id2)
        assert message2['status'] == 'clicked', "Clicked status update failed"
        
        # Test bounce
        token3 = str(uuid.uuid4())
        message_id3 = db.create_message(
            campaign_id=campaign_id,
            recipient_email="test3@example.com",
            tracking_token=token3
        )
        db.update_message_bounced(message_id3, "User unknown", "permanent")
        message3 = db.get_message(message_id3)
        assert message3['status'] == 'bounced', "Bounced status update failed"
        
        # Test bounce record
        bounce_id = db.add_bounce(
            message_id3,
            bounce_type="permanent",
            bounce_reason="User unknown",
            source="api"
        )
        assert bounce_id > 0, "Bounce record creation failed"
        
        # Test link click tracking
        click_id = db.track_link_click(
            message_id2,
            "https://example.com/offer",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1"
        )
        assert click_id > 0, "Link click tracking failed"
        
        # Test event logging
        event_id = db.add_message_event(
            message_id,
            "test_event",
            json.dumps({"test": True})
        )
        assert event_id > 0, "Event logging failed"
        
        # Test metrics
        metrics = db.get_campaign_metrics(campaign_id)
        assert metrics['total'] == 3, f"Metrics total count incorrect: expected 3, got {metrics['total']}"
        # sent=0 because message_id became 'opened' and message_id2 became 'clicked'
        assert metrics['sent'] == 0, f"Metrics sent count incorrect: expected 0, got {metrics['sent']}"
        assert metrics['opened'] == 1, f"Metrics opened count incorrect: expected 1, got {metrics['opened']}"
        assert metrics['clicked'] == 1, f"Metrics clicked count incorrect: expected 1, got {metrics['clicked']}"
        assert metrics['bounced'] == 1, f"Metrics bounced count incorrect: expected 1, got {metrics['bounced']}"
        
        # Test CSV export
        csv_data = db.export_campaign_to_csv(campaign_id)
        assert len(csv_data) > 0, "CSV export failed"
        assert "test@example.com" in csv_data, "CSV export missing email"
        
        # Test campaign list
        campaigns = db.get_all_campaigns()
        assert len(campaigns) > 0, "Campaign list failed"
        
        # Test message list
        messages = db.get_campaign_messages(campaign_id)
        assert len(messages) == 3, "Message list failed"
        
        # Test deletion
        db.delete_campaign(campaign_id)
        deleted = db.get_campaign(campaign_id)
        assert deleted is None, "Campaign deletion failed"
        
        print("✓ Database tests passed")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_bounce_handler():
    """Test bounce handler."""
    print("Testing Bounce Handler...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        handler = BounceHandler(db)
        
        # Create test data
        campaign_id = db.create_campaign("Bounce Test")
        token = str(uuid.uuid4())
        message_id = db.create_message(
            campaign_id=campaign_id,
            recipient_email="bounce@example.com",
            tracking_token=token
        )
        db.update_message_sent(message_id)
        
        # Test SendGrid bounce handling
        sendgrid_event = {
            "event": "bounce",
            "sg_message_id": token,
            "bounce_type": "permanent",
            "reason": "User unknown"
        }
        
        result = handler.handle_sendgrid_event(sendgrid_event)
        assert result is not None, "SendGrid bounce handling failed"
        
        message = db.get_message(message_id)
        assert message['status'] == 'bounced', "Bounce status not updated"
        
        # Test Gmail notification handling
        gmail_data = {
            "token": token,
            "status": "permanent-failure",
            "reason": "Invalid recipient"
        }
        
        result = handler.handle_gmail_notification(gmail_data)
        assert result is not None, "Gmail bounce handling failed"
        
        # Test SendGrid open event
        open_event = {
            "event": "open",
            "sg_message_id": token
        }
        
        result = handler.handle_sendgrid_event(open_event)
        assert result is not None, "SendGrid open handling failed"
        
        print("✓ Bounce handler tests passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_flask_app():
    """Test Flask app and endpoints."""
    print("Testing Flask App...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        app = create_app(db_path)
        client = app.test_client()
        
        # Test health check
        response = client.get('/health')
        assert response.status_code == 200, "Health check failed"
        
        # Test campaign creation
        response = client.post('/api/campaigns', 
            json={'name': 'Flask Test Campaign'})
        assert response.status_code == 201, "Campaign creation failed"
        campaign_data = response.get_json()
        campaign_id = campaign_data['id']
        
        # Test campaign retrieval
        response = client.get(f'/api/campaigns/{campaign_id}')
        assert response.status_code == 200, "Campaign retrieval failed"
        
        # Test message creation
        token = str(uuid.uuid4())
        response = client.post('/api/messages',
            json={
                'campaign_id': campaign_id,
                'recipient_email': 'flask@example.com',
                'tracking_token': token
            })
        assert response.status_code == 201, "Message creation failed"
        message_data = response.get_json()
        message_id = message_data['id']
        
        # Test tracking pixel
        response = client.get(f'/track/pixel/{token}')
        assert response.status_code == 200, "Tracking pixel failed"
        assert response.content_type == 'image/gif', "Tracking pixel wrong type"
        
        # Test click redirect
        response = client.get(f'/track/redirect/{token}?url=https://example.com')
        assert response.status_code == 200, "Click redirect failed"
        
        # Test bounce reporting
        response = client.post(f'/api/messages/{message_id}/bounce',
            json={
                'bounce_reason': 'Test bounce',
                'bounce_type': 'permanent'
            })
        assert response.status_code == 200, "Bounce reporting failed"
        
        # Test SendGrid webhook
        response = client.post('/webhooks/sendgrid',
            json={
                'event': 'bounce',
                'sg_message_id': token,
                'bounce_type': 'permanent',
                'reason': 'Test bounce'
            })
        assert response.status_code == 200, "SendGrid webhook failed"
        
        # Test campaign list
        response = client.get('/api/campaigns')
        assert response.status_code == 200, "Campaign list failed"
        
        # Test campaign export
        response = client.get(f'/api/campaigns/{campaign_id}/export')
        assert response.status_code == 200, "Campaign export failed"
        
        print("✓ Flask app tests passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_integration():
    """Test complete integration flow."""
    print("Testing Integration Flow...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db = Database(db_path)
        app = create_app(db_path)
        client = app.test_client()
        
        # 1. Create campaign
        response = client.post('/api/campaigns',
            json={'name': 'Integration Test'})
        campaign_id = response.get_json()['id']
        
        # 2. Create messages
        tokens = []
        for i in range(5):
            token = str(uuid.uuid4())
            tokens.append(token)
            response = client.post('/api/messages',
                json={
                    'campaign_id': campaign_id,
                    'recipient_email': f'user{i}@example.com',
                    'tracking_token': token
                })
            message_id = response.get_json()['id']
            
            # Mark as sent
            client.post(f'/api/messages/{message_id}/sent')
        
        # 3. Simulate opens and clicks
        for i, token in enumerate(tokens[:3]):  # 3 opens
            response = client.get(f'/track/pixel/{token}')
            assert response.status_code == 200
        
        for token in tokens[:2]:  # 2 clicks
            response = client.get(f'/track/redirect/{token}?url=https://example.com')
            assert response.status_code == 200
        
        # 4. Simulate a bounce
        bounce_event = {
            "event": "bounce",
            "sg_message_id": tokens[3],
            "bounce_type": "permanent",
            "reason": "Invalid email"
        }
        response = client.post('/webhooks/sendgrid', json=bounce_event)
        assert response.status_code == 200
        
        # 5. Check metrics
        response = client.get(f'/api/campaigns/{campaign_id}')
        metrics = response.get_json()['metrics']
        
        assert metrics['total'] == 5, f"Total count incorrect: {metrics['total']}"
        # Statuses: 0-2 opened (0-1 also clicked), 3 bounced, 4 never sent (queued)
        # So: queued=1, sent=0, opened=1, clicked=2, bounced=1
        # sent_count (for rates) = opened + clicked + sent = 1+2+0 = 3
        # open_rate = 1/3 = 33.33%, click_rate = 2/3 = 66.67%
        assert metrics['opened'] == 1, f"Opened count incorrect: {metrics['opened']}"
        assert metrics['clicked'] == 2, f"Clicked count incorrect: {metrics['clicked']}"
        assert metrics['bounced'] == 1, f"Bounced count incorrect: {metrics['bounced']}"
        assert metrics['open_rate'] == 33.33, f"Open rate incorrect: {metrics['open_rate']}"
        assert metrics['click_rate'] == 66.67, f"Click rate incorrect: {metrics['click_rate']}"
        
        print("✓ Integration flow tests passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("Email Tracking Service - Test Suite")
    print("=" * 50)
    print()
    
    tests = [
        test_database,
        test_bounce_handler,
        test_flask_app,
        test_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} error: {e}")
            failed += 1
    
    print()
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
