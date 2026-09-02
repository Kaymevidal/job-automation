# Job Automation Pro

Desktop application that helps a job seeker find and shortlist vacancies
that actually match their profile: it scrapes postings from several job
boards, deduplicates them across sources, scores compatibility against a
candidate profile using a local LLM (Ollama), and can tailor a resume
per application. It does not contact anyone on the candidate's behalf —
see [Status](#status) for what is and isn't automated.

## Download (Windows)

Grab `JobAutomationPro.exe` from the
[Releases page](../../releases) — no Python or pip install required.

Before running it, install [Ollama](https://ollama.com) (used for
compatibility scoring and resume tailoring) and pull a model:

```
ollama pull gemma2:9b
```

Then just double-click `JobAutomationPro.exe`. It creates a `data/` and
`logs/` folder next to itself on first run — nothing else to configure.
Fill in the Perfil tab (profile) before using the scoring/resume features.

## Architecture

The GUI (`src/gui_main.py`) is the primary way to run this app; a separate
headless worker (`src/main.py`) can also run the same sync+score pipeline
in Docker, driven by `docker-compose.yml` — useful for scheduled/unattended
runs, but not required to use the app.

Both entrypoints share the same codebase under `src/`. The scraper,
scoring, and document modules are plain functions over a SQLAlchemy
session with no Docker-specific dependency, so the GUI calls them
directly instead of duplicating logic.

```
src/
  core/
    config.py        Environment configuration
    constants.py      Domain enums and thresholds
    logger.py         Logging setup (loguru)
  database/
    models.py          SQLAlchemy models
    database.py         Engine, session management
    migrations.py        Schema creation and auto column migration
  scrapers/
    remoteok.py           RemoteOK API (remote/tech)
    vagascombr.py          vagas.com.br (all industries, BR)
    infojobs.py             InfoJobs (all industries, BR)
    catho.py                  Catho (all industries, BR)
    dedup.py                    Cross-source duplicate detection
  scoring/
    compatibility.py       Keyword pre-filter + Ollama scoring + work mode
  documents/
    resume_tailor.py       Ollama resume tailoring, rendered to .docx
    applications.py          get_or_create_application
  gui/
    main_window.py           Tabs: Vagas, Candidaturas, Perfil
    pipeline.py                Runs sync -> score on a QThread
  main.py                Headless worker entrypoint (Docker)
  gui_main.py            Desktop GUI entrypoint (Windows host / the .exe)
```

## Data model

- `User` — candidate profile: `profile_summary`, `skills`, `desired_roles`,
  `salary_expectation`, `languages`, LinkedIn/portfolio URLs, and
  `resume_path` (a `.docx` file the app can tailor per application)
- `Vacancy` — a scraped job posting: source, tags, description, work mode,
  `compatibility_score`, and `duplicate_of_id` for cross-source dedup
- `Application` — the link between a user and a vacancy, created only when
  the user opens the posting from the Vagas tab; tracks status and the
  tailored resume path
- `SchedulerJob` — scheduled/recurring jobs tracked by APScheduler (not
  wired up yet; the pipeline currently runs on demand)

## Building the .exe yourself

```
pip install -r requirements-build.txt
pyinstaller JobAutomationPro.spec
```

The result is `dist/JobAutomationPro.exe`, a single file with no external
Python dependency. `.github/workflows/build-exe.yml` builds and attaches
it to a GitHub Release automatically whenever a `v*` tag is pushed.

## Running the Docker worker (optional)

1. Copy the environment template: `cp .env.example .env`
2. `docker compose up -d` — starts Ollama and runs the worker once
   against it. The worker container exits after a single run
   (`restart: "no"`); rerun with `docker compose up job-automation`
   as needed. It shares the same `data/job_automation.db` as the GUI
   if run from the same folder.

## Local development

```
pip install -r requirements.txt
python -m src.gui_main
```

## Dependencies

Two requirement files exist because the GUI only runs on Windows:

- `requirements.txt` — full set, used for native Windows development
  and for building the `.exe`
- `requirements-docker.txt` — headless subset used by the Docker image
- `requirements-build.txt` — `requirements.txt` plus PyInstaller

## Configuration

Environment variables (see `.env.example`), read from `.env` next to the
project root (or next to the `.exe` when running the packaged build):

| Variable          | Description                              | Default                                  |
|-------------------|-------------------------------------------|-------------------------------------------|
| `DATABASE_URL`    | SQLAlchemy connection string              | `sqlite:///./data/job_automation.db`      |
| `OLLAMA_BASE_URL` | Ollama server URL                         | `http://localhost:11434`                  |
| `OLLAMA_MODEL`    | Model used for compatibility scoring      | `gemma2:9b`                               |
| `LOG_LEVEL`       | Logging level                             | `INFO`                                    |
| `DATA_DIR`        | Directory for the SQLite database         | `./data`                                  |
| `LOG_DIR`         | Directory for log files                   | `./logs`                                  |

## Status

Working: multi-source scraping (RemoteOK, vagas.com.br, InfoJobs, Catho)
with pagination and cross-source deduplication, keyword pre-filter +
Ollama compatibility scoring (with work-mode classification), resume
tailoring per application, and a PyQt6 GUI covering all of it.

By design, not automated:

- The app never contacts a company or sends anything on the candidate's
  behalf — a prior version could find a company's email and draft an
  Outlook message; this was removed due to LGPD/privacy concerns around
  scraping and storing personal email addresses. An `Application` row
  now only exists because the user actually opened that posting to apply.
- No cover letter generation (removed alongside the email feature, since
  it existed to accompany an emailed application).

Known gaps:

- LinkedIn/Indeed/Glassdoor are defined in `ScraperSource` but not
  implemented — Indeed sits behind a Cloudflare challenge, LinkedIn was
  ruled out due to its Terms of Service.
- Resume tailoring only supports `.docx`; PDF resumes are left as-is
  (no PDF text-extraction dependency yet).
- `SchedulerJob`/APScheduler are not wired up; the pipeline runs only
  when triggered (`docker compose up`, or the GUI's "Buscar e Processar
  Vagas" / per-vacancy buttons).
- Single local user only; the GUI's Perfil tab edits one profile row.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup
instructions and project scope (in particular, what kinds of features won't
be merged and why). Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
