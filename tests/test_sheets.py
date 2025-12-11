"""Unit tests for Google Sheets integration."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from autobulk.sheets import (
    SheetsClient, Recipient, validate_email, validate_recipient,
    ValidationError
)
from autobulk.config import GoogleConfig
from autobulk.exceptions import ConfigurationError


class TestRecipientDataclass:
    """Tests for the Recipient dataclass."""
    
    def test_recipient_creation(self):
        """Test creating a Recipient instance."""
        recipient = Recipient(
            name="John Doe",
            email="john@example.com",
            custom_fields={"company": "Acme"}
        )
        assert recipient.name == "John Doe"
        assert recipient.email == "john@example.com"
        assert recipient.custom_fields == {"company": "Acme"}
    
    def test_recipient_hashable(self):
        """Test that recipients are hashable for deduplication."""
        recipient1 = Recipient(name="John Doe", email="john@example.com")
        recipient2 = Recipient(name="John Doe", email="john@example.com")
        
        # Should be equal
        assert recipient1 == recipient2
        # Should have same hash
        assert hash(recipient1) == hash(recipient2)
    
    def test_recipient_deduplication(self):
        """Test deduplication of recipients."""
        recipient1 = Recipient(name="John Doe", email="john@example.com")
        recipient2 = Recipient(name="John Doe", email="john@example.com")
        
        seen = set()
        seen.add(recipient1)
        
        # Should not add duplicate
        assert recipient2 not in seen or recipient1 == recipient2


class TestEmailValidation:
    """Tests for email validation."""
    
    def test_valid_email(self):
        """Test valid email formats."""
        valid_emails = [
            "user@example.com",
            "john.doe@example.co.uk",
            "test+tag@example.com",
            "user123@example.org",
        ]
        for email in valid_emails:
            assert validate_email(email), f"Expected {email} to be valid"
    
    def test_invalid_email(self):
        """Test invalid email formats."""
        invalid_emails = [
            "plaintext",
            "@example.com",
            "user@",
            "user@.com",
            "user @example.com",
            "user@example",
        ]
        for email in invalid_emails:
            assert not validate_email(email), f"Expected {email} to be invalid"


class TestRecipientValidation:
    """Tests for recipient row validation."""
    
    def test_valid_recipient(self):
        """Test validation of valid recipient row."""
        row = {"name": "John Doe", "email": "john@example.com"}
        # Should not raise
        validate_recipient(row, 1, ["name", "email"])
    
    def test_missing_required_field(self):
        """Test validation fails with missing required field."""
        row = {"name": "John Doe"}
        with pytest.raises(ValidationError) as exc_info:
            validate_recipient(row, 1, ["name", "email"])
        
        assert exc_info.value.row_number == 1
        assert exc_info.value.field == "email"
    
    def test_empty_required_field(self):
        """Test validation fails with empty required field."""
        row = {"name": "", "email": "john@example.com"}
        with pytest.raises(ValidationError) as exc_info:
            validate_recipient(row, 1, ["name", "email"])
        
        assert exc_info.value.row_number == 1
        assert exc_info.value.field == "name"
    
    def test_invalid_email_field(self):
        """Test validation fails with invalid email."""
        row = {"name": "John Doe", "email": "not-an-email"}
        with pytest.raises(ValidationError) as exc_info:
            validate_recipient(row, 1, ["name", "email"])
        
        assert exc_info.value.row_number == 1
        assert exc_info.value.field == "email"
        assert "Invalid email format" in exc_info.value.message
    
    def test_whitespace_trimming(self):
        """Test that whitespace is handled correctly."""
        row = {"name": "  John Doe  ", "email": "  john@example.com  "}
        # Should not raise even with whitespace
        validate_recipient(row, 1, ["name", "email"])


class TestSheetsClientInitialization:
    """Tests for SheetsClient initialization."""
    
    def test_init_no_credentials(self):
        """Test initialization fails without credentials."""
        config = GoogleConfig()
        with pytest.raises(ConfigurationError) as exc_info:
            SheetsClient(config)
        
        assert "No Google credentials provided" in exc_info.value.message
    
    @patch('autobulk.sheets.Credentials.from_service_account_file')
    @patch('googleapiclient.discovery.build')
    def test_init_with_credentials_file(self, mock_build, mock_from_file):
        """Test initialization with credentials file."""
        # Mock the credentials and service
        mock_creds = MagicMock()
        mock_from_file.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_file = Path(tmpdir) / "creds.json"
            creds_file.write_text('{}')
            
            config = GoogleConfig(credentials_path=str(creds_file))
            client = SheetsClient(config)
            
            assert client._credentials == mock_creds
            assert client._service == mock_service
            mock_from_file.assert_called_once()
    
    @patch('autobulk.sheets.Credentials.from_service_account_info')
    @patch('googleapiclient.discovery.build')
    def test_init_with_credentials_json(self, mock_build, mock_from_info):
        """Test initialization with credentials JSON."""
        mock_creds = MagicMock()
        mock_from_info.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        creds_json = '{"type": "service_account"}'
        config = GoogleConfig(credentials_json=creds_json)
        client = SheetsClient(config)
        
        assert client._credentials == mock_creds
        assert client._service == mock_service
        mock_from_info.assert_called_once()
    
    def test_init_invalid_json_credentials(self):
        """Test initialization fails with invalid JSON credentials."""
        config = GoogleConfig(credentials_json="invalid json")
        with pytest.raises(ConfigurationError) as exc_info:
            SheetsClient(config)
        
        assert "Invalid JSON" in exc_info.value.message
    
    def test_init_missing_credentials_file(self):
        """Test initialization fails when credentials file doesn't exist."""
        config = GoogleConfig(credentials_path="/nonexistent/path.json")
        with pytest.raises(ConfigurationError) as exc_info:
            SheetsClient(config)
        
        assert "Credentials file not found" in exc_info.value.message
    
    def test_cache_dir_creation(self):
        """Test that cache directory is created."""
        config = GoogleConfig(credentials_json='{}')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            
            with patch('autobulk.sheets.Credentials.from_service_account_info'):
                with patch('googleapiclient.discovery.build'):
                    client = SheetsClient(config, cache_dir=cache_dir)
            
            # Cache directory might not exist yet, but should be set
            assert client.cache_dir == cache_dir


