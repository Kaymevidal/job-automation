# Job Automation Pro

Desktop application for automating the job application workflow: scraping job
postings, scoring their compatibility against a candidate profile using a
local LLM, generating tailored application documents, and tracking
applications through a scheduler.

## Architecture

The system is split into two runtimes:

- **Host (Windows)** — the PyQt6 desktop GUI and Outlook integration
  (`pywin32`), which cannot run inside a Linux container.
- **Container (Docker)** — a headless worker that talks to Ollama, runs
  scraping and scoring jobs, generates documents, and persists everything to
  a shared SQLite database.

Both runtimes share the same codebase under `src/` and the same database.

```
src/
  core/
    config.py       Environment configuration
    constants.py     Domain enums and thresholds
    logger.py        Logging setup (loguru)
  database/
    models.py         SQLAlchemy models
    database.py        Engine, session management
    migrations.py       Schema creation and status checks
  main.py               Headless worker entrypoint
```

## Data model

- `User` — candidate profile
- `Vacancy` — a scraped job posting, with source and compatibility score
- `Application` — the link between a user and a vacancy, with status
- `SchedulerJob` — scheduled/recurring jobs tracked by APScheduler

## Requirements

- Docker and Docker Compose
- Python 3.12 (for running the GUI natively on Windows)
- [Ollama](https://ollama.com) model pulled locally, e.g. `gemma2:9b`

## Setup

1. Copy the environment template:

   ```
   cp .env.example .env
   ```

2. Build and start the stack:

   ```
   docker compose up -d
   ```

   This starts the Ollama server and runs the worker once against it. The
   worker container exits after a single run (`restart: "no"`); rerun with
   `docker compose up job-automation` as needed.

3. For local (non-Docker) development on Windows, install the full
   dependency set and run the import check:

   ```
   pip install -r requirements.txt
   python test_imports.py
   ```

## Dependencies

Two requirement files exist because the GUI and Outlook integration only
run on Windows:

- `requirements.txt` — full set, used for native Windows development
  (includes PyQt6 and pywin32)
- `requirements-docker.txt` — headless subset used by the Docker image

## Configuration

Environment variables (see `.env.example`):

| Variable          | Description                              | Default                                  |
|-------------------|-------------------------------------------|-------------------------------------------|
| `DATABASE_URL`    | SQLAlchemy connection string              | `sqlite:///./data/job_automation.db`      |
| `OLLAMA_BASE_URL` | Ollama server URL                         | `http://localhost:11434`                  |
| `OLLAMA_MODEL`    | Model used for compatibility scoring      | `gemma2:9b`                               |
| `LOG_LEVEL`       | Logging level                             | `INFO`                                    |
| `DATA_DIR`        | Directory for the SQLite database         | `./data`                                  |
| `LOG_DIR`         | Directory for log files                   | `./logs`                                  |

## Status

Foundational layer only: configuration, logging, database models, and the
worker entrypoint. Scraping, compatibility scoring, and document generation
are not yet implemented.
