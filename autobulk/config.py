"""Runtime configuration helpers for the autobulk application."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HOME = Path(os.getenv("AUTOBULK_HOME", Path.home() / ".autobulk"))


def _ensure_home_directory() -> Path:
    DEFAULT_HOME.mkdir(parents=True, exist_ok=True)
    return DEFAULT_HOME


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    database_url: str
    worker_poll_interval: float
    recipient_cache_path: Path

    @classmethod
    def load(cls) -> "Settings":
        home = _ensure_home_directory()
        db_url = os.getenv("AUTOBULK_DB_URL")
        if not db_url:
            db_path = home / "autobulk.db"
            db_url = f"sqlite:///{db_path}"

        poll_interval = float(os.getenv("AUTOBULK_WORKER_POLL", "5"))
        cache_path = Path(os.getenv("AUTOBULK_RECIPIENT_CACHE", home / "recipients.csv"))

        return cls(
            database_url=db_url,
            worker_poll_interval=poll_interval,
            recipient_cache_path=cache_path,
        )


__all__ = ["Settings"]
