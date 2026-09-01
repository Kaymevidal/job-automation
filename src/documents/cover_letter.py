import re
from pathlib import Path

from ollama import Client
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import COVER_LETTERS_DIR, OLLAMA_HOST, OLLAMA_MODEL
from src.core.constants import ApplicationStatus, MIN_COMPATIBILITY_SCORE
from src.core.logger import logger
from src.database.models import Application, User, Vacancy

_client = Client(host=OLLAMA_HOST)

PROMPT_TEMPLATE = """You are writing a professional cover letter on behalf of a job candidate.

Candidate profile:
{profile_summary}

They are applying for:
Title: {title}
Company: {company}
Job description:
{description}

Write a concise cover letter body (3-4 short paragraphs, under 300 words). Start with a \
salutation addressed to the hiring team at {company}. Do not include a letterhead, date, \
or contact block - just the letter body, ending with a closing line and the candidate's \
name, {name}.

Only state facts grounded in the candidate profile and job description above. Never insert \
placeholder text or bracketed instructions like "[mention X]" - if you lack a specific \
detail, write the sentence generically instead of leaving a placeholder."""

_BROKEN_MARKERS = ("[", "]", "{", "}")


def _looks_broken(text: str) -> bool:
    return any(marker in text for marker in _BROKEN_MARKERS)


def generate_cover_letter_text(user: User, vacancy: Vacancy) -> str:
    prompt = PROMPT_TEMPLATE.format(
        profile_summary=user.profile_summary,
        title=vacancy.title,
        company=vacancy.company,
        description=vacancy.description or "(no description provided)",
        name=user.name,
    )

    messages = [{"role": "user", "content": prompt}]
    for attempt in range(2):
        response = _client.chat(model=OLLAMA_MODEL, messages=messages, options={"temperature": 0.4})
        text = response["message"]["content"].strip()

        if not _looks_broken(text):
            return text

        logger.warning(f"Cover letter for vacancy {vacancy.id} looked broken on attempt {attempt + 1}, retrying")
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": text},
            {"role": "user", "content": "That contained placeholder brackets. Rewrite it with no "
                                         "brackets at all, using only generic phrasing where you "
                                         "lack a specific detail."},
        ]

    raise ValueError(f"Cover letter generation kept producing placeholder text for vacancy {vacancy.id}")


def _safe_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_")[:80]


def render_cover_letter_pdf(text: str, vacancy: Vacancy) -> Path:
    filename = f"{vacancy.id}_{_safe_filename(vacancy.company)}.pdf"
    output_path = COVER_LETTERS_DIR / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    story = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        story.append(Paragraph(paragraph.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 12))

    doc.build(story)
    return output_path


def generate_applications_for_top_matches(
    session: Session, user: User, min_score: float = MIN_COMPATIBILITY_SCORE
) -> int:
    candidates = session.execute(
        select(Vacancy).where(Vacancy.compatibility_score >= min_score)
    ).scalars().all()

    created = 0
    for vacancy in candidates:
        existing = session.execute(
            select(Application).where(
                Application.user_id == user.id,
                Application.vacancy_id == vacancy.id,
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        try:
            letter_text = generate_cover_letter_text(user, vacancy)
            pdf_path = render_cover_letter_pdf(letter_text, vacancy)
        except Exception as e:
            logger.error(f"Cover letter generation failed for vacancy {vacancy.id}: {e}")
            continue

        session.add(Application(
            user_id=user.id,
            vacancy_id=vacancy.id,
            status=ApplicationStatus.PENDING,
            cover_letter_path=str(pdf_path),
            cover_letter_text=letter_text,
            resume_used_path=user.resume_path,
        ))
        session.commit()
        created += 1
        logger.info(f"Application created for vacancy {vacancy.id} ({vacancy.title}), cover letter at {pdf_path}")

    logger.info(f"Created {created} applications from {len(candidates)} qualifying vacancies")
    return created
