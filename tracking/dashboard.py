from flask import render_template_string, jsonify
from .database import Database


def register_dashboard_routes(app):
    """Register dashboard routes to the Flask app."""
    
    @app.route('/dashboard')
    def dashboard():
        """Main dashboard page."""
        campaigns = app.db.get_all_campaigns()
        
        summary_stats = {
            'total_campaigns': len(campaigns),
            'total_messages': 0,
            'total_sent': 0,
            'total_opened': 0,
            'total_clicked': 0,
            'total_bounced': 0,
        }
        
        campaign_data = []
        
        for campaign in campaigns:
            metrics = app.db.get_campaign_metrics(campaign['id'])
            summary_stats['total_messages'] += metrics['total']
            summary_stats['total_sent'] += metrics['sent']
            summary_stats['total_opened'] += metrics['opened']
            summary_stats['total_clicked'] += metrics['clicked']
            summary_stats['total_bounced'] += metrics['bounced']
            
            campaign_data.append({
                'id': campaign['id'],
                'name': campaign['name'],
                'metrics': metrics
            })
        
        # Calculate aggregate rates
        if summary_stats['total_sent'] > 0:
            summary_stats['open_rate'] = round(
                (summary_stats['total_opened'] / summary_stats['total_sent']) * 100, 2
            )
            summary_stats['click_rate'] = round(
                (summary_stats['total_clicked'] / summary_stats['total_sent']) * 100, 2
            )
        else:
            summary_stats['open_rate'] = 0
            summary_stats['click_rate'] = 0
        
        if summary_stats['total_messages'] > 0:
            summary_stats['bounce_rate'] = round(
                (summary_stats['total_bounced'] / summary_stats['total_messages']) * 100, 2
            )
        else:
            summary_stats['bounce_rate'] = 0
        
        html = _get_dashboard_html(summary_stats, campaign_data)
        return render_template_string(html)
    
    @app.route('/api/dashboard/summary')
    def dashboard_summary():
        """API endpoint for dashboard summary."""
        campaigns = app.db.get_all_campaigns()
        
        summary_stats = {
            'total_campaigns': len(campaigns),
            'total_messages': 0,
            'total_sent': 0,
            'total_opened': 0,
            'total_clicked': 0,
            'total_bounced': 0,
        }
        
        for campaign in campaigns:
            metrics = app.db.get_campaign_metrics(campaign['id'])
            summary_stats['total_messages'] += metrics['total']
            summary_stats['total_sent'] += metrics['sent']
            summary_stats['total_opened'] += metrics['opened']
            summary_stats['total_clicked'] += metrics['clicked']
            summary_stats['total_bounced'] += metrics['bounced']
        
        if summary_stats['total_sent'] > 0:
            summary_stats['open_rate'] = round(
                (summary_stats['total_opened'] / summary_stats['total_sent']) * 100, 2
            )
            summary_stats['click_rate'] = round(
                (summary_stats['total_clicked'] / summary_stats['total_sent']) * 100, 2
            )
        else:
            summary_stats['open_rate'] = 0
            summary_stats['click_rate'] = 0
        
        if summary_stats['total_messages'] > 0:
            summary_stats['bounce_rate'] = round(
                (summary_stats['total_bounced'] / summary_stats['total_messages']) * 100, 2
            )
        else:
            summary_stats['bounce_rate'] = 0
        
        return jsonify(summary_stats)


def _get_dashboard_html(summary_stats, campaign_data):
    """Get HTML for dashboard."""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Email Tracking Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        header h1 {
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 0 20px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .summary-card h3 {
            color: #999;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        
        .summary-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }
        
        .summary-card .unit {
            font-size: 14px;
            color: #999;
            margin-top: 5px;
        }
        
        .campaigns-section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            padding: 20px;
        }
        
        .campaigns-section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            background: #f9f9f9;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #ddd;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        
        tr:hover {
            background: #f9f9f9;
        }
        
        .metric-value {
            font-weight: 600;
            color: #667eea;
        }
        
        .status-sent {
            color: #4CAF50;
        }
        
        .status-opened {
            color: #2196F3;
        }
        
        .status-clicked {
            color: #FF9800;
        }
        
        .status-bounced {
            color: #f44336;
        }
        
        .campaign-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        
        .campaign-link:hover {
            text-decoration: underline;
        }
        
        footer {
            text-align: center;
            color: #999;
            padding: 20px;
            font-size: 12px;
            border-top: 1px solid #eee;
            margin-top: 40px;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .empty-state p {
            font-size: 18px;
            margin-bottom: 10px;
        }
        
        .no-data {
            color: #ccc;
        }
    </style>
</head>
<body>
    <header>
        <h1>📧 Email Tracking Dashboard</h1>
        <p>Real-time email delivery and engagement metrics</p>
    </header>
    
    <div class="container">
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Campaigns</h3>
                <div class="value">{{ summary_stats.total_campaigns }}</div>
            </div>
            <div class="summary-card">
                <h3>Total Emails</h3>
                <div class="value">{{ summary_stats.total_messages }}</div>
            </div>
            <div class="summary-card">
                <h3>Sent</h3>
                <div class="value">{{ summary_stats.total_sent }}</div>
            </div>
            <div class="summary-card">
                <h3>Opened</h3>
                <div class="value">{{ summary_stats.total_opened }}</div>
                <div class="unit">{{ summary_stats.open_rate }}% rate</div>
            </div>
            <div class="summary-card">
                <h3>Clicked</h3>
                <div class="value">{{ summary_stats.total_clicked }}</div>
                <div class="unit">{{ summary_stats.click_rate }}% rate</div>
            </div>
            <div class="summary-card">
                <h3>Bounced</h3>
                <div class="value">{{ summary_stats.total_bounced }}</div>
                <div class="unit">{{ summary_stats.bounce_rate }}% rate</div>
            </div>
        </div>
        
        {% if campaign_data %}
        <div class="campaigns-section">
            <h2>Campaigns</h2>
            <table>
                <thead>
                    <tr>
                        <th>Campaign Name</th>
                        <th>Total</th>
                        <th class="status-sent">Sent</th>
                        <th class="status-opened">Opened</th>
                        <th class="status-clicked">Clicked</th>
                        <th class="status-bounced">Bounced</th>
                        <th>Open Rate</th>
                        <th>Click Rate</th>
                        <th>Bounce Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {% for campaign in campaign_data %}
                    <tr>
                        <td><a href="/api/campaigns/{{ campaign.id }}" class="campaign-link">{{ campaign.name }}</a></td>
                        <td class="metric-value">{{ campaign.metrics.total }}</td>
                        <td class="metric-value status-sent">{{ campaign.metrics.sent }}</td>
                        <td class="metric-value status-opened">{{ campaign.metrics.opened }}</td>
                        <td class="metric-value status-clicked">{{ campaign.metrics.clicked }}</td>
                        <td class="metric-value status-bounced">{{ campaign.metrics.bounced }}</td>
                        <td class="metric-value">{{ campaign.metrics.open_rate }}%</td>
                        <td class="metric-value">{{ campaign.metrics.click_rate }}%</td>
                        <td class="metric-value">{{ campaign.metrics.bounce_rate }}%</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="empty-state">
            <p>No campaigns yet</p>
            <p class="no-data">Create a campaign to start tracking emails</p>
        </div>
        {% endif %}
    </div>
    
    <footer>
        <p>Email Tracking Service • Built with ❤️ for email marketers</p>
    </footer>
    
    <script>
        // Auto-refresh dashboard every 30 seconds
        setTimeout(function() {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
'''
