"""Email tracking service for bulk email sender."""

__version__ = "0.1.0"

from .database import Database
from .app import create_app
from .bounce_handler import BounceHandler

__all__ = ['Database', 'create_app', 'BounceHandler']
