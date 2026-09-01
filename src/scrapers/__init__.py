from sqlalchemy.orm import Session

from src.core.logger import logger


def sync_all(session: Session, query: str | None = None) -> int:
    from src.scrapers import catho, infojobs, remoteok, vagascombr

    total = 0
    for module in (remoteok, vagascombr, infojobs, catho):
        try:
            total += module.sync_vacancies(session, query)
        except Exception as e:
            logger.error(f"{module.__name__}: sync failed: {e}")

    return total
