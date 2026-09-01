#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports - Job Automation Pro")
print("-" * 60)

try:
    print("[1/6] src.core.config")
    from src.core.config import (
        APP_NAME, APP_VERSION, DATABASE_URL, OLLAMA_HOST, LOG_LEVEL
    )
    print(f"  APP_NAME: {APP_NAME}")
    print(f"  APP_VERSION: {APP_VERSION}")
    print(f"  DATABASE_URL: {DATABASE_URL}")
    print(f"  OLLAMA_HOST: {OLLAMA_HOST}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

try:
    print("[2/6] src.core.constants")
    from src.core.constants import (
        ApplicationStatus, ExperienceLevel, ScraperSource, MIN_COMPATIBILITY_SCORE
    )
    print(f"  ApplicationStatus.PENDING: {ApplicationStatus.PENDING}")
    print(f"  ExperienceLevel.JUNIOR: {ExperienceLevel.JUNIOR}")
    print(f"  ScraperSource.LINKEDIN: {ScraperSource.LINKEDIN}")
    print(f"  MIN_COMPATIBILITY_SCORE: {MIN_COMPATIBILITY_SCORE}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

try:
    print("[3/6] src.core.logger")
    from src.core.logger import logger, log_startup
    logger.info("Test log message")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

try:
    print("[4/6] src.database.models")
    from src.database.models import User, Vacancy, Application, SchedulerJob, Base
    print(f"  User model: {User.__tablename__}")
    print(f"  Vacancy model: {Vacancy.__tablename__}")
    print(f"  Application model: {Application.__tablename__}")
    print(f"  SchedulerJob model: {SchedulerJob.__tablename__}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

try:
    print("[5/6] src.database.database")
    from src.database.database import get_session, check_connection
    is_connected = check_connection()
    print(f"  Database connection OK: {is_connected}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

try:
    print("[6/6] src.database.migrations")
    from src.database.migrations import run_migrations, check_database_status
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

print("-" * 60)
print("All imports succeeded")
