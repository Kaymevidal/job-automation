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
The scraper, scoring, and document generation modules are plain functions
over a SQLAlchemy session with no Docker-specific dependency, so the GUI
calls them directly instead of duplicating logic.

```
src/
  core/
    config.py        Environment configuration
    constants.py      Domain enums and thresholds
    logger.py         Logging setup (loguru)
  database/
    models.py          SQLAlchemy models
    database.py         Engine, session management
    migrations.py        Schema creation and status checks
  scrapers/
    remoteok.py           Fetches and persists vacancies from the RemoteOK API
  scoring/
    compatibility.py       Keyword pre-filter + Ollama compatibility scoring
  documents/
    cover_letter.py         Ollama cover letter generation, rendered to PDF
  gui/
    main_window.py           Tabs: Vagas, Candidaturas, Perfil
    pipeline.py                Runs sync -> score -> generate on a QThread
  main.py                Headless worker entrypoint (Docker)
  gui_main.py            Desktop GUI entrypoint (Windows host)
```

## Data model

- `User` — candidate profile, including `profile_summary` (free text used
  for compatibility scoring)
- `Vacancy` — a scraped job posting: source, tags, description, and
  `compatibility_score`
- `Application` — the link between a user and a vacancy, with status and
  the generated cover letter path
- `SchedulerJob` — scheduled/recurring jobs tracked by APScheduler (not
  wired up yet; the pipeline currently runs on demand)

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

4. Launch the desktop GUI (Windows host, requires PyQt6 from step 3):

   ```
   python -m src.gui_main
   ```

   Fill in the Perfil tab (name, email, and profile_summary) first — the
   scoring step skips users with no profile_summary. The Vagas and
   Candidaturas tabs read from the same database the Docker worker writes
   to, so either side can run the pipeline.

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

End-to-end pipeline working: RemoteOK scraping, keyword pre-filter +
Ollama compatibility scoring, cover letter generation (PDF), and a PyQt6
GUI to review vacancies, manage application status, and edit the profile.

Known gaps:

- Only one scraper source (RemoteOK); LinkedIn/Indeed/Glassdoor are
  defined in `ScraperSource` but not implemented — Indeed in particular
  sits behind a Cloudflare challenge that blocks plain HTTP scraping.
- No resume generation, only cover letters — `resume_path` is a file the
  user provides, not something the app builds.
- `SchedulerJob`/APScheduler are not wired up; the pipeline runs only when
  triggered (`docker compose up` or the GUI button).
- Single local user only; the GUI's Perfil tab edits one profile row.
