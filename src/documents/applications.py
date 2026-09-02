from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.constants import ApplicationStatus
from src.core.logger import logger
from src.database.models import Application, User, Vacancy


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
