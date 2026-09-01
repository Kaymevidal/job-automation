import re

from ollama import Client
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import OLLAMA_HOST, OLLAMA_MODEL
from src.core.constants import WorkMode
from src.core.logger import logger
from src.database.models import User, Vacancy

_client = Client(host=OLLAMA_HOST)

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}")
_STOPWORDS = {
    "and", "or", "the", "with", "for", "in", "of", "a", "an", "to", "on",
    "using", "experience", "years", "year", "work", "working", "team",
}


def _keywords(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def is_plausible_match(profile_summary: str, vacancy: Vacancy) -> bool:
    profile_keywords = _keywords(profile_summary)
    vacancy_keywords = _keywords(vacancy.title) | _keywords(vacancy.tags or "")
    return bool(profile_keywords & vacancy_keywords)

PROMPT_TEMPLATE = """You are a recruiting assistant. Compare the candidate profile with the job \
posting below and judge how compatible they are.

Candidate profile:
{profile_summary}

Job title: {title}
Company: {company}
Location: {location}
Job description:
{description}

Score compatibility from 0.0 (no match) to 1.0 (excellent match), considering \
skills, seniority, and domain overlap. Respond with the score and a short \
reasoning in one or two sentences.

Also classify the work mode as one of: "remote" (fully remote, home office, no \
commute required), "hybrid" (mix of remote and in-office, e.g. explicitly says \
hybrid or a number of in-office days per week), or "onsite" (fully in-person, \
no remote work mentioned). Base this only on explicit statements in the title, \
location, or description - if the posting gives no indication either way, \
default to "onsite" since that is the norm on these job boards."""


class CompatibilityResult(BaseModel):
    score: float = Field(ge=0, le=1)
    reasoning: str
    work_mode: WorkMode


def score_compatibility(profile_summary: str, vacancy: Vacancy) -> CompatibilityResult:
    prompt = PROMPT_TEMPLATE.format(
        profile_summary=profile_summary,
        title=vacancy.title,
        company=vacancy.company,
        location=vacancy.location or "(not provided)",
        description=vacancy.description or "(no description provided)",
    )

    response = _client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=CompatibilityResult.model_json_schema(),
    )

    return CompatibilityResult.model_validate_json(response["message"]["content"])


def score_pending_vacancies(session: Session, user: User, limit: int = 20) -> int:
    if not user.profile_summary:
        logger.warning(f"User {user.id} has no profile_summary, skipping scoring")
        return 0

    pending = session.execute(
        select(Vacancy).where(Vacancy.compatibility_score.is_(None)).limit(limit)
    ).scalars().all()

    scored = 0
    filtered_out = 0
    for vacancy in pending:
        if not is_plausible_match(user.profile_summary, vacancy):
            vacancy.compatibility_score = 0.0
            session.commit()
            filtered_out += 1
            logger.info(f"Vacancy {vacancy.id} ({vacancy.title}): pre-filtered, no keyword overlap")
            continue

        try:
            result = score_compatibility(user.profile_summary, vacancy)
        except Exception as e:
            logger.error(f"Scoring failed for vacancy {vacancy.id}: {e}")
            continue

        vacancy.compatibility_score = result.score
        vacancy.work_mode = result.work_mode
        session.commit()
        scored += 1
        logger.info(
            f"Vacancy {vacancy.id} ({vacancy.title}): score={result.score:.2f}, "
            f"work_mode={result.work_mode.value} - {result.reasoning}"
        )

    logger.info(f"Scored {scored} and pre-filtered {filtered_out} of {len(pending)} pending vacancies")
    return scored
