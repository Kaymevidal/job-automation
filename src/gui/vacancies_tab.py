from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import or_, select

from src.core.constants import ScraperSource, WorkMode
from src.database.database import get_session
from src.database.models import Application, User, Vacancy
from src.documents.cover_letter import get_or_create_application
from src.gui.cover_letter_worker import CoverLetterWorker
from src.gui.email_draft_controller import EmailDraftController
from src.gui.search_worker import SearchWorker

COLUMNS = ["Titulo", "Empresa", "Local", "Modalidade", "Fonte", "Score", "Abrir", "Candidatura", "Rascunho"]
COLUMN_WIDTHS = {2: 150, 3: 100, 4: 100, 5: 70, 6: 85, 7: 140, 8: 160}

SOURCE_LABELS = {
    ScraperSource.REMOTEOK: "RemoteOK",
    ScraperSource.VAGAS_COM_BR: "Vagas.com",
    ScraperSource.INFOJOBS: "InfoJobs",
    ScraperSource.CATHO: "Catho",
    ScraperSource.LINKEDIN: "LinkedIn",
    ScraperSource.INDEED: "Indeed",
    ScraperSource.GLASSDOOR: "Glassdoor",
    ScraperSource.MANUAL: "Manual",
}

WORK_MODE_LABELS = {
    WorkMode.REMOTE: "Remoto",
    WorkMode.HYBRID: "Hibrido",
    WorkMode.ONSITE: "Presencial",
}

SCORE_FILTERS = [
    ("Qualquer score", None),
    (">= 0.9", 0.9),
    (">= 0.8", 0.8),
    (">= 0.7", 0.7),
    (">= 0.6", 0.6),
    (">= 0.5", 0.5),
]


class VacanciesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.search_worker: SearchWorker | None = None

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por titulo, empresa ou local...")
        self.search_edit.textChanged.connect(self.refresh)
        self.search_edit.returnPressed.connect(self._search_online)

        self.search_button = QPushButton("Buscar Online")
        self.search_button.clicked.connect(self._search_online)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Todas as fontes", None)
        for source, label in SOURCE_LABELS.items():
            self.source_combo.addItem(label, source)
        self.source_combo.currentIndexChanged.connect(self.refresh)

        self.min_score_combo = QComboBox()
        for label, value in SCORE_FILTERS:
            self.min_score_combo.addItem(label, value)
        self.min_score_combo.currentIndexChanged.connect(self.refresh)

        self.work_mode_combo = QComboBox()
        self.work_mode_combo.addItem("Qualquer modalidade", None)
        for mode, label in WORK_MODE_LABELS.items():
            self.work_mode_combo.addItem(label, mode)
        self.work_mode_combo.currentIndexChanged.connect(self.refresh)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(self.search_edit, 1)
        filter_bar.addWidget(self.search_button)
        filter_bar.addWidget(self.source_combo)
        filter_bar.addWidget(self.work_mode_combo)
        filter_bar.addWidget(self.min_score_combo)

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
        layout.setSpacing(10)
        layout.addLayout(filter_bar)
        layout.addWidget(self.table)

        self._draft_controller = EmailDraftController(self)
        self._draft_controller.finished.connect(lambda _success: self.refresh())
        self._cover_letter_workers: list[CoverLetterWorker] = []

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            user = session.execute(select(User)).scalars().first()
            applied_vacancy_ids = set()
            if user is not None:
                applied_vacancy_ids = set(
                    session.execute(
                        select(Application.vacancy_id).where(Application.user_id == user.id)
                    ).scalars().all()
                )

            query = select(Vacancy)

            search_text = self.search_edit.text().strip()
            if search_text:
                like = f"%{search_text}%"
                query = query.where(
                    or_(
                        Vacancy.title.ilike(like),
                        Vacancy.company.ilike(like),
                        Vacancy.location.ilike(like),
                    )
                )

            source = self.source_combo.currentData()
            if source is not None:
                query = query.where(Vacancy.source == source)

            work_mode = self.work_mode_combo.currentData()
            if work_mode is not None:
                query = query.where(Vacancy.work_mode == work_mode)

            min_score = self.min_score_combo.currentData()
            if min_score is not None:
                query = query.where(Vacancy.compatibility_score >= min_score)

            query = query.order_by(Vacancy.compatibility_score.desc().nullslast(), Vacancy.scraped_at.desc())
            vacancies = session.execute(query).scalars().all()

            self.table.setRowCount(len(vacancies))
            for row, vacancy in enumerate(vacancies):
                score = f"{vacancy.compatibility_score:.2f}" if vacancy.compatibility_score is not None else "-"
                source_label = SOURCE_LABELS.get(vacancy.source, vacancy.source.value)
                mode_label = WORK_MODE_LABELS.get(vacancy.work_mode, "-")
                values = [vacancy.title, vacancy.company, vacancy.location or "-", mode_label, source_label, score]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, QTableWidgetItem(value))

                open_button = QPushButton("Abrir")
                open_button.clicked.connect(lambda _checked, url=vacancy.url: QDesktopServices.openUrl(QUrl(url)))
                self.table.setCellWidget(row, 6, open_button)

                already_applied = vacancy.id in applied_vacancy_ids

                apply_button = QPushButton("Ja adicionada" if already_applied else "+ Candidatura")
                apply_button.setEnabled(user is not None and not already_applied)
                apply_button.clicked.connect(
                    lambda _checked, vacancy_id=vacancy.id: self._add_to_applications(vacancy_id)
                )
                self.table.setCellWidget(row, 7, apply_button)

                draft_button = QPushButton("Gerar Rascunho")
                draft_button.setEnabled(user is not None)
                draft_button.clicked.connect(
                    lambda _checked, vacancy_id=vacancy.id: self._generate_draft(vacancy_id)
                )
                self.table.setCellWidget(row, 8, draft_button)

            for col, width in COLUMN_WIDTHS.items():
                self.table.setColumnWidth(col, width)

    def _search_online(self) -> None:
        term = self.search_edit.text().strip()
        if not term:
            return

        if self.search_worker is not None and self.search_worker.isRunning():
            return

        self.search_button.setEnabled(False)
        self.search_button.setText("Buscando...")

        self.search_worker = SearchWorker(term)
        self.search_worker.finished_ok.connect(self._on_search_finished)
        self.search_worker.start()

    def _on_search_finished(self, success: bool, message: str, created: int) -> None:
        self.search_button.setEnabled(True)
        self.search_button.setText("Buscar Online")

        if success:
            self.refresh()
        else:
            QMessageBox.warning(self, "Erro na busca", message)

    def _add_to_applications(self, vacancy_id: int) -> None:
        button = self.sender()

        with get_session() as session:
            user = session.execute(select(User)).scalars().first()
            if user is None:
                QMessageBox.warning(self, "Sem perfil", "Cadastre seu perfil na aba Perfil primeiro.")
                return

            vacancy = session.get(Vacancy, vacancy_id)
            get_or_create_application(session, user, vacancy)

        if isinstance(button, QPushButton):
            button.setText("Ja adicionada")
            button.setEnabled(False)

    def _generate_draft(self, vacancy_id: int) -> None:
        button = self.sender()

        with get_session() as session:
            user = session.execute(select(User)).scalars().first()
            if user is None:
                QMessageBox.warning(self, "Sem perfil", "Cadastre seu perfil na aba Perfil primeiro.")
                return
            if not user.profile_summary:
                QMessageBox.warning(self, "Perfil incompleto", "Preencha o resumo do perfil antes de gerar a carta.")
                return

            vacancy = session.get(Vacancy, vacancy_id)
            application = get_or_create_application(session, user, vacancy)
            application_id = application.id
            has_letter = bool(application.cover_letter_text)

        if isinstance(button, QPushButton):
            button.setEnabled(False)
            button.setText("Gerando carta...")

        if has_letter:
            self._on_cover_letter_ready(True, "", application_id, button)
            return

        worker = CoverLetterWorker(application_id)
        worker.finished_ok.connect(
            lambda success, message, app_id=application_id, btn=button:
            self._on_cover_letter_ready(success, message, app_id, btn)
        )
        self._cover_letter_workers.append(worker)
        worker.start()

    def _on_cover_letter_ready(
        self, success: bool, message: str, application_id: int, button: QPushButton | None
    ) -> None:
        if not success:
            if isinstance(button, QPushButton):
                button.setEnabled(True)
                button.setText("Gerar Rascunho")
            QMessageBox.critical(self, "Erro ao gerar carta", message)
            return

        self._draft_controller.start(application_id, button)
