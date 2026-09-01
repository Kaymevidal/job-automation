from ollama import Client
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import OLLAMA_HOST, OLLAMA_MODEL
from src.core.logger import logger
from src.database.models import User, Vacancy

_client = Client(host=OLLAMA_HOST)

PROMPT_TEMPLATE = """You are a recruiting assistant. Compare the candidate profile with the job \
posting below and judge how compatible they are.

Candidate profile:
{profile_summary}

Job title: {title}
Company: {company}
Job description:
{description}

Score compatibility from 0.0 (no match) to 1.0 (excellent match), considering \
skills, seniority, and domain overlap. Respond with the score and a short \
reasoning in one or two sentences."""


class CompatibilityResult(BaseModel):
    score: float = Field(ge=0, le=1)
    reasoning: str


def score_compatibility(profile_summary: str, vacancy: Vacancy) -> CompatibilityResult:
    prompt = PROMPT_TEMPLATE.format(
        profile_summary=profile_summary,
        title=vacancy.title,
        company=vacancy.company,
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
    for vacancy in pending:
        try:
            result = score_compatibility(user.profile_summary, vacancy)
        except Exception as e:
            logger.error(f"Scoring failed for vacancy {vacancy.id}: {e}")
            continue

        vacancy.compatibility_score = result.score
        session.commit()
        scored += 1
        logger.info(f"Vacancy {vacancy.id} ({vacancy.title}): score={result.score:.2f} - {result.reasoning}")

    logger.info(f"Scored {scored} of {len(pending)} pending vacancies")
    return scored
