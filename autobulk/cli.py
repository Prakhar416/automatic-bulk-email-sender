"""Command line interface for scheduling and running autobulk jobs."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer
from dateutil import parser as date_parser
from rich.console import Console
from rich.table import Table

from .config import Settings
from .db import init_db, session_scope
from .email import EmailSender
from .models import JobStatus, RecipientSource, ScheduleType
from .recipients import RecipientResolver
from .scheduler import JobCreateRequest, SchedulingService
from .worker import Worker

console = Console()
app = typer.Typer(help="Automatic bulk email scheduler")
jobs_app = typer.Typer(help="Manage scheduled jobs")
app.add_typer(jobs_app, name="job")

settings = Settings.load()


@app.callback()
def configure(_: typer.Context) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    init_db()


@app.command()
def worker(
    poll_interval: Optional[float] = typer.Option(
        None,
        help="Override the default worker poll interval (seconds)",
    ),
    run_once: bool = typer.Option(False, help="Process due jobs once and exit"),
) -> None:
    """Start the worker/daemon that processes scheduled jobs."""

    resolver = RecipientResolver(settings.recipient_cache_path)
    sender = EmailSender()
    interval = poll_interval or settings.worker_poll_interval
    Worker(
        recipient_resolver=resolver,
        email_sender=sender,
        poll_interval=interval,
        run_once=run_once,
    ).start()


@jobs_app.command("create")
def create_job(
    name: str = typer.Option(..., prompt=True, help="Friendly job name"),
    template: str = typer.Option(..., prompt=True, help="Template identifier"),
    schedule: ScheduleType = typer.Option(
        ScheduleType.IMMEDIATE,
        case_sensitive=False,
        help="Schedule type: immediate, delayed, recurring",
    ),
    run_at: Optional[str] = typer.Option(None, help="ISO timestamp for delayed jobs"),
    cron: Optional[str] = typer.Option(None, help="Cron expression for recurring jobs"),
    recipient_filter: List[str] = typer.Option(
        None,
        "--recipient-filter",
        "-F",
        help="recipient filter in key=value format",
    ),
    recipients: Optional[str] = typer.Option(
        None,
        help="Comma separated list of recipient emails for static jobs",
    ),
    recipients_file: Optional[Path] = typer.Option(
        None,
        help="Path to a newline separated recipients file",
        exists=True,
        readable=True,
    ),
    max_retries: int = typer.Option(3, help="Maximum retries before dead-letter"),
) -> None:
    """Create a new scheduled job."""

    parsed_run_at = _parse_datetime(run_at)
    recipient_payload = _load_recipients(recipients, recipients_file)
    recipient_filter_dict = _parse_filters(recipient_filter)

    if recipient_payload and recipient_filter_dict:
        raise typer.BadParameter("Provide either recipients or recipient filters, not both")
    if not recipient_payload and not recipient_filter_dict:
        raise typer.BadParameter("You must provide recipients or a recipient filter")

    recipient_source = (
        RecipientSource.STATIC_LIST if recipient_payload else RecipientSource.FILTER
    )

    if schedule == ScheduleType.DELAYED and not parsed_run_at:
        raise typer.BadParameter("Delayed jobs require --run-at timestamp")
    if schedule == ScheduleType.RECURRING and not cron:
        raise typer.BadParameter("Recurring jobs require --cron expression")

    request = JobCreateRequest(
        name=name,
        template_name=template,
        schedule_type=schedule,
        recipient_source=recipient_source,
        recipient_filter=recipient_filter_dict,
        recipients=recipient_payload,
        run_at=parsed_run_at,
        cron_expression=cron,
        max_retries=max_retries,
    )

    with session_scope() as session:
        service = SchedulingService(session)
        job = service.create_job(request)
        console.print(f"Created job [bold]{job.id}[/] next run at {job.next_run_at}")


@jobs_app.command("list")
def list_jobs() -> None:
    """List all scheduled jobs."""

    with session_scope() as session:
        service = SchedulingService(session)
        jobs = service.list_jobs()

    table = Table(title="Scheduled Jobs")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Template")
    table.add_column("Schedule", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Next Run", justify="center")
    table.add_column("Retries", justify="right")

    for job in jobs:
        next_run = job.next_run_at.isoformat() if job.next_run_at else "-"
        table.add_row(
            job.id,
            job.name,
            job.template_name,
            job.schedule_type.value,
            job.status.value,
            next_run,
            f"{job.retry_count}/{job.max_retries}",
        )

    console.print(table)


@jobs_app.command("cancel")
def cancel_job(job_id: str = typer.Argument(..., help="ID of the job to cancel")) -> None:
    """Cancel a scheduled job."""

    with session_scope() as session:
        service = SchedulingService(session)
        try:
            job = service.cancel_job(job_id)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    console.print(f"Job [bold]{job.id}[/] cancelled")


@jobs_app.command("executions")
def list_executions(
    job_id: str = typer.Argument(..., help="Job ID"),
    limit: int = typer.Option(10, help="Number of executions to display"),
) -> None:
    """List recent executions for a job."""

    with session_scope() as session:
        service = SchedulingService(session)
        executions = service.recent_executions(job_id, limit=limit)

    table = Table(title=f"Executions for job {job_id}")
    table.add_column("Execution ID", style="cyan")
    table.add_column("Attempt", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Sent", justify="right")
    table.add_column("Started at")
    table.add_column("Finished at")
    table.add_column("Error")

    for execution in executions:
        table.add_row(
            execution.id,
            str(execution.attempt),
            execution.status.value,
            str(execution.emails_sent),
            execution.started_at.isoformat() if execution.started_at else "-",
            execution.finished_at.isoformat() if execution.finished_at else "-",
            (execution.error or "-")[:60],
        )

    console.print(table)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = date_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_filters(items: Optional[List[str]]) -> dict[str, str]:
    filters: dict[str, str] = {}
    if not items:
        return filters
    for item in items:
        if "=" not in item:
            raise typer.BadParameter("Filters must be in key=value format")
        key, value = item.split("=", 1)
        filters[key.strip()] = value.strip()
    return filters


def _load_recipients(recipients: Optional[str], recipients_file: Optional[Path]) -> list[str]:
    payload: list[str] = []
    if recipients:
        payload.extend([email.strip() for email in recipients.split(",") if email.strip()])
    if recipients_file:
        payload.extend([
            line.strip()
            for line in recipients_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ])
    return payload


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    app()
