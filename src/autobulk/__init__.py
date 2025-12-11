"""Automatic bulk email sender package."""

__version__ = "0.1.0"

from .config import Settings, load_settings
from .logging import setup_logging, get_logger

__all__ = ["Settings", "load_settings", "setup_logging", "get_logger"]