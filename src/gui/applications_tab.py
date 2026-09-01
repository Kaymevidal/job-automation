import os

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from src.core.constants import ApplicationStatus
from src.database.database import get_session
from src.database.models import Application, User, Vacancy

COLUMNS = ["Vaga", "Empresa", "Score", "Status", "Carta", "E-mail"]


class ApplicationsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(2, len(COLUMNS)):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            rows = session.execute(
                select(Application, Vacancy)
                .join(Vacancy, Application.vacancy_id == Vacancy.id)
                .order_by(Application.created_at.desc())
            ).all()

            self.table.setRowCount(len(rows))
            for row, (application, vacancy) in enumerate(rows):
                score = f"{vacancy.compatibility_score:.2f}" if vacancy.compatibility_score is not None else "-"
                self.table.setItem(row, 0, QTableWidgetItem(vacancy.title))
                self.table.setItem(row, 1, QTableWidgetItem(vacancy.company))
                self.table.setItem(row, 2, QTableWidgetItem(score))

                status_combo = QComboBox()
                status_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
                status_combo.addItems([status.value for status in ApplicationStatus])
                status_combo.setCurrentText(application.status.value)
                status_combo.currentTextChanged.connect(
                    lambda value, app_id=application.id: self._update_status(app_id, value)
                )
                self.table.setCellWidget(row, 3, status_combo)

                if application.cover_letter_path:
                    letter_button = QPushButton("Abrir PDF")
                    letter_button.clicked.connect(
                        lambda _checked, path=application.cover_letter_path: self._open_file(path)
                    )
                    self.table.setCellWidget(row, 4, letter_button)
                else:
                    self.table.setItem(row, 4, QTableWidgetItem("-"))

                email_label = "Rascunho criado" if application.email_drafted_at else "Criar rascunho"
                email_button = QPushButton(email_label)
                email_button.clicked.connect(
                    lambda _checked, app_id=application.id: self._draft_email(app_id)
                )
                self.table.setCellWidget(row, 5, email_button)

            self.table.resizeColumnsToContents()

    def _update_status(self, application_id: int, status_value: str) -> None:
        with get_session() as session:
            application = session.get(Application, application_id)
            application.status = ApplicationStatus(status_value)

    def _draft_email(self, application_id: int) -> None:
        with get_session() as session:
            application = session.get(Application, application_id)
            vacancy = session.get(Vacancy, application.vacancy_id)
            user = session.get(User, application.user_id)

            to_email = vacancy.contact_email
            if not to_email:
                to_email, ok = QInputDialog.getText(
                    self, "E-mail de contato", f"E-mail para candidatura em {vacancy.company}:"
                )
                if not ok or not to_email.strip():
                    return
                to_email = to_email.strip()
                vacancy.contact_email = to_email

            try:
                from src.integrations.outlook import draft_application_email
                draft_application_email(application, vacancy, user, to_email)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao criar rascunho", str(e))
                return

        self.refresh()

    @staticmethod
    def _open_file(path: str) -> None:
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
