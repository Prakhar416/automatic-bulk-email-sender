"""CLI commands for recipient management."""

import sys
import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .config import load_settings
from .logging import setup_logging, get_logger
from .sheets import SheetsClient, ValidationError
from .exceptions import ConfigurationError

console = Console()
logger = get_logger(__name__)


@click.group()
def recipients():
    """Manage recipients from various sources."""
    pass


@recipients.command()
@click.option(
    "--spreadsheet-id",
    "-s",
    required=False,
    help="Google Sheet ID to sync from"
)
@click.option(
    "--range",
    "-r",
    default="Sheet1",
    help="Range to read from (e.g., 'Sheet1' or 'Sheet1!A1:C100')"
)
@click.option(
    "--preview",
    "-p",
    type=int,
    default=5,
    help="Number of rows to preview"
)
@click.option(
    "--cache/--no-cache",
    default=True,
    help="Whether to cache results"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
def sync(spreadsheet_id: Optional[str], range: str, preview: int, cache: bool, debug: bool):
    """Sync recipients from Google Sheets."""
    settings = _setup_logging(debug)
    
    try:
        # Get spreadsheet ID from config if not provided
        if not spreadsheet_id and settings:
            spreadsheet_id = settings.sheets.spreadsheet_id
        
        if not spreadsheet_id:
            console.print(
                "[red]Error: No spreadsheet ID provided[/red]\n"
                "Provide via --spreadsheet-id or set AUTOBULK_SHEETS__SPREADSHEET_ID"
            )
            sys.exit(1)
        
        console.print(f"[blue]Syncing recipients from spreadsheet: {spreadsheet_id}[/blue]")
        
        # Initialize Sheets client
        try:
            if not settings:
                console.print("[red]Error: Could not load configuration[/red]")
                sys.exit(1)
            
            sheets_client = SheetsClient(settings.google)
        except ConfigurationError as e:
            console.print(f"[red]Configuration error: {e.message}[/red]")
            logger.error(f"Configuration error: {e.message}", extra={"context": e.context})
            sys.exit(1)
        
        # Fetch recipients
        try:
            recipients_list, errors = sheets_client.fetch_rows(
                spreadsheet_id=spreadsheet_id,
                range_name=range,
                required_columns=settings.sheets.required_columns
            )
        except ConfigurationError as e:
            console.print(f"[red]Error fetching recipients: {e.message}[/red]")
            logger.error(f"Error fetching recipients: {e.message}", extra={"context": e.context})
            sys.exit(1)
        
        # Display validation errors
        if errors:
            console.print(f"\n[yellow]⚠️  {len(errors)} validation error(s) found:[/yellow]")
            error_table = Table(title="Validation Errors", show_header=True)
            error_table.add_column("Row", style="cyan")
            error_table.add_column("Field", style="magenta")
            error_table.add_column("Error", style="red")
            
            for error in errors[:10]:  # Show first 10 errors
                error_table.add_row(
                    str(error.row_number),
                    error.field,
                    error.message
                )
            
            if len(errors) > 10:
                error_table.add_row(
                    "...",
                    "...",
                    f"... and {len(errors) - 10} more errors"
                )
            
            console.print(error_table)
        
        # Display recipients summary
        console.print(f"\n[green]✓ Fetched {len(recipients_list)} unique recipients[/green]")
        
        if recipients_list:
            # Preview recipients
            preview_count = min(preview, len(recipients_list))
            console.print(f"\n[blue]Preview (first {preview_count} rows):[/blue]")
            
            preview_table = Table(show_header=True, title="Recipients Preview")
            preview_table.add_column("Name", style="cyan")
            preview_table.add_column("Email", style="magenta")
            preview_table.add_column("Custom Fields", style="yellow")
            
            for recipient in recipients_list[:preview_count]:
                custom_fields_str = ", ".join(
                    f"{k}={v}" for k, v in recipient.custom_fields.items()
                ) if recipient.custom_fields else "-"
                
                preview_table.add_row(
                    recipient.name,
                    recipient.email,
                    custom_fields_str
                )
            
            console.print(preview_table)
        
        # Cache recipients if requested
        if cache:
            try:
                cache_dir = None
                if settings.sheets.cache_dir:
                    cache_dir = Path(settings.sheets.cache_dir)
                
                cached_files = sheets_client.cache_recipients(
                    recipients_list,
                    format=settings.sheets.cache_format
                )
                
                console.print(f"\n[green]✓ Recipients cached:[/green]")
                for format_type, file_path in cached_files.items():
                    console.print(f"  - {format_type.upper()}: {file_path}")
                
            except ConfigurationError as e:
                console.print(f"\n[yellow]⚠️  Failed to cache recipients: {e.message}[/yellow]")
                logger.warning(f"Failed to cache recipients: {e.message}")
        
        # Summary
        console.print(
            Panel(
                f"[green]Sync complete![/green]\n"
                f"Recipients: {len(recipients_list)}\n"
                f"Validation errors: {len(errors)}\n"
                f"Spreadsheet: {spreadsheet_id}",
                title="Sync Summary"
            )
        )
        
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception(f"Unexpected error during sync: {e}")
        sys.exit(1)


def _setup_logging(debug: bool = False):
    """Load application settings and setup logging."""
    try:
        settings = load_settings()
        
        if debug:
            if hasattr(settings, 'debug'):
                settings.debug = True
            if hasattr(settings, 'logging'):
                settings.logging.level = "DEBUG"
        
        setup_logging(settings=settings)
        
        return settings
    except Exception:
        import logging
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        return None
