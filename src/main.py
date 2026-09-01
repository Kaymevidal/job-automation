import sys

from src.core.config import APP_NAME, APP_VERSION
from src.core.logger import log_startup, logger
from src.database.database import check_connection, get_session
from src.database.migrations import check_database_status, run_migrations
from src.scrapers.remoteok import sync_vacancies


def main() -> int:
    log_startup()

    if not check_connection():
        logger.error("Database is not accessible, aborting")
        return 1

    run_migrations()

    status = check_database_status()
    logger.info(f"Database status: {status}")

    with get_session() as session:
        sync_vacancies(session)

    logger.info(f"{APP_NAME} v{APP_VERSION} finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
