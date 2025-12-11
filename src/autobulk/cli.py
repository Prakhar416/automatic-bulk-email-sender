"""CLI entrypoint for autobulk."""

import click
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import load_settings, Settings
from .logging import setup_logging
from .recipients_cli import recipients


console = Console()


@click.group()
def main():
    """Automatic bulk email sender with Gmail/SendGrid integration."""
    pass


main.add_command(recipients)


@main.command()
@click.option("--template", "-t", required=True, help="Email template to use")
@click.option("--recipients", "-r", required=True, help="File containing recipient emails")
@click.option("--dry-run", is_flag=True, help="Preview emails without sending")
@click.option("--provider", default="gmail", help="Email provider to use")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def send(template, recipients, dry_run, provider, debug):
    """Send bulk emails using the specified template."""
    _setup_logging(debug)
    
    if dry_run:
        console.print("[yellow]Running in dry-run mode - no emails will be sent[/yellow]")
    
    console.print(f"[green]Starting bulk email send with template: {template}[/green]")
    console.print(f"[blue]Provider: {provider}[/blue]")
    console.print(f"[blue]Recipients file: {recipients}[/blue]")
    
    console.print("[yellow]⚠️  Email sending functionality not implemented yet[/yellow]")


@main.command()
@click.option("--template", "-t", required=True, help="Email template to use")
@click.option("--recipients", "-r", required=True, help="File containing recipient emails")
@click.option("--provider", default="gmail", help="Email provider to use")
@click.option("--cron", help="Cron expression for scheduling")
@click.option("--at", help="Specific time to run (ISO format)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def schedule(template, recipients, provider, cron, at, debug):
    """Schedule bulk email campaigns."""
    _setup_logging(debug)
    
    console.print(f"[green]Scheduling bulk email campaign[/green]")
    console.print(f"[blue]Template: {template}[/blue]")
    console.print(f"[blue]Provider: {provider}[/blue]")
    console.print(f"[blue]Recipients: {recipients}[/blue]")
    
    if cron:
        console.print(f"[blue]Schedule: {cron} (cron)[/blue]")
    elif at:
        console.print(f"[blue]Schedule: {at} (one-time)[/blue]")
    else:
        console.print("[red]Error: Must specify either --cron or --at[/red]")
        return
    
    console.print("[yellow]⚠️  Email scheduling functionality not implemented yet[/yellow]")


@main.command()
def templates():
    """Manage email templates."""
    console.print("[yellow]⚠️  Template management functionality not implemented yet[/yellow]")


@main.command()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def status(debug):
    """Show application status and configuration."""
    settings = _setup_logging(debug)
    
    # Display status
    console.print(Panel.fit(
        f"[bold green]Autobulk Status[/bold green]\n"
        f"Version: {__version__}\n"
        f"Debug Mode: {settings.debug if hasattr(settings, 'debug') else False}\n"
        f"Logging Level: {settings.logging.level if hasattr(settings, 'logging') else 'INFO'}\n"
        f"Templates Directory: {settings.templates.templates_dir if hasattr(settings, 'templates') else 'templates'}\n"
        f"Database: {settings.database.url if hasattr(settings, 'database') else 'sqlite:///autobulk.db'}\n"
        f"Default Provider: gmail",
        title="Application Status"
    ))


@main.command()
@click.argument("provider")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def test_connection(provider, debug):
    """Test connection to email provider."""
    _setup_logging(debug)
    
    console.print(f"[blue]Testing {provider} connection...[/blue]")
    console.print(f"[yellow]⚠️  {provider} connection testing not implemented yet[/yellow]")


@main.command()
def version():
    """Show version information."""
    console.print(f"Autobulk version {__version__}")


def _setup_logging(debug: bool = False) -> Settings:
    """Load application settings and setup logging."""
    try:
        # Load settings with minimal configuration
        settings = load_settings()
        
        # Override debug flag if specified
        if debug:
            if hasattr(settings, 'debug'):
                settings.debug = True
            if hasattr(settings, 'logging'):
                settings.logging.level = "DEBUG"
        
        # Setup logging
        setup_logging(settings=settings)
        
        return settings
    except Exception:
        # Fallback to basic logging if settings fail to load
        import logging
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        return None


if __name__ == "__main__":
    main()