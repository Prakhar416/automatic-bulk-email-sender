"""Recipient resolution helpers used by scheduled jobs."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

from .models import Job, RecipientSource

logger = logging.getLogger(__name__)

DEFAULT_RECIPIENTS = [
    {"email": "demo+marketing@example.com", "department": "marketing"},
    {"email": "demo+sales@example.com", "department": "sales"},
    {"email": "demo+eng@example.com", "department": "engineering"},
]


class RecipientResolver:
    """Loads recipients from a cache file or the job definition itself."""

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path

    def resolve(self, job: Job) -> list[str]:
        if job.recipient_source == RecipientSource.STATIC_LIST:
            recipients = list(job.recipients or [])
            if not recipients:
                raise ValueError("Static list job does not define any recipients")
            return recipients
        return self._resolve_from_filter(job.recipient_filter or {})

    def _resolve_from_filter(self, recipient_filter: dict[str, Any]) -> list[str]:
        records = self._load_cache()
        if not recipient_filter:
            logger.warning("Recipient filter is empty; returning every cached recipient")
            return [record["email"] for record in records if record.get("email")]

        filtered: list[str] = []
        for record in records:
            if all(str(record.get(field)) == str(value) for field, value in recipient_filter.items()):
                email = record.get("email")
                if email:
                    filtered.append(email)

        if not filtered:
            raise ValueError("No cached recipients matched the provided filter")
        return filtered

    def _load_cache(self) -> list[dict[str, Any]]:
        if not self.cache_path.exists():
            logger.info("Recipient cache %s not found; using default sample recipients", self.cache_path)
            return DEFAULT_RECIPIENTS

        if self.cache_path.suffix.lower() == ".csv":
            return self._load_csv()
        if self.cache_path.suffix.lower() == ".json":
            return self._load_json()
        raise ValueError(f"Unsupported recipient cache format: {self.cache_path.suffix}")

    def _load_csv(self) -> list[dict[str, Any]]:
        with self.cache_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return [row for row in reader]

    def _load_json(self) -> list[dict[str, Any]]:
        with self.cache_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
            raise ValueError("JSON recipient cache must be a list of objects")


__all__ = ["RecipientResolver"]
