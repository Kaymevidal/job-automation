from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QPushButton, QWidget

from src.database.database import get_session
from src.database.models import Application, User, Vacancy
from src.gui.email_lookup_worker import EmailLookupWorker


class EmailDraftController(QObject):
    finished = pyqtSignal(bool)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self._workers: list[EmailLookupWorker] = []

    def start(self, application_id: int, trigger_button: QPushButton | None = None) -> None:
        with get_session() as session:
            vacancy = session.get(Vacancy, session.get(Application, application_id).vacancy_id)
            company = vacancy.company
            title = vacancy.title
            existing_email = vacancy.contact_email

        if existing_email:
            self._confirm_and_draft(application_id, existing_email)
            return

        if isinstance(trigger_button, QPushButton):
            trigger_button.setEnabled(False)
            trigger_button.setText("Buscando e-mail...")

        worker = EmailLookupWorker(company, title)
        worker.finished_ok.connect(
            lambda email, app_id=application_id, btn=trigger_button: self._on_email_found(app_id, email, btn)
        )
        self._workers.append(worker)
        worker.start()

    def _on_email_found(self, application_id: int, email: str, button: QPushButton | None) -> None:
        if isinstance(button, QPushButton):
            button.setEnabled(True)
            button.setText("Criar rascunho")

        self._confirm_and_draft(application_id, email)

    def _confirm_and_draft(self, application_id: int, suggested_email: str) -> None:
        with get_session() as session:
            application = session.get(Application, application_id)
            vacancy = session.get(Vacancy, application.vacancy_id)
            user = session.get(User, application.user_id)

            to_email, ok = QInputDialog.getText(
                self._parent,
                "E-mail de contato",
                f"E-mail para candidatura em {vacancy.company}:"
                + ("" if suggested_email else "\n(nao encontrado automaticamente, digite manualmente)"),
                text=suggested_email,
            )
            if not ok or not to_email.strip():
                self.finished.emit(False)
                return
            to_email = to_email.strip()
            vacancy.contact_email = to_email

            try:
                from src.integrations.outlook import draft_application_email
                draft_application_email(application, vacancy, user, to_email)
            except Exception as e:
                QMessageBox.critical(self._parent, "Erro ao criar rascunho", str(e))
                self.finished.emit(False)
                return

        self.finished.emit(True)