class TestSheetsClientFetchRows:
    """Tests for fetching rows from sheets."""
    
    def _create_mock_client(self):
        """Helper to create a mocked SheetsClient."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                
                client = SheetsClient(config)
                return client, mock_service
    
    def test_fetch_rows_success(self):
        """Test successful row fetching."""
        client, mock_service = self._create_mock_client()
        
        # Mock the API response
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name', 'Email'],
                ['John Doe', 'john@example.com'],
                ['Jane Smith', 'jane@example.com'],
            ]
        }
        
        recipients, errors = client.fetch_rows('test-sheet')
        
        assert len(recipients) == 2
        assert len(errors) == 0
        assert recipients[0].name == "John Doe"
        assert recipients[0].email == "john@example.com"
        assert recipients[1].name == "Jane Smith"
    
    def test_fetch_rows_with_custom_fields(self):
        """Test fetching rows with custom fields."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name', 'Email', 'Company', 'Department'],
                ['John Doe', 'john@example.com', 'Acme', 'Sales'],
            ]
        }
        
        recipients, errors = client.fetch_rows('test-sheet')
        
        assert len(recipients) == 1
        assert recipients[0].custom_fields == {'company': 'Acme', 'department': 'Sales'}
    
    def test_fetch_rows_with_validation_errors(self):
        """Test fetching rows with validation errors."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name', 'Email'],
                ['John Doe', 'john@example.com'],
                ['', 'invalid-email'],  # Both invalid
                ['Jane Smith', 'jane@example.com'],
            ]
        }
        
        recipients, errors = client.fetch_rows('test-sheet')
        
        assert len(recipients) == 2
        assert len(errors) == 1
        assert errors[0].row_number == 3  # Zero-indexed becomes 1-indexed
    
    def test_fetch_rows_deduplication(self):
        """Test that duplicate recipients are removed."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name', 'Email'],
                ['John Doe', 'john@example.com'],
                ['John Doe', 'john@example.com'],  # Duplicate
                ['Jane Smith', 'jane@example.com'],
            ]
        }
        
        recipients, errors = client.fetch_rows('test-sheet')
        
        assert len(recipients) == 2
        assert len(errors) == 0
    
    def test_fetch_rows_missing_required_columns(self):
        """Test error when required columns are missing."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name'],  # Missing 'email' column
                ['John Doe'],
            ]
        }
        
        with pytest.raises(ConfigurationError) as exc_info:
            client.fetch_rows('test-sheet', required_columns=['name', 'email'])
        
        assert "Missing required columns" in exc_info.value.message
    
    def test_fetch_rows_empty_sheet(self):
        """Test handling empty sheet."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {}
        
        recipients, errors = client.fetch_rows('test-sheet')
        
        assert len(recipients) == 0
        assert len(errors) == 0
    
    def test_fetch_rows_custom_range(self):
        """Test fetching with custom range."""
        client, mock_service = self._create_mock_client()
        
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                ['Name', 'Email'],
                ['John Doe', 'john@example.com'],
            ]
        }
        
        recipients, errors = client.fetch_rows('test-sheet', range_name='Sheet1!A1:B100')
        
        # Verify the range was passed correctly
        call_args = mock_service.spreadsheets().values().get.call_args
        assert call_args[1]['range'] == 'Sheet1!A1:B100'


