"""Data models for email sender."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum


class SendStatus(str, Enum):
    """Status of an email send operation."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BOUNCED = "bounced"


@dataclass
class EmailMessage:
    """Represents an email message."""

    recipient: str
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.html_body and not self.text_body:
            raise ValueError("Either html_body or text_body must be provided")


@dataclass
class TemplateMetadata:
    """Metadata about a template."""

    name: str
    subject: str
    required_variables: List[str]
    optional_variables: List[str] = field(default_factory=list)
    has_html: bool = True
    has_text: bool = True
    description: Optional[str] = None


@dataclass
class SendResult:
    """Result of sending an email."""

    recipient: str
    status: SendStatus
    message_id: Optional[str] = None
    error_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recipient": self.recipient,
            "status": self.status.value,
            "message_id": self.message_id,
            "error_reason": self.error_reason,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }
