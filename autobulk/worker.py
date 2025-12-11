"""Worker/daemon that continuously dispatches due jobs."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .email import EmailSender
from .models import ExecutionStatus, Job, JobExecution, JobStatus
from .recipients import RecipientResolver
from .scheduler import advance_job
from .db import SessionLocal
from .models import utcnow

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        recipient_resolver: RecipientResolver,
        email_sender: EmailSender,
        poll_interval: float = 5.0,
        run_once: bool = False,
    ) -> None:
        self.recipient_resolver = recipient_resolver
        self.email_sender = email_sender
        self.poll_interval = poll_interval
        self.run_once = run_once

    def start(self) -> None:
        logger.info("Worker starting (poll_interval=%ss, run_once=%s)", self.poll_interval, self.run_once)
        try:
            while True:
                processed = self.tick()
                if self.run_once:
                    logger.info("Worker run_once complete (processed %s jobs)", processed)
                    break
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:  # pragma: no cover - interactive stop
            logger.info("Worker interrupted; shutting down")

    def tick(self) -> int:
        session: Session = SessionLocal()
        processed = 0
        try:
            due_jobs = self._load_due_jobs(session)
            for job in due_jobs:
                self._process_job(session, job)
                processed += 1
            session.commit()
        finally:
            session.close()
        return processed

    def _load_due_jobs(self, session: Session) -> list[Job]:
        now = utcnow()
        stmt = (
            select(Job)
            .where(
                Job.cancelled.is_(False),
                Job.next_run_at.is_not(None),
                Job.next_run_at <= now,
                Job.status.in_([JobStatus.SCHEDULED, JobStatus.FAILED]),
            )
            .order_by(Job.next_run_at.asc())
        )
        return list(session.scalars(stmt))

    def _process_job(self, session: Session, job: Job) -> None:
        execution = JobExecution(
            job_id=job.id,
            status=ExecutionStatus.RUNNING,
            attempt=job.retry_count + 1,
            started_at=utcnow(),
        )
        job.status = JobStatus.RUNNING
        job.last_error = None
        session.add_all([job, execution])
        session.commit()

        try:
            recipients = self.recipient_resolver.resolve(job)
            context = {"job_id": job.id, "attempt": execution.attempt}
            result = self.email_sender.send_bulk(job.template_name, recipients, context=context)
            execution.emails_sent = result.total_recipients
            execution.status = ExecutionStatus.SUCCEEDED
            execution.finished_at = utcnow()
            execution.details = {"recipients": recipients}
            job.retry_count = 0
            advance_job(job)
            session.add_all([job, execution])
            session.commit()
            logger.info("Job %s succeeded (%s recipients)", job.id, result.total_recipients)
        except Exception as exc:  # pragma: no cover - defensive
            self._handle_failure(session, job, execution, exc)

    def _handle_failure(self, session: Session, job: Job, execution: JobExecution, exc: Exception) -> None:
        job.retry_count += 1
        job.last_error = str(exc)
        execution.status = ExecutionStatus.FAILED
        execution.error = str(exc)
        execution.finished_at = utcnow()
        logger.exception("Job %s failed (attempt %s)", job.id, execution.attempt)

        if job.retry_count > job.max_retries:
            job.status = JobStatus.DEAD_LETTER
            job.next_run_at = None
            logger.error("Job %s moved to dead-letter after %s retries", job.id, job.retry_count)
        else:
            job.status = JobStatus.FAILED
            delay = self._retry_delay(job.retry_count)
            job.next_run_at = utcnow() + delay
            logger.info("Job %s scheduled for retry in %s seconds", job.id, int(delay.total_seconds()))

        session.add_all([job, execution])
        session.commit()

    def _retry_delay(self, attempt: int) -> timedelta:
        # Exponential backoff with 30s base window, capped at 10 minutes
        seconds = min(600, 30 * (2 ** (attempt - 1)))
        return timedelta(seconds=seconds)


__all__ = ["Worker"]
