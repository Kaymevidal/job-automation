import requests

from src.core.config import HUNTER_API_KEY
from src.core.logger import logger

API_URL = "https://api.hunter.io/v2/domain-search"
REQUEST_TIMEOUT = 15

RELEVANT_DEPARTMENTS = {"hr", "recruiting"}


def is_configured() -> bool:
    return bool(HUNTER_API_KEY)


def search_company_emails(company: str, domain: str | None = None) -> list[dict]:
    if not HUNTER_API_KEY:
        return []

    params = {"api_key": HUNTER_API_KEY}
    if domain:
        params["domain"] = domain
    else:
        params["company"] = company

    try:
        response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
    except Exception as e:
        logger.warning(f"hunter.io: request failed for {company}: {e}")
        return []

    if response.status_code != 200:
        logger.warning(f"hunter.io: lookup failed for {company}: HTTP {response.status_code}")
        return []

    emails = response.json().get("data", {}).get("emails", [])
    candidates = []
    for entry in emails:
        value = entry.get("value")
        if not value:
            continue
        candidates.append({
            "email": value,
            "source": "hunter.io",
            "context": f"type={entry.get('type')}, department={entry.get('department')}, "
                       f"position={entry.get('position')}, confidence={entry.get('confidence')}",
            "department": entry.get("department"),
            "type": entry.get("type"),
            "confidence": entry.get("confidence") or 0,
        })

    candidates.sort(
        key=lambda c: (
            c["department"] in RELEVANT_DEPARTMENTS,
            c["type"] == "generic",
            c["confidence"],
        ),
        reverse=True,
    )
    return candidates
