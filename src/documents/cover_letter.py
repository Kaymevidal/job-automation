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
from src.documents.resume_tailor import tailor_resume_for_application
from src.documents.utils import looks_broken, safe_filename

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

        if not looks_broken(text):
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


def render_cover_letter_pdf(text: str, vacancy: Vacancy) -> Path:
    filename = f"{vacancy.id}_{safe_filename(vacancy.company)}.pdf"
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


def get_or_create_application(session: Session, user: User, vacancy: Vacancy) -> Application:
    existing = session.execute(
        select(Application).where(
            Application.user_id == user.id,
            Application.vacancy_id == vacancy.id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        return existing

    application = Application(
        user_id=user.id,
        vacancy_id=vacancy.id,
        status=ApplicationStatus.PENDING,
        resume_used_path=user.resume_path,
    )
    session.add(application)
    session.commit()
    logger.info(f"Application created for vacancy {vacancy.id} ({vacancy.title})")
    return application


def generate_cover_letter_for_application(session: Session, application: Application) -> None:
    user = session.get(User, application.user_id)
    vacancy = session.get(Vacancy, application.vacancy_id)

    letter_text = generate_cover_letter_text(user, vacancy)
    pdf_path = render_cover_letter_pdf(letter_text, vacancy)

    application.cover_letter_path = str(pdf_path)
    application.cover_letter_text = letter_text
    session.commit()
    logger.info(f"Cover letter generated for application {application.id}, vacancy {vacancy.id}")

    try:
        tailor_resume_for_application(session, application)
    except Exception as e:
        logger.error(f"Resume tailoring failed for application {application.id}: {e}")


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

        application = get_or_create_application(session, user, vacancy)

        try:
            generate_cover_letter_for_application(session, application)
        except Exception as e:
            logger.error(f"Cover letter generation failed for vacancy {vacancy.id}: {e}")
            session.delete(application)
            session.commit()
            continue

        created += 1

    logger.info(f"Created {created} applications from {len(candidates)} qualifying vacancies")
    return created
