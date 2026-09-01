from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.constants import ScraperSource
from src.core.logger import logger
from src.database.models import Vacancy
from src.scrapers.br_common import REQUEST_HEADERS, REQUEST_TIMEOUT, parse_experience_level

BASE_URL = "https://www.catho.com.br"
LISTING_URL = f"{BASE_URL}/vagas/"


def fetch_jobs() -> list[BeautifulSoup]:
    response = requests.get(LISTING_URL, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.select("li[data-offer-item]")


def _location_text(card: BeautifulSoup) -> str | None:
    location_p = card.select_one(".i_job_location")
    if location_p is None:
        return None

    container = location_p.find_parent("p")
    if container is None:
        return None

    text = container.get_text(separator=" ", strip=True)
    return text.split("-", 1)[-1].strip() if "-" in text else text


def parse_vacancy(card: BeautifulSoup) -> dict | None:
    external_id = card.get("data-offer-item")
    link = card.select_one("h2.title_offer a")

    if not external_id or link is None:
        return None

    company_el = card.select_one("p .text-12")

    return {
        "source": ScraperSource.CATHO,
        "external_id": external_id,
        "title": link.get_text(separator=" ", strip=True),
        "company": company_el.get_text(strip=True) if company_el else "Confidencial",
        "location": _location_text(card),
        "url": urljoin(BASE_URL, link["href"]),
        "description": None,
        "experience_level": parse_experience_level(card.get_text()),
        "posted_at": None,
    }


def sync_vacancies(session: Session) -> int:
    cards = fetch_jobs()
    created = 0

    for card in cards:
        try:
            record = parse_vacancy(card)
        except Exception as e:
            logger.warning(f"catho: failed to parse a job card: {e}")
            continue

        if record is None:
            continue

        existing = session.execute(
            select(Vacancy).where(
                Vacancy.source == ScraperSource.CATHO,
                Vacancy.external_id == record["external_id"],
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        session.add(Vacancy(**record))
        created += 1

    logger.info(f"catho sync: {created} new vacancies out of {len(cards)} fetched")
    return created
