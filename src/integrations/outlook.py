from datetime import datetime, timezone
from pathlib import Path

import win32com.client

from src.core.logger import logger
from src.database.models import Application, User, Vacancy

OL_MAIL_ITEM = 0


def create_draft_email(to_email: str, subject: str, body: str, attachments: list[str | None]) -> None:
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(OL_MAIL_ITEM)

    mail.To = to_email
    mail.Subject = subject
    mail.Body = body

    for attachment in attachments:
        if not attachment:
            continue
        path = Path(attachment)
        if not path.exists():
            logger.warning(f"Attachment not found, skipping: {path}")
            continue
        mail.Attachments.Add(str(path.resolve()))

    mail.Display()


def draft_application_email(application: Application, vacancy: Vacancy, user: User, to_email: str) -> None:
    subject = f"Application for {vacancy.title} at {vacancy.company}"
    body = application.cover_letter_text or (
        f"Dear Hiring Team,\n\nPlease find attached my resume and cover letter for the "
        f"{vacancy.title} position.\n\nBest regards,\n{user.name}"
    )

    create_draft_email(
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=[application.cover_letter_path, application.resume_used_path],
    )

    application.email_drafted_at = datetime.now(timezone.utc)
