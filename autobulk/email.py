"""Simplified email sending utilities used by the worker."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    template: str
    total_recipients: int


class EmailTransport:
    """Base transport interface."""

    def send(self, recipient: str, template: str, context: dict | None = None) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleEmailTransport(EmailTransport):
    """Transport that logs emails instead of sending them."""

    def send(self, recipient: str, template: str, context: dict | None = None) -> None:
        logger.info("Sending template '%s' to %s with context=%s", template, recipient, context or {})


class EmailSender:
    """Simple facade responsible for dispatching emails via a transport."""

    def __init__(self, transport: EmailTransport | None = None) -> None:
        self.transport = transport or ConsoleEmailTransport()

    def send_bulk(self, template: str, recipients: Iterable[str], context: dict | None = None) -> EmailSendResult:
        sent = 0
        for recipient in recipients:
            self.transport.send(recipient=recipient, template=template, context=context)
            sent += 1
        logger.info("Template '%s' dispatched to %s recipients", template, sent)
        return EmailSendResult(template=template, total_recipients=sent)


__all__ = ["EmailSender", "EmailSendResult", "ConsoleEmailTransport"]
