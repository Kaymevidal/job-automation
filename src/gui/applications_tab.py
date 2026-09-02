import os

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from src.core.config import TAILORED_RESUMES_DIR
from src.core.constants import ApplicationStatus
from src.database.database import get_session
from src.database.models import Application, User, Vacancy
from src.gui.resume_worker import ResumeWorker

COLUMNS = ["Vaga", "Empresa", "Score", "Status", "Curriculo"]
COLUMN_WIDTHS = {2: 70, 3: 130, 4: 130}


def _is_tailored(resume_used_path: str | None) -> bool:
    if not resume_used_path:
        return False
    return str(TAILORED_RESUMES_DIR) in resume_used_path


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

        self._resume_workers: list[ResumeWorker] = []

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

                resume_button = QPushButton()
                if _is_tailored(application.resume_used_path):
                    resume_button.setText("Abrir CV")
                    resume_button.clicked.connect(
                        lambda _checked, path=application.resume_used_path: self._open_file(path)
                    )
                else:
                    resume_button.setText("Gerar Curriculo")
                    resume_button.clicked.connect(
                        lambda _checked, app_id=application.id: self._generate_resume(app_id)
                    )
                self.table.setCellWidget(row, 4, resume_button)

            for col, width in COLUMN_WIDTHS.items():
                self.table.setColumnWidth(col, width)

    def _update_status(self, application_id: int, status_value: str) -> None:
        with get_session() as session:
            application = session.get(Application, application_id)
            application.status = ApplicationStatus(status_value)

    def _generate_resume(self, application_id: int) -> None:
        button = self.sender()

        with get_session() as session:
            application = session.get(Application, application_id)
            user = session.get(User, application.user_id)
            if not user.profile_summary:
                QMessageBox.warning(
                    self, "Perfil incompleto", "Preencha o resumo do perfil antes de gerar o curriculo."
                )
                return

        if isinstance(button, QPushButton):
            button.setEnabled(False)
            button.setText("Gerando...")

        worker = ResumeWorker(application_id)
        worker.finished_ok.connect(
            lambda success, message, btn=button: self._on_resume_ready(success, message, btn)
        )
        self._resume_workers.append(worker)
        worker.start()

    def _on_resume_ready(self, success: bool, message: str, button: QPushButton | None) -> None:
        if not success:
            if isinstance(button, QPushButton):
                button.setEnabled(True)
                button.setText("Gerar Curriculo")
            QMessageBox.critical(self, "Erro ao gerar curriculo", message)
            return

        self.refresh()

    @staticmethod
    def _open_file(path: str) -> None:
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
