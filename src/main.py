import sys

from sqlalchemy import select

from src.core.config import APP_NAME, APP_VERSION
from src.core.logger import log_startup, logger
from src.database.database import check_connection, get_session
from src.database.migrations import check_database_status, run_migrations
from src.database.models import User
from src.documents.cover_letter import generate_applications_for_top_matches
from src.scoring.compatibility import score_pending_vacancies
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

    with get_session() as session:
        users = session.execute(select(User)).scalars().all()
        if not users:
            logger.info("No users registered yet, skipping compatibility scoring")
        for user in users:
            score_pending_vacancies(session, user)
            generate_applications_for_top_matches(session, user)

    logger.info(f"{APP_NAME} v{APP_VERSION} finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
