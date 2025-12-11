import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, List, Any


class Database:
    def __init__(self, db_path: str = "tracking.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Campaigns table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                template_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Email messages table - tracks each email sent
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                template_id INTEGER,
                recipient_email TEXT NOT NULL,
                tracking_token TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'queued',
                queued_at TIMESTAMP,
                sent_at TIMESTAMP,
                opened_at TIMESTAMP,
                clicked_at TIMESTAMP,
                bounced_at TIMESTAMP,
                bounce_reason TEXT,
                bounce_type TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
            )
            """)

            # Message events table - detailed event log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
            """)

            # Link clicks tracking
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS link_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                click_count INTEGER DEFAULT 1,
                first_clicked_at TIMESTAMP,
                last_clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
            """)

            # Bounce feedback table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bounces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                bounce_type TEXT NOT NULL,
                bounce_subtype TEXT,
                bounce_reason TEXT,
                diagnostic_code TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
            """)

            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_tracking_token ON messages(tracking_token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_campaign_id ON messages(campaign_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient_email ON messages(recipient_email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_events_message_id ON message_events(message_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_link_clicks_message_id ON link_clicks(message_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bounces_message_id ON bounces(message_id)")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get a database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_campaign(self, name: str, template_id: Optional[int] = None) -> int:
        """Create a new campaign."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO campaigns (name, template_id) VALUES (?, ?)",
                (name, template_id)
            )
            conn.commit()
            return cursor.lastrowid

    def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get campaign by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_message(
        self,
        campaign_id: int,
        recipient_email: str,
        tracking_token: str,
        template_id: Optional[int] = None,
        status: str = "queued",
        queued_at: Optional[str] = None
    ) -> int:
        """Create a new message record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if queued_at is None:
                queued_at = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT INTO messages 
                (campaign_id, template_id, recipient_email, tracking_token, status, queued_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (campaign_id, template_id, recipient_email, tracking_token, status, queued_at))
            conn.commit()
            return cursor.lastrowid

    def get_message_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get message by tracking token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE tracking_token = ?", (token,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get message by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_message_sent(self, message_id: int, sent_at: Optional[str] = None) -> bool:
        """Mark message as sent."""
        if sent_at is None:
            sent_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET status = 'sent', sent_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (sent_at, message_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_message_opened(self, message_id: int, opened_at: Optional[str] = None) -> bool:
        """Mark message as opened."""
        if opened_at is None:
            opened_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET status = 'opened', opened_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status != 'bounced'
            """, (opened_at, message_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_message_clicked(self, message_id: int, clicked_at: Optional[str] = None) -> bool:
        """Mark message as clicked."""
        if clicked_at is None:
            clicked_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET status = 'clicked', clicked_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status != 'bounced'
            """, (clicked_at, message_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_message_bounced(
        self,
        message_id: int,
        bounce_reason: str,
        bounce_type: Optional[str] = None,
        bounced_at: Optional[str] = None
    ) -> bool:
        """Mark message as bounced."""
        if bounced_at is None:
            bounced_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET status = 'bounced', bounced_at = ?, bounce_reason = ?, bounce_type = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (bounced_at, bounce_reason, bounce_type, message_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_message_event(self, message_id: int, event_type: str, event_data: Optional[str] = None) -> int:
        """Add an event to message event log."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_events (message_id, event_type, event_data)
                VALUES (?, ?, ?)
            """, (message_id, event_type, event_data))
            conn.commit()
            return cursor.lastrowid

    def track_link_click(
        self,
        message_id: int,
        url: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> int:
        """Track a link click."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if this click already exists
            cursor.execute("""
                SELECT id FROM link_clicks 
                WHERE message_id = ? AND url = ?
            """, (message_id, url))
            
            existing = cursor.fetchone()
            if existing:
                # Update existing click record
                cursor.execute("""
                    UPDATE link_clicks 
                    SET click_count = click_count + 1, last_clicked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (existing[0],))
                conn.commit()
                return existing[0]
            else:
                # Create new click record
                cursor.execute("""
                    INSERT INTO link_clicks 
                    (message_id, url, first_clicked_at, user_agent, ip_address)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
                """, (message_id, url, user_agent, ip_address))
                conn.commit()
                return cursor.lastrowid

    def add_bounce(
        self,
        message_id: int,
        bounce_type: str,
        bounce_reason: str,
        bounce_subtype: Optional[str] = None,
        diagnostic_code: Optional[str] = None,
        source: str = "webhook"
    ) -> int:
        """Add a bounce record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bounces 
                (message_id, bounce_type, bounce_subtype, bounce_reason, diagnostic_code, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, bounce_type, bounce_subtype, bounce_reason, diagnostic_code, source))
            conn.commit()
            return cursor.lastrowid

    def get_campaign_metrics(self, campaign_id: int) -> Dict[str, Any]:
        """Get metrics for a campaign."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) as count FROM messages WHERE campaign_id = ?", (campaign_id,))
            total = cursor.fetchone()['count']
            
            # Messages by status
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM messages 
                WHERE campaign_id = ? 
                GROUP BY status
            """, (campaign_id,))
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Count sent emails (any that were sent, not bounced or still queued)
            cursor.execute("""
                SELECT COUNT(*) as count FROM messages 
                WHERE campaign_id = ? AND status IN ('sent', 'opened', 'clicked')
            """, (campaign_id,))
            sent_count = cursor.fetchone()['count']
            
            # Get bounce reasons
            cursor.execute("""
                SELECT bounce_reason, COUNT(*) as count FROM messages 
                WHERE campaign_id = ? AND status = 'bounced' 
                GROUP BY bounce_reason
            """, (campaign_id,))
            bounce_reasons = {row['bounce_reason']: row['count'] for row in cursor.fetchall()}
            
            # Calculate rates based on sent count (excluding bounces)
            opened_count = status_counts.get("opened", 0)
            clicked_count = status_counts.get("clicked", 0)
            bounced_count = status_counts.get("bounced", 0)
            
            return {
                "total": total,
                "queued": status_counts.get("queued", 0),
                "sent": status_counts.get("sent", 0),
                "opened": opened_count,
                "clicked": clicked_count,
                "bounced": bounced_count,
                "bounce_reasons": bounce_reasons,
                "open_rate": round((opened_count / max(sent_count, 1)) * 100, 2) if sent_count > 0 else 0,
                "click_rate": round((clicked_count / max(sent_count, 1)) * 100, 2) if sent_count > 0 else 0,
                "bounce_rate": round((bounced_count / max(total, 1)) * 100, 2),
            }

    def get_all_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_campaign_messages(self, campaign_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages for a campaign."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages 
                WHERE campaign_id = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (campaign_id, limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def export_campaign_to_csv(self, campaign_id: int) -> str:
        """Export campaign data to CSV format (as string)."""
        import csv
        from io import StringIO
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, recipient_email, status, tracking_token,
                    queued_at, sent_at, opened_at, clicked_at, bounced_at,
                    bounce_reason, bounce_type, error_message
                FROM messages 
                WHERE campaign_id = ? 
                ORDER BY created_at DESC
            """, (campaign_id,))
            
            rows = cursor.fetchall()
            
        output = StringIO()
        if rows:
            fieldnames = [description[0] for description in cursor.description]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        return output.getvalue()

    def delete_campaign(self, campaign_id: int) -> bool:
        """Delete a campaign and all related data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete related data first (foreign keys)
            cursor.execute("SELECT id FROM messages WHERE campaign_id = ?", (campaign_id,))
            message_ids = [row[0] for row in cursor.fetchall()]
            
            for msg_id in message_ids:
                cursor.execute("DELETE FROM message_events WHERE message_id = ?", (msg_id,))
                cursor.execute("DELETE FROM link_clicks WHERE message_id = ?", (msg_id,))
                cursor.execute("DELETE FROM bounces WHERE message_id = ?", (msg_id,))
            
            cursor.execute("DELETE FROM messages WHERE campaign_id = ?", (campaign_id,))
            cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
            
            conn.commit()
            return cursor.rowcount > 0
