import os
import json
import uuid
from flask import Flask, request, jsonify, send_file
from io import BytesIO
from datetime import datetime
from typing import Optional, Tuple
from .database import Database
from .bounce_handler import BounceHandler


def create_app(db_path: str = "tracking.db") -> Flask:
    """Factory function to create and configure Flask app."""
    app = Flask(__name__)
    app.config['DB_PATH'] = db_path
    db = Database(db_path)
    bounce_handler = BounceHandler(db)
    
    # Inject database into app context
    app.db = db
    app.bounce_handler = bounce_handler
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy"}), 200
    
    @app.route('/api/campaigns', methods=['POST'])
    def create_campaign():
        """Create a new campaign."""
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({"error": "Campaign name is required"}), 400
        
        try:
            campaign_id = app.db.create_campaign(
                name=data['name'],
                template_id=data.get('template_id')
            )
            return jsonify({
                "id": campaign_id,
                "name": data['name'],
                "created_at": datetime.utcnow().isoformat()
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
    def get_campaign(campaign_id):
        """Get campaign details."""
        campaign = app.db.get_campaign(campaign_id)
        
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
        
        metrics = app.db.get_campaign_metrics(campaign_id)
        
        return jsonify({
            **dict(campaign),
            "metrics": metrics
        }), 200
    
    @app.route('/api/campaigns', methods=['GET'])
    def list_campaigns():
        """List all campaigns."""
        campaigns = app.db.get_all_campaigns()
        
        result = []
        for campaign in campaigns:
            metrics = app.db.get_campaign_metrics(campaign['id'])
            result.append({
                **dict(campaign),
                "metrics": metrics
            })
        
        return jsonify(result), 200
    
    @app.route('/api/campaigns/<int:campaign_id>/messages', methods=['GET'])
    def get_campaign_messages(campaign_id):
        """Get messages for a campaign."""
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        campaign = app.db.get_campaign(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
        
        messages = app.db.get_campaign_messages(campaign_id, limit, offset)
        
        return jsonify([dict(msg) for msg in messages]), 200
    
    @app.route('/api/campaigns/<int:campaign_id>/export', methods=['GET'])
    def export_campaign(campaign_id):
        """Export campaign data as CSV."""
        campaign = app.db.get_campaign(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
        
        csv_data = app.db.export_campaign_to_csv(campaign_id)
        
        output = BytesIO()
        output.write(csv_data.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'campaign_{campaign_id}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        ), 200
    
    @app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
    def delete_campaign_route(campaign_id):
        """Delete a campaign."""
        campaign = app.db.get_campaign(campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404
        
        app.db.delete_campaign(campaign_id)
        
        return jsonify({"message": "Campaign deleted successfully"}), 200
    
    @app.route('/api/messages', methods=['POST'])
    def create_message():
        """Create a new message record."""
        data = request.get_json()
        
        if not data or 'campaign_id' not in data or 'recipient_email' not in data:
            return jsonify({"error": "campaign_id and recipient_email are required"}), 400
        
        # Generate tracking token if not provided
        tracking_token = data.get('tracking_token', str(uuid.uuid4()))
        
        try:
            message_id = app.db.create_message(
                campaign_id=data['campaign_id'],
                recipient_email=data['recipient_email'],
                tracking_token=tracking_token,
                template_id=data.get('template_id'),
                status=data.get('status', 'queued')
            )
            
            return jsonify({
                "id": message_id,
                "tracking_token": tracking_token,
                "status": "queued",
                "created_at": datetime.utcnow().isoformat()
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/messages/<int:message_id>', methods=['GET'])
    def get_message(message_id):
        """Get message details."""
        message = app.db.get_message(message_id)
        
        if not message:
            return jsonify({"error": "Message not found"}), 404
        
        return jsonify(dict(message)), 200
    
    @app.route('/api/messages/<int:message_id>/sent', methods=['POST'])
    def mark_sent(message_id):
        """Mark message as sent."""
        message = app.db.get_message(message_id)
        
        if not message:
            return jsonify({"error": "Message not found"}), 404
        
        data = request.get_json() or {}
        app.db.update_message_sent(message_id, data.get('sent_at'))
        app.db.add_message_event(message_id, 'sent', json.dumps(data))
        
        return jsonify({"status": "sent"}), 200
    
    @app.route('/track/pixel/<token>', methods=['GET'])
    def track_pixel(token):
        """Tracking pixel endpoint - marks email as opened."""
        message = app.db.get_message_by_token(token)
        
        if not message:
            # Return a 1x1 pixel anyway for privacy
            pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x54\x01\x00\x3B'
            return pixel, 200, {'Content-Type': 'image/gif', 'Cache-Control': 'no-cache'}
        
        # Mark as opened
        app.db.update_message_opened(message['id'])
        app.db.add_message_event(message['id'], 'opened', json.dumps({
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': _get_client_ip(),
            'referer': request.headers.get('Referer'),
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        # Return 1x1 GIF pixel
        pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x54\x01\x00\x3B'
        return pixel, 200, {'Content-Type': 'image/gif', 'Cache-Control': 'no-cache'}
    
    @app.route('/track/redirect/<token>', methods=['GET'])
    def track_redirect(token):
        """Click tracking redirect endpoint."""
        message = app.db.get_message_by_token(token)
        url = request.args.get('url')
        
        if not url:
            return jsonify({"error": "url parameter is required"}), 400
        
        if not message:
            # Redirect anyway to avoid suspicion
            return jsonify({"error": "Tracking token not found"}), 404
        
        # Mark as clicked
        app.db.update_message_clicked(message['id'])
        
        # Track the click
        app.db.track_link_click(
            message['id'],
            url,
            user_agent=request.headers.get('User-Agent'),
            ip_address=_get_client_ip()
        )
        
        app.db.add_message_event(message['id'], 'clicked', json.dumps({
            'url': url,
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': _get_client_ip(),
            'referer': request.headers.get('Referer'),
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        # Redirect to the actual URL
        return jsonify({
            "redirect": url,
            "tracked": True
        }), 200
    
    @app.route('/webhooks/sendgrid', methods=['POST'])
    def sendgrid_webhook():
        """Handle SendGrid webhook events."""
        try:
            events = request.get_json()
            
            if not isinstance(events, list):
                events = [events]
            
            for event in events:
                app.bounce_handler.handle_sendgrid_event(event)
            
            return jsonify({"processed": len(events)}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/webhooks/gmail', methods=['POST'])
    def gmail_webhook():
        """Handle Gmail delivery status notifications."""
        try:
            data = request.get_json()
            app.bounce_handler.handle_gmail_notification(data)
            return jsonify({"processed": True}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/messages/<int:message_id>/bounce', methods=['POST'])
    def report_bounce(message_id):
        """Manually report a bounce for a message."""
        data = request.get_json()
        
        if not data or 'bounce_reason' not in data:
            return jsonify({"error": "bounce_reason is required"}), 400
        
        message = app.db.get_message(message_id)
        if not message:
            return jsonify({"error": "Message not found"}), 404
        
        app.db.update_message_bounced(
            message_id,
            data['bounce_reason'],
            data.get('bounce_type'),
            data.get('bounced_at')
        )
        
        app.db.add_bounce(
            message_id,
            bounce_type=data.get('bounce_type', 'permanent'),
            bounce_reason=data['bounce_reason'],
            bounce_subtype=data.get('bounce_subtype'),
            diagnostic_code=data.get('diagnostic_code'),
            source='api'
        )
        
        return jsonify({"status": "bounced"}), 200
    
    @app.route('/api/health', methods=['GET'])
    def api_health():
        """API health endpoint."""
        return jsonify({"status": "ok"}), 200
    
    return app


def _get_client_ip() -> str:
    """Get client IP address from request."""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ.get('HTTP_X_FORWARDED_FOR').split(',')[0].strip()
    return request.environ.get('REMOTE_ADDR', 'unknown')
