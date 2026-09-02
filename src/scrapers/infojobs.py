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
    fetch_full_description,
    parse_experience_level,
)

BASE_URL = "https://www.infojobs.com.br"
LISTING_URL = f"{BASE_URL}/empregos.aspx"
MAX_DETAIL_FETCHES = 30


def fetch_jobs(query: str | None = None) -> list[BeautifulSoup]:
    params = {"palabra": query} if query else None
    response = requests.get(LISTING_URL, params=params, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.select("div.js_rowCard[data-id]")


def parse_vacancy(card: BeautifulSoup) -> dict | None:
    external_id = card.get("data-id")
    href = card.get("data-href")
    title_el = card.select_one(".js_vacancyTitle")

    if not external_id or not href or title_el is None:
        return None

    company_el = card.select_one("a[href*='empresa-']")
    location_el = card.select_one(".mb-8")

    return {
        "source": ScraperSource.INFOJOBS,
        "external_id": external_id,
        "title": title_el.get_text(separator=" ", strip=True),
        "company": company_el.get_text(separator=" ", strip=True) if company_el else "Nao informado",
        "location": location_el.get_text(separator=" ", strip=True).split(",")[0].strip() if location_el else None,
        "work_mode": detect_work_mode(card.get_text()),
        "url": urljoin(BASE_URL, href),
        "description": None,
        "experience_level": parse_experience_level(card.get_text()),
        "posted_at": None,
    }


def sync_vacancies(session: Session, query: str | None = None) -> int:
    cards = fetch_jobs(query)
    created = 0
    detail_fetches = 0

    for card in cards:
        try:
            record = parse_vacancy(card)
        except Exception as e:
            logger.warning(f"infojobs: failed to parse a job card: {e}")
            continue

        if record is None:
            continue

        existing = session.execute(
            select(Vacancy).where(
                Vacancy.source == ScraperSource.INFOJOBS,
                Vacancy.external_id == record["external_id"],
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        if detail_fetches < MAX_DETAIL_FETCHES:
            record["description"] = fetch_full_description(record["url"])
            detail_fetches += 1

        session.add(Vacancy(**record))
        created += 1

    logger.info(f"infojobs sync: {created} new vacancies out of {len(cards)} fetched")
    return created