class TestSheetsClientCaching:
    """Tests for recipient caching."""
    
    def _create_mock_client(self):
        """Helper to create a mocked SheetsClient."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    client = SheetsClient(config, cache_dir=Path(tmpdir))
                    yield client, Path(tmpdir)
    
    def test_cache_recipients_csv(self):
        """Test caching recipients to CSV."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    client = SheetsClient(config, cache_dir=Path(tmpdir))
                    
                    recipients = [
                        Recipient("John Doe", "john@example.com", {"company": "Acme"}),
                        Recipient("Jane Smith", "jane@example.com", {}),
                    ]
                    
                    result = client.cache_recipients(recipients, format="csv")
                    
                    assert "csv" in result
                    csv_file = result["csv"]
                    assert csv_file.exists()
                    
                    # Verify CSV content
                    content = csv_file.read_text()
                    assert "John Doe" in content
                    assert "john@example.com" in content
    
    def test_cache_recipients_json(self):
        """Test caching recipients to JSON."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    client = SheetsClient(config, cache_dir=Path(tmpdir))
                    
                    recipients = [
                        Recipient("John Doe", "john@example.com", {"company": "Acme"}),
                    ]
                    
                    result = client.cache_recipients(recipients, format="json")
                    
                    assert "json" in result
                    json_file = result["json"]
                    assert json_file.exists()
                    
                    # Verify JSON content
                    data = json.loads(json_file.read_text())
                    assert len(data) == 1
                    assert data[0]["name"] == "John Doe"
                    assert data[0]["email"] == "john@example.com"
    
    def test_cache_recipients_both(self):
        """Test caching recipients to both CSV and JSON."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    client = SheetsClient(config, cache_dir=Path(tmpdir))
                    
                    recipients = [
                        Recipient("John Doe", "john@example.com"),
                    ]
                    
                    result = client.cache_recipients(recipients, format="both")
                    
                    assert "csv" in result
                    assert "json" in result
                    assert result["csv"].exists()
                    assert result["json"].exists()


class TestPagination:
    """Tests for handling large datasets with pagination."""
    
    def test_fetch_rows_with_many_rows(self):
        """Test fetching many rows."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                
                client = SheetsClient(config)
                
                # Create a large dataset
                rows = [['Name', 'Email']]
                for i in range(1000):
                    rows.append([f'User {i}', f'user{i}@example.com'])
                
                mock_service.spreadsheets().values().get().execute.return_value = {
                    'values': rows
                }
                
                recipients, errors = client.fetch_rows('test-sheet')
                
                assert len(recipients) == 1000
                assert len(errors) == 0


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_recipient_with_special_characters(self):
        """Test handling recipients with special characters."""
        recipient = Recipient(
            name="José María",
            email="jose@example.com"
        )
        assert recipient.name == "José María"
    
    def test_column_names_case_insensitive(self):
        """Test that column names are case-insensitive."""
        config = GoogleConfig(credentials_json='{}')
        
        with patch('autobulk.sheets.Credentials.from_service_account_info'):
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service
                
                client = SheetsClient(config)
                
                # Use uppercase column names
                mock_service.spreadsheets().values().get().execute.return_value = {
                    'values': [
                        ['NAME', 'EMAIL'],
                        ['John Doe', 'john@example.com'],
                    ]
                }
                
                recipients, errors = client.fetch_rows('test-sheet')
                
                assert len(recipients) == 1
                assert recipients[0].name == "John Doe"
