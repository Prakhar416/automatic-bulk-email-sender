# Automatic Bulk Email Sender

A lightweight scheduling and worker service for dispatching bulk emails from templates. Jobs are persisted in SQLite via SQLAlchemy so schedules survive restarts. The CLI allows you to create immediate, delayed, and recurring jobs, while the worker daemon processes due jobs, refreshes recipient lists, and retries failures with backoff.

## Features

- 📆 **Scheduling** powered by APScheduler cron expressions and manual run times
- 💾 **SQLite persistence** for job definitions and execution history with retry counters and error logs
- 🧰 **CLI tooling** (`autobulk`) for creating, listing, cancelling jobs, and viewing execution history
- 🧵 **Worker / daemon** (`autobulk worker`) that refreshes recipient data, sends via `EmailSender`, and records outcomes
- 📓 **Dead-letter semantics** once the job exceeds its retry budget

## Requirements

- Python 3.10+
- Optional: a CSV or JSON cache of recipients (defaults are provided for quick testing)

## Installation

```bash
pip install --upgrade pip
pip install -e .
```

This command exposes the `autobulk` CLI on your PATH.

## Configuration

Environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `AUTOBULK_DB_URL` | Database URL | `sqlite:///$HOME/.autobulk/autobulk.db` |
| `AUTOBULK_WORKER_POLL` | Worker polling interval (seconds) | `5` |
| `AUTOBULK_RECIPIENT_CACHE` | Path to CSV/JSON recipient cache | `$HOME/.autobulk/recipients.csv` |

If the recipient cache is missing, a small in-memory sample list is used so you can experiment immediately.

## Managing Recipients

- **Static list jobs** embed recipients directly through CLI options
- **Filtered jobs** rely on a cache file (CSV or JSON) that contains at least an `email` column/field and optional metadata (e.g., department). The worker reloads this cache every time a job runs.

Example CSV (`~/contacts.csv`):

```csv
email,department
jane@example.com,marketing
sam@example.com,engineering
```

## CLI Usage

Show help:

```bash
autobulk --help
autobulk job --help
```

### Create jobs

Immediate job with static recipients:

```bash
autobulk job create \
  --name "Welcome blast" \
  --template welcome_v1 \
  --recipients jane@example.com,sam@example.com
```

Delayed job (ISO timestamp) using filters:

```bash
autobulk job create \
  --name "Product launch" \
  --template launch_v2 \
  --schedule delayed \
  --run-at 2024-01-31T09:00:00Z \
  --recipient-filter department=marketing
```

Recurring job via cron (runs weekdays at 08:00 UTC):

```bash
autobulk job create \
  --name "Daily digest" \
  --template digest_v5 \
  --schedule recurring \
  --cron "0 8 * * 1-5" \
  --recipient-filter department=engineering
```

### Inspect and manage jobs

```bash
# List all jobs
autobulk job list

# Cancel a job
autobulk job cancel <job-id>

# Show executions
autobulk job executions <job-id> --limit 20
```

## Worker / Scheduler

Run the worker (blocks and polls for due jobs):

```bash
autobulk worker
```

For local testing you can process due jobs once and exit:

```bash
autobulk worker --run-once
```

In production, run the worker under a process manager (systemd, Supervisor, Docker, etc.). The worker:

1. Loads due jobs whose `next_run_at` has elapsed
2. Refreshes recipient data from the cache file (CSV/JSON or defaults)
3. Sends emails via `EmailSender` (logging transport by default)
4. Records execution outcome, retries failures with exponential backoff, and moves exhausted jobs to a dead-letter status
5. Reschedules recurring jobs by computing their next run using APScheduler cron triggers

## Development Tips

- The database and cache directories are created automatically under `$HOME/.autobulk`
- You can override settings per command by exporting the environment variables or passing CLI options
- The worker logs progress and errors to stdout; use `AUTOBULK_WORKER_POLL` to adjust responsiveness

## Roadmap

- Integrations with real email transports (SES, SendGrid, etc.)
- Google Sheets or Airtable connectors for live recipient sources
- Web dashboard for monitoring job metrics
