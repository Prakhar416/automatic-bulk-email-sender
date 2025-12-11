"""Automatic bulk email scheduling and worker utilities."""
from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("automatic-bulk-email-sender")
except PackageNotFoundError:  # pragma: no cover - during local development
    __version__ = "0.1.0"
