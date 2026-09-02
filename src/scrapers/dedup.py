from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.logger import logger
from src.database.models import Vacancy
from src.scrapers.br_common import GENERIC_COMPANY_NAMES, normalize_city_for_dedup, normalize_for_dedup


def deduplicate_vacancies(session: Session) -> int:
    vacancies = session.execute(
        select(Vacancy)
        .where(Vacancy.duplicate_of_id.is_(None))
        .order_by(Vacancy.scraped_at.asc())
    ).scalars().all()

    canonical_by_key: dict[tuple[str, str, str], Vacancy] = {}
    marked = 0

    for vacancy in vacancies:
        company_key = normalize_for_dedup(vacancy.company)
        if company_key in GENERIC_COMPANY_NAMES:
            continue

        # Remote postings have no meaningful city to disambiguate by, so
        # title+company alone decides the match for them.
        city_key = "" if vacancy.work_mode and vacancy.work_mode.value == "remote" \
            else normalize_city_for_dedup(vacancy.location)

        key = (normalize_for_dedup(vacancy.title), company_key, city_key)
        if not key[0]:
            continue

        canonical = canonical_by_key.get(key)
        if canonical is None:
            canonical_by_key[key] = vacancy
            continue

        vacancy.duplicate_of_id = canonical.id
        marked += 1

    if marked:
        session.commit()

    logger.info(f"Deduplication: marked {marked} of {len(vacancies)} vacancies as duplicates")
    return marked
