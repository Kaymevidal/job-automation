import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from ollama import Client
from pydantic import BaseModel

from src.core.config import OLLAMA_HOST, OLLAMA_MODEL
from src.core.logger import logger
from src.scrapers.br_common import REQUEST_HEADERS, REQUEST_TIMEOUT

SEARCH_URL = "https://html.duckduckgo.com/html/"
MAX_SEARCH_RESULTS = 6
MAX_PAGE_FETCHES = 4
MAX_CANDIDATES = 6

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
SKIP_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "indeed.com",
    "glassdoor.com", "twitter.com", "x.com", "youtube.com", "tiktok.com",
)
GENERIC_LOCAL_PARTS = {
    "webmaster", "privacy", "abuse", "noreply", "no-reply", "postmaster",
    "dpo", "suporte", "support", "sac",
}

_client = Client(host=OLLAMA_HOST)


class EmailChoice(BaseModel):
    email: str | None
    reasoning: str


def _unwrap_ddg_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query:
        return query["uddg"][0]
    return href if href.startswith("http") else None


def search_web(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    response = requests.get(SEARCH_URL, params={"q": query}, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for link in soup.select("a.result__a")[:max_results]:
        url = _unwrap_ddg_url(link.get("href"))
        if url:
            results.append({"title": link.get_text(strip=True), "url": url})
    return results


def _extract_emails(text: str) -> set[str]:
    found = {match.group(0).lower() for match in EMAIL_RE.finditer(text)}
    return {email for email in found if email.split("@")[0] not in GENERIC_LOCAL_PARTS}


def _is_skippable(url: str) -> bool:
    return any(domain in url for domain in SKIP_DOMAINS)


def find_candidate_emails(company: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    fetched = 0

    results = search_web(f"{company} contato email RH")

    for result in results:
        for email in _extract_emails(result["title"]):
            if email not in seen:
                seen.add(email)
                candidates.append({"email": email, "source": result["url"], "context": result["title"]})

        if _is_skippable(result["url"]) or fetched >= MAX_PAGE_FETCHES:
            continue

        try:
            page = requests.get(result["url"], headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            fetched += 1
        except Exception as e:
            logger.warning(f"company_email: failed to fetch {result['url']}: {e}")
            continue

        for email in _extract_emails(page.text):
            if email not in seen:
                seen.add(email)
                candidates.append({"email": email, "source": result["url"], "context": result["title"]})

        if len(candidates) >= MAX_CANDIDATES:
            break

    return candidates


def choose_best_email(company: str, vacancy_title: str, candidates: list[dict]) -> EmailChoice:
    if not candidates:
        return EmailChoice(email=None, reasoning="No email candidates found")

    if len(candidates) == 1:
        return EmailChoice(email=candidates[0]["email"], reasoning="Only candidate found")

    listing = "\n".join(
        f"- {c['email']} (found on {c['source']}, page title: {c['context']})" for c in candidates
    )
    prompt = f"""A candidate is applying for the job "{vacancy_title}" at "{company}". Below are email \
addresses found while searching the web for this company's contact information.

{listing}

Pick the single email most likely to be the right contact for a job application (HR, recruiting, \
or a general company contact). Avoid personal-looking addresses unrelated to the company and avoid \
third-party sites unless they are clearly listing this company's own contact. If none of them look \
like a plausible fit, return null for email."""

    response = _client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=EmailChoice.model_json_schema(),
    )
    return EmailChoice.model_validate_json(response["message"]["content"])


def find_company_email(company: str, vacancy_title: str) -> str | None:
    candidates = find_candidate_emails(company)
    logger.info(f"company_email: {len(candidates)} candidate(s) found for {company}")

    choice = choose_best_email(company, vacancy_title, candidates)
    logger.info(f"company_email: chose {choice.email} for {company} - {choice.reasoning}")
    return choice.email
