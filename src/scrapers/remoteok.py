from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.constants import ScraperSource
from src.core.logger import logger
from src.database.models import Vacancy

API_URL = "https://remoteok.com/api"
REQUEST_HEADERS = {"User-Agent": "job-automation-pro (+https://github.com/)"}
REQUEST_TIMEOUT = 15


def fetch_jobs(query: str | None = None) -> list[dict]:
    params = {"tag": query} if query else None
    response = requests.get(API_URL, params=params, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return [item for item in response.json() if "id" in item]


def _clean_description(html: str | None) -> str | None:
    if not html:
        return None
    return BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()


def _salary_range(record: dict) -> str | None:
    salary_min = record.get("salary_min") or 0
    salary_max = record.get("salary_max") or 0
    if not salary_min and not salary_max:
        return None
    return f"${salary_min:,} - ${salary_max:,}"


def parse_vacancy(record: dict) -> dict:
    posted_at = None
    if record.get("epoch"):
        posted_at = datetime.fromtimestamp(record["epoch"], tz=timezone.utc)

    return {
        "source": ScraperSource.REMOTEOK,
        "external_id": str(record["id"]),
        "title": record.get("position", ""),
        "company": record.get("company", ""),
        "location": record.get("location") or "Remote",
        "url": record.get("url", ""),
        "description": _clean_description(record.get("description")),
        "salary_range": _salary_range(record),
        "posted_at": posted_at,
        "tags": ",".join(record.get("tags") or []) or None,
    }


def sync_vacancies(session: Session, query: str | None = None) -> int:
    records = fetch_jobs(query)
    created = 0

    for record in records:
        external_id = str(record["id"])
        existing = session.execute(
            select(Vacancy).where(
                Vacancy.source == ScraperSource.REMOTEOK,
                Vacancy.external_id == external_id,
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        session.add(Vacancy(**parse_vacancy(record)))
        created += 1

    logger.info(f"RemoteOK sync: {created} new vacancies out of {len(records)} fetched")
    return created
