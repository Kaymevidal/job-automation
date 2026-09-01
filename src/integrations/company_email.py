import re
import urllib.parse

import requests
from bs4 import BeautifulSoup
from ollama import Client
from pydantic import BaseModel

from src.core.config import OLLAMA_HOST, OLLAMA_MODEL
from src.core.logger import logger
from src.integrations import hunter_io
from src.scrapers.br_common import REQUEST_HEADERS, REQUEST_TIMEOUT

SEARCH_URL = "https://html.duckduckgo.com/html/"
SEARCH_QUERIES = [
    "{company} contato email RH",
    "{company} trabalhe conosco vagas",
    "{company} fale conosco",
]
MAX_RESULTS_PER_QUERY = 5
MAX_PAGE_FETCHES = 6
MAX_CANDIDATES = 10

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
NON_EMAIL_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp",
    "css", "js", "woff", "woff2", "ttf", "eot", "mp4", "pdf",
}
SKIP_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "indeed.com",
    "glassdoor.com", "twitter.com", "x.com", "youtube.com", "tiktok.com",
)
GENERIC_LOCAL_PARTS = {
    "webmaster", "privacy", "abuse", "noreply", "no-reply", "postmaster",
    "dpo", "suporte", "support", "sac", "exemplo", "example", "seuemail",
    "seunome", "test", "teste", "user", "usuario",
}
PLACEHOLDER_DOMAINS = {
    "email.com", "exemplo.com", "example.com", "domain.com", "test.com",
    "teste.com", "seudominio.com", "seudominio.com.br", "dominio.com",
}
RELEVANT_LOCAL_PARTS = {
    "rh", "vagas", "recrutamento", "carreiras", "trabalheconosco",
    "curriculo", "curriculos", "recruiting", "careers", "jobs", "hr",
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


def search_web(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    response = requests.get(SEARCH_URL, params={"q": query}, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for link in soup.select("a.result__a")[:max_results]:
        url = _unwrap_ddg_url(link.get("href"))
        if url:
            results.append({"title": link.get_text(strip=True), "url": url})
    return results


def _is_real_email(email: str) -> bool:
    local, _, domain = email.partition("@")
    if local in GENERIC_LOCAL_PARTS or domain in PLACEHOLDER_DOMAINS:
        return False
    extension = domain.rsplit(".", 1)[-1]
    return extension not in NON_EMAIL_EXTENSIONS


def _extract_emails(text: str) -> set[str]:
    found = {match.group(0).lower() for match in EMAIL_RE.finditer(text)}
    return {email for email in found if _is_real_email(email)}


def _extract_mailto_emails(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    emails = set()
    for link in soup.select('a[href^="mailto:"]'):
        address = link["href"][len("mailto:"):].split("?")[0].strip().lower()
        if address and _is_real_email(address):
            emails.add(address)
    return emails


def _is_skippable(url: str) -> bool:
    return any(domain in url for domain in SKIP_DOMAINS)


def _relevance_rank(candidate: dict) -> tuple:
    local_part = candidate["email"].split("@")[0]
    return (
        candidate.get("is_mailto", False),
        local_part in RELEVANT_LOCAL_PARTS,
    )


def find_candidate_emails(company: str) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    fetched_urls: set[str] = set()

    for query_template in SEARCH_QUERIES:
        if len(candidates) >= MAX_CANDIDATES:
            break

        try:
            results = search_web(query_template.format(company=company))
        except Exception as e:
            logger.warning(f"company_email: search failed for query '{query_template}': {e}")
            continue

        for result in results:
            for email in _extract_emails(result["title"]):
                if email not in seen:
                    seen.add(email)
                    candidates.append({
                        "email": email, "source": result["url"],
                        "context": result["title"], "is_mailto": False,
                    })

            if _is_skippable(result["url"]) or result["url"] in fetched_urls:
                continue
            if len(fetched_urls) >= MAX_PAGE_FETCHES:
                continue

            try:
                page = requests.get(result["url"], headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
                fetched_urls.add(result["url"])
            except Exception as e:
                logger.warning(f"company_email: failed to fetch {result['url']}: {e}")
                continue

            mailto_emails = _extract_mailto_emails(page.text)
            for email in mailto_emails:
                if email not in seen:
                    seen.add(email)
                    candidates.append({
                        "email": email, "source": result["url"],
                        "context": result["title"], "is_mailto": True,
                    })

            for email in _extract_emails(page.text):
                if email not in seen:
                    seen.add(email)
                    candidates.append({
                        "email": email, "source": result["url"],
                        "context": result["title"], "is_mailto": False,
                    })

            if len(candidates) >= MAX_CANDIDATES:
                break

    candidates.sort(key=_relevance_rank, reverse=True)
    return candidates


def choose_best_email(company: str, vacancy_title: str, candidates: list[dict]) -> EmailChoice:
    if not candidates:
        return EmailChoice(email=None, reasoning="No email candidates found")

    if len(candidates) == 1:
        return EmailChoice(email=candidates[0]["email"], reasoning="Only candidate found")

    listing = "\n".join(
        f"- {c['email']} (found on {c['source']}, context: {c['context']}, "
        f"from a mailto link: {c.get('is_mailto', False)})"
        for c in candidates
    )
    prompt = f"""A candidate is applying for the job "{vacancy_title}" at "{company}". Below are email \
addresses found while searching for this company's contact information, ranked with the most \
promising ones first (a mailto link on the company's own page is the strongest signal; addresses like \
rh@, vagas@, recrutamento@, carreiras@, or a "department=hr"/"department=recruiting" tag are also \
strong signals).

{listing}

Pick the single email most likely to be the right contact for a job application (HR, recruiting, \
or a general company contact). Do NOT pick a named individual's personal address (e.g. a CEO, \
director, or other executive/management contact) just because it has high confidence or belongs to \
the company - sending an unsolicited job application to a specific executive's personal inbox is \
inappropriate and not what a job seeker would do; only pick a personal address if it is explicitly \
labeled as HR/recruiting. Avoid personal-looking addresses unrelated to the company and avoid \
third-party sites unless they are clearly listing this company's own contact. If none of them look \
like a plausible fit, return null for email."""

    response = _client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=EmailChoice.model_json_schema(),
    )
    return EmailChoice.model_validate_json(response["message"]["content"])


def find_company_email(company: str, vacancy_title: str) -> str | None:
    if hunter_io.is_configured():
        hunter_candidates = hunter_io.search_company_emails(company)
        if hunter_candidates:
            logger.info(f"company_email: {len(hunter_candidates)} candidate(s) from hunter.io for {company}")
            choice = choose_best_email(company, vacancy_title, hunter_candidates)
            logger.info(f"company_email: chose {choice.email} for {company} (hunter.io) - {choice.reasoning}")
            if choice.email:
                return choice.email

    candidates = find_candidate_emails(company)
    logger.info(f"company_email: {len(candidates)} candidate(s) found via web search for {company}")

    choice = choose_best_email(company, vacancy_title, candidates)
    logger.info(f"company_email: chose {choice.email} for {company} - {choice.reasoning}")
    return choice.email
