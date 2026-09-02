from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.constants import ScraperSource
from src.core.logger import logger
from src.database.models import Vacancy
from src.scrapers.br_common import (
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    detect_work_mode,
    parse_br_date,
    parse_experience_level,
    slugify,
)

BASE_URL = "https://www.vagas.com.br"
DEFAULT_LISTING_URL = f"{BASE_URL}/vagas-de-todas-as-areas"


def fetch_jobs(query: str | None = None, pages: int = 1) -> list[BeautifulSoup]:
    url = f"{BASE_URL}/vagas-de-{slugify(query)}" if query else DEFAULT_LISTING_URL
    cards = []

    for page in range(1, pages + 1):
        params = {"pagina": page} if page > 1 else None
        response = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_cards = soup.select("li.vaga")
        if not page_cards:
            break
        cards.extend(page_cards)

    return cards


def parse_vacancy(card: BeautifulSoup) -> dict | None:
    link = card.select_one("a.link-detalhes-vaga")
    if link is None or not link.get("data-id-vaga"):
        return None

    location_div = card.select_one("footer .vaga-local")
    location = next(location_div.stripped_strings, None) if location_div else None

    company_el = card.select_one(".emprVaga")
    description_el = card.select_one(".detalhes p")
    level_el = card.select_one(".nivelVaga")
    date_el = card.select_one(".data-publicacao")

    title = link.get_text(separator=" ", strip=True)
    description = description_el.get_text(separator=" ", strip=True) if description_el else None

    return {
        "source": ScraperSource.VAGAS_COM_BR,
        "external_id": link["data-id-vaga"],
        "title": title,
        "company": company_el.get_text(strip=True) if company_el else "Confidencial",
        "location": location,
        "work_mode": detect_work_mode(title, location, description),
        "url": urljoin(BASE_URL, link["href"]),
        "description": description,
        "experience_level": parse_experience_level(level_el.get_text() if level_el else None),
        "posted_at": parse_br_date(date_el.get_text() if date_el else None),
    }


def sync_vacancies(session: Session, query: str | None = None, pages: int = 1) -> int:
    cards = fetch_jobs(query, pages=pages)
    created = 0

    for card in cards:
        try:
            record = parse_vacancy(card)
        except Exception as e:
            logger.warning(f"vagas.com.br: failed to parse a job card: {e}")
            continue

        if record is None:
            continue

        existing = session.execute(
            select(Vacancy).where(
                Vacancy.source == ScraperSource.VAGAS_COM_BR,
                Vacancy.external_id == record["external_id"],
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        session.add(Vacancy(**record))
        created += 1

    logger.info(f"vagas.com.br sync: {created} new vacancies out of {len(cards)} fetched")
    return created
