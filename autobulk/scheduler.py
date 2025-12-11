"""Scheduling helpers built on top of the persistence layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from apscheduler.triggers.cron import CronTrigger

from .models import Job, JobExecution, JobStatus, RecipientSource, ScheduleType, utcnow


@dataclass
class JobCreateRequest:
    name: str
    template_name: str
    schedule_type: ScheduleType
    recipient_source: RecipientSource
    recipient_filter: dict[str, Any] | None = None
    recipients: Iterable[str] | None = None
    run_at: datetime | None = None
    cron_expression: str | None = None
    max_retries: int = 3


class SchedulingService:
    """Encapsulates persistence operations for jobs."""

    def __init__(self, session) -> None:
        self.session = session

    def create_job(self, request: JobCreateRequest) -> Job:
        job = Job(
            name=request.name,
            template_name=request.template_name,
            schedule_type=request.schedule_type,
            recipient_source=request.recipient_source,
            recipient_filter=request.recipient_filter,
            recipients=list(request.recipients or []) or None,
            run_at=request.run_at,
            cron_expression=request.cron_expression,
            max_retries=request.max_retries,
            status=JobStatus.SCHEDULED,
        )
        job.next_run_at = compute_next_run(job)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def list_jobs(self) -> list[Job]:
        return self.session.query(Job).order_by(Job.created_at.desc()).all()

    def get_job(self, job_id: str) -> Job | None:
        return self.session.query(Job).filter(Job.id == job_id).first()

    def cancel_job(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = JobStatus.CANCELLED
        job.cancelled = True
        job.next_run_at = None
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def recent_executions(self, job_id: str, limit: int = 10) -> list[JobExecution]:
        return (
            self.session.query(JobExecution)
            .filter(JobExecution.job_id == job_id)
            .order_by(JobExecution.created_at.desc())
            .limit(limit)
            .all()
        )


def compute_next_run(job: Job, reference: datetime | None = None) -> datetime | None:
    reference = reference or utcnow()
    if job.schedule_type == ScheduleType.IMMEDIATE:
        return reference
    if job.schedule_type == ScheduleType.DELAYED:
        if not job.run_at:
            raise ValueError("Delayed jobs must define run_at")
        return job.run_at
    if job.schedule_type == ScheduleType.RECURRING:
        if not job.cron_expression:
            raise ValueError("Recurring jobs require a cron expression")
        trigger = CronTrigger.from_crontab(job.cron_expression, timezone=timezone.utc)
        return trigger.get_next_fire_time(previous_fire_time=None, now=reference)
    raise ValueError(f"Unsupported schedule type: {job.schedule_type}")


def advance_job(job: Job) -> None:
    """Update job after a run completes."""
    if job.schedule_type == ScheduleType.RECURRING:
        job.next_run_at = compute_next_run(job, reference=utcnow())
        job.status = JobStatus.SCHEDULED
    else:
        job.next_run_at = None
        job.status = JobStatus.COMPLETED


__all__ = ["SchedulingService", "JobCreateRequest", "compute_next_run", "advance_job"]
