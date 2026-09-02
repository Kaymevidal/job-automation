from sqlalchemy.orm import Session

from src.core.logger import logger


def sync_all(session: Session, query: str | None = None, pages: int = 1) -> int:
    from src.scrapers import catho, infojobs, remoteok, vagascombr

    paginated_modules = (vagascombr, catho)

    total = 0
    for module in (remoteok, vagascombr, infojobs, catho):
        try:
            if module in paginated_modules:
                total += module.sync_vacancies(session, query, pages=pages)
            else:
                total += module.sync_vacancies(session, query)
        except Exception as e:
            logger.error(f"{module.__name__}: sync failed: {e}")

    return total
