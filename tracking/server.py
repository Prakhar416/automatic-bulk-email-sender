#!/usr/bin/env python
"""
Email tracking server - serves as the tracking pixel/redirect endpoint.
"""

import os
from dotenv import load_dotenv
from .app import create_app
from .dashboard import register_dashboard_routes

# Load environment variables
load_dotenv()


def create_tracking_app():
    """Create and configure the tracking application."""
    db_path = os.getenv('TRACKING_DB_PATH', 'tracking.db')
    app = create_app(db_path=db_path)
    
    # Register dashboard routes
    register_dashboard_routes(app)
    
    return app


if __name__ == '__main__':
    app = create_tracking_app()
    
    host = os.getenv('TRACKING_HOST', '0.0.0.0')
    port = int(os.getenv('TRACKING_PORT', 5000))
    debug = os.getenv('TRACKING_DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    print(f"Starting Email Tracking Server on {host}:{port}")
    print(f"Dashboard: http://{host}:{port}/dashboard")
    print(f"Health Check: http://{host}:{port}/health")
    
    app.run(host=host, port=port, debug=debug)
