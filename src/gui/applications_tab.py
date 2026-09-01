import os

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from src.core.constants import ApplicationStatus
from src.database.database import get_session
from src.database.models import Application, Vacancy
from src.gui.email_draft_controller import EmailDraftController

COLUMNS = ["Vaga", "Empresa", "Score", "Status", "E-mail", "Carta", "Rascunho"]
COLUMN_WIDTHS = {2: 70, 3: 130, 4: 190, 5: 100, 6: 160}


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
        for col, width in COLUMN_WIDTHS.items():
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(col, width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.table)

        self._draft_controller = EmailDraftController(self)
        self._draft_controller.finished.connect(lambda _success: self.refresh())

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

                self.table.setItem(row, 4, QTableWidgetItem(vacancy.contact_email or "-"))

                if application.cover_letter_path:
                    letter_button = QPushButton("Abrir PDF")
                    letter_button.clicked.connect(
                        lambda _checked, path=application.cover_letter_path: self._open_file(path)
                    )
                    self.table.setCellWidget(row, 5, letter_button)
                else:
                    self.table.setItem(row, 5, QTableWidgetItem("-"))

                email_label = "Rascunho criado" if application.email_drafted_at else "Criar rascunho"
                email_button = QPushButton(email_label)
                email_button.clicked.connect(
                    lambda _checked, app_id=application.id: self._draft_email(app_id)
                )
                self.table.setCellWidget(row, 6, email_button)

            for col, width in COLUMN_WIDTHS.items():
                self.table.setColumnWidth(col, width)

    def _update_status(self, application_id: int, status_value: str) -> None:
        with get_session() as session:
            application = session.get(Application, application_id)
            application.status = ApplicationStatus(status_value)

    def _draft_email(self, application_id: int) -> None:
        button = self.sender()
        self._draft_controller.start(application_id, button if isinstance(button, QPushButton) else None)

    @staticmethod
    def _open_file(path: str) -> None:
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
