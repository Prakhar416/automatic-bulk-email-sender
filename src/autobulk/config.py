"""Configuration management for autobulk."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
import yaml
import json
from dotenv import load_dotenv


class GoogleConfig(BaseSettings):
    """Google API configuration."""
    
    credentials_path: Optional[str] = Field(None, description="Path to Google service account JSON file")
    credentials_json: Optional[str] = Field(None, description="Google credentials as JSON string")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None


class SheetsConfig(BaseSettings):
    """Google Sheets configuration."""
    
    spreadsheet_id: Optional[str] = Field(None, description="Google Sheet ID to read from")
    range: str = Field("Sheet1", description="Range to read from (e.g., 'Sheet1' or 'Sheet1!A1:C100')")
    required_columns: list = Field(default_factory=lambda: ["name", "email"], description="Required column names")
    cache_format: str = Field("both", description="Cache format: csv, json, or both")
    cache_dir: Optional[str] = Field(None, description="Directory for caching recipients")


class GmailConfig(BaseSettings):
    """Gmail API configuration."""
    
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class SendGridConfig(BaseSettings):
    """SendGrid configuration."""
    
    api_key: Optional[str] = Field(None, description="SendGrid API key")
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class SchedulerConfig(BaseSettings):
    """Scheduling configuration."""
    
    timezone: str = Field("UTC", description="Default timezone for scheduling")
    max_concurrent: int = Field(10, description="Maximum concurrent email operations")
    retry_attempts: int = Field(3, description="Number of retry attempts for failed operations")
    retry_delay: int = Field(60, description="Delay between retry attempts in seconds")


class TemplateConfig(BaseSettings):
    """Template configuration."""
    
    templates_dir: str = Field("templates", description="Directory containing email templates")
    default_template: Optional[str] = Field(None, description="Default template name")
    cache_templates: bool = Field(True, description="Whether to cache parsed templates")


class TrackingConfig(BaseSettings):
    """Email tracking configuration."""
    
    base_url: Optional[str] = Field(None, description="Base URL for tracking links")
    enabled: bool = Field(True, description="Enable email tracking")
    open_tracking: bool = Field(True, description="Enable open tracking")
    click_tracking: bool = Field(True, description="Enable click tracking")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    url: str = Field("sqlite:///autobulk.db", description="SQLAlchemy database URL")
    echo: bool = Field(False, description="Enable SQL query logging")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file_path: Optional[str] = Field(None, description="Path to log file")
    max_file_size: int = Field(10 * 1024 * 1024, description="Maximum log file size in bytes")
    backup_count: int = Field(5, description="Number of backup log files to keep")
    console_output: bool = Field(True, description="Enable console logging")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application settings
    app_name: str = Field("autobulk", description="Application name")
    debug: bool = Field(False, description="Enable debug mode")
    
    # Component configurations
    google: GoogleConfig = Field(default_factory=GoogleConfig)
    sheets: SheetsConfig = Field(default_factory=SheetsConfig)
    gmail: GmailConfig = Field(default_factory=GmailConfig)
    sendgrid: SendGridConfig = Field(default_factory=SendGridConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    model_config = ConfigDict(
        env_prefix="AUTOBULK_",
        case_sensitive=False
    )


def _load_env_file(env_file: Path) -> Dict[str, Any]:
    """Load environment variables from a .env file."""
    load_dotenv(env_file)
    # Only return AUTOBULK_ prefixed variables
    return {k: v for k, v in os.environ.items() if k.startswith('AUTOBULK_')}


def _load_config_file(config_file: Path) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    if not config_file.exists():
        return {}
    
    with open(config_file, 'r') as f:
        if config_file.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(f) or {}
        elif config_file.suffix.lower() == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_file.suffix}")


def _merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple configuration dictionaries."""
    result = {}
    for config in configs:
        if config:
            for key, value in config.items():
                if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                    result[key] = _merge_configs(result[key], value)
                else:
                    result[key] = value
    return result


@lru_cache()
def load_settings(
    config_dir: Optional[Path] = None,
    env_file: Optional[str] = None,
    config_file: Optional[str] = None
) -> Settings:
    """
    Load application settings from multiple sources.
    
    Sources are loaded in order of precedence (later sources override earlier):
    1. Default values
    2. Environment file (.env)
    3. Configuration file (YAML/JSON)
    4. Environment variables
    
    Args:
        config_dir: Directory containing config files (default: current directory)
        env_file: Path to environment file (default: .env in config_dir)
        config_file: Path to configuration file (default: config.yaml in config_dir)
    
    Returns:
        Loaded settings instance
    """
    if config_dir is None:
        config_dir = Path.cwd()
    
    # Default paths
    if env_file is None:
        env_file = config_dir / ".env"
    else:
        env_file = Path(env_file)
    
    if config_file is None:
        config_file = config_dir / "config.yaml"
    else:
        config_file = Path(config_file)
    
    # Load configurations
    env_config = _load_env_file(env_file) if env_file.exists() else {}
    file_config = _load_config_file(config_file) if config_file.exists() else {}
    
    # Environment variables (already loaded by dotenv)
    env_vars = dict(os.environ)
    
    # Merge configurations
    merged_config = _merge_configs(file_config, env_config, env_vars)
    
    try:
        return Settings(**merged_config)
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")