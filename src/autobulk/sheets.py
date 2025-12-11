"""Google Sheets integration for autobulk."""

import csv
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.auth.credentials import Credentials as BaseCredentials
from googleapiclient import discovery

from .config import GoogleConfig
from .exceptions import AuthenticationError, ConfigurationError


logger = logging.getLogger(__name__)


@dataclass
class Recipient:
    """Typed recipient data from Google Sheets."""
    name: str
    email: str
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Make recipients hashable for deduplication."""
        return hash((self.name, self.email))

    def __eq__(self, other: object) -> bool:
        """Check equality for deduplication."""
        if not isinstance(other, Recipient):
            return NotImplemented
        return self.name == other.name and self.email == other.email


class ValidationError(Exception):
    """Exception raised during validation."""
    def __init__(self, row_number: int, field: str, message: str):
        self.row_number = row_number
        self.field = field
        self.message = message
        super().__init__(f"Row {row_number}, {field}: {message}")


def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_recipient(row: Dict[str, Any], row_number: int, required_fields: List[str]) -> None:
    """
    Validate a recipient row.
    
    Args:
        row: Dictionary of row data
        row_number: Row number for error reporting
        required_fields: List of required field names
        
    Raises:
        ValidationError: If validation fails
    """
    # Check required fields
    for field in required_fields:
        if field not in row or not row[field] or (isinstance(row[field], str) and row[field].strip() == ""):
            raise ValidationError(row_number, field, f"Required field missing or empty")
    
    # Validate email
    email = str(row.get("email", "")).strip()
    if not email:
        raise ValidationError(row_number, "email", "Email is required")
    if not validate_email(email):
        raise ValidationError(row_number, "email", f"Invalid email format: {email}")
    
    # Validate name
    name = str(row.get("name", "")).strip()
    if not name:
        raise ValidationError(row_number, "name", "Name is required")


class SheetsClient:
    """Client for reading data from Google Sheets."""

    def __init__(self, config: GoogleConfig, cache_dir: Optional[Path] = None):
        """
        Initialize Google Sheets client.
        
        Args:
            config: Google configuration containing credentials
            cache_dir: Directory for caching CSV/JSON exports
            
        Raises:
            ConfigurationError: If credentials are not provided
        """
        self.config = config
        self.cache_dir = cache_dir or Path.home() / ".autobulk" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._service = None
        self._credentials = None
        self._initialize_credentials()

    def _initialize_credentials(self) -> None:
        """
        Initialize Google API credentials.
        
        Raises:
            ConfigurationError: If credentials cannot be loaded
        """
        try:
            if self.config.credentials_path:
                # Load from file
                creds_path = Path(self.config.credentials_path)
                if not creds_path.exists():
                    raise ConfigurationError(
                        f"Credentials file not found: {self.config.credentials_path}",
                        context={"credentials_path": self.config.credentials_path}
                    )
                
                self._credentials = Credentials.from_service_account_file(
                    str(creds_path),
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                logger.info(f"Loaded credentials from file: {self.config.credentials_path}")
                
            elif self.config.credentials_json:
                # Load from JSON string
                import json as json_module
                creds_dict = json_module.loads(self.config.credentials_json)
                self._credentials = Credentials.from_service_account_info(
                    creds_dict,
                    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
                )
                logger.info("Loaded credentials from JSON string")
                
            else:
                raise ConfigurationError(
                    "No Google credentials provided. Set AUTOBULK_GOOGLE__CREDENTIALS_PATH or AUTOBULK_GOOGLE__CREDENTIALS_JSON",
                    context={"config_keys": ["credentials_path", "credentials_json"]}
                )
            
            # Build the Sheets API service
            self._service = discovery.build(
                'sheets', 'v4', credentials=self._credentials, cache_discovery=False
            )
            logger.info("Google Sheets API service initialized")
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in credentials: {e}",
                cause=e,
                context={"error": str(e)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize Google credentials: {e}",
                cause=e,
                context={"error": str(e)}
            )

    def fetch_rows(
        self,
        spreadsheet_id: str,
        range_name: str = "Sheet1",
        required_columns: Optional[List[str]] = None
    ) -> tuple[List[Recipient], List[ValidationError]]:
        """
        Fetch and process rows from a Google Sheet.
        
        Args:
            spreadsheet_id: The Google Sheet ID
            range_name: The range to fetch (e.g., "Sheet1" or "Sheet1!A1:C100")
            required_columns: List of required column names
            
        Returns:
            Tuple of (list of recipients, list of validation errors)
        """
        if required_columns is None:
            required_columns = ["name", "email"]
        
        try:
            # Fetch data
            result = self._service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning(f"No data found in range: {range_name}")
                return [], []
            
            # First row is headers
            headers = [h.strip().lower() for h in values[0]]
            
            # Check required columns
            missing_columns = set(required_columns) - set(headers)
            if missing_columns:
                raise ConfigurationError(
                    f"Missing required columns: {', '.join(missing_columns)}",
                    context={"missing": list(missing_columns), "headers": headers}
                )
            
            # Process rows
            recipients = []
            errors = []
            seen = set()  # For deduplication
            
            for row_num, row_values in enumerate(values[1:], start=2):
                try:
                    # Pad row with empty strings if necessary
                    row_values = row_values + [''] * (len(headers) - len(row_values))
                    
                    # Create row dictionary
                    row_dict = {
                        headers[i]: row_values[i] if i < len(row_values) else ""
                        for i in range(len(headers))
                    }
                    
                    # Validate row
                    validate_recipient(row_dict, row_num, required_columns)
                    
                    # Extract standard fields
                    name = str(row_dict.get("name", "")).strip()
                    email = str(row_dict.get("email", "")).strip()
                    
                    # Extract custom fields
                    custom_fields = {
                        k: v for k, v in row_dict.items()
                        if k not in ("name", "email") and v
                    }
                    
                    # Deduplicate
                    recipient = Recipient(name=name, email=email, custom_fields=custom_fields)
                    if recipient not in seen:
                        recipients.append(recipient)
                        seen.add(recipient)
                    else:
                        logger.debug(f"Duplicate recipient skipped: {email}")
                
                except ValidationError as e:
                    errors.append(e)
                    logger.warning(f"Validation error: {e}")
            
            logger.info(f"Fetched {len(recipients)} recipients with {len(errors)} validation errors")
            return recipients, errors
            
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to fetch rows from sheet: {e}",
                cause=e,
                context={
                    "spreadsheet_id": spreadsheet_id,
                    "range": range_name,
                    "error": str(e)
                }
            )

    def cache_recipients(
        self,
        recipients: List[Recipient],
        format: str = "both"
    ) -> Dict[str, Path]:
        """
        Cache recipients to local CSV/JSON files.
        
        Args:
            recipients: List of recipients to cache
            format: "csv", "json", or "both"
            
        Returns:
            Dictionary mapping format to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = {}
        
        try:
            if format in ("csv", "both"):
                csv_path = self.cache_dir / f"recipients_{timestamp}.csv"
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    if recipients:
                        writer = csv.DictWriter(
                            f,
                            fieldnames=["name", "email", "custom_fields"]
                        )
                        writer.writeheader()
                        for recipient in recipients:
                            writer.writerow({
                                "name": recipient.name,
                                "email": recipient.email,
                                "custom_fields": json.dumps(recipient.custom_fields)
                            })
                result["csv"] = csv_path
                logger.info(f"Cached recipients to CSV: {csv_path}")
            
            if format in ("json", "both"):
                json_path = self.cache_dir / f"recipients_{timestamp}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        [asdict(r) for r in recipients],
                        f,
                        indent=2,
                        ensure_ascii=False
                    )
                result["json"] = json_path
                logger.info(f"Cached recipients to JSON: {json_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cache recipients: {e}")
            raise ConfigurationError(
                f"Failed to cache recipients: {e}",
                cause=e,
                context={"cache_dir": str(self.cache_dir)}
            )
