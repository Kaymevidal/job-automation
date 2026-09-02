from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
from src.database.models import User, Vacancy
from src.documents.applications import get_or_create_application
from src.gui.search_worker import SearchWorker
from src.gui.vacancy_detail_dialog import VacancyDetailDialog

COLUMNS = ["Titulo", "Empresa", "Local", "Modalidade", "Fonte", "Score", "Detalhes", "Abrir"]
COLUMN_WIDTHS = {2: 150, 3: 100, 4: 100, 5: 70, 6: 90, 7: 85}

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

        self.show_duplicates_check = QCheckBox("Mostrar duplicatas")
        self.show_duplicates_check.stateChanged.connect(self.refresh)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(self.search_edit, 1)
        filter_bar.addWidget(self.search_button)
        filter_bar.addWidget(self.source_combo)
        filter_bar.addWidget(self.work_mode_combo)
        filter_bar.addWidget(self.min_score_combo)
        filter_bar.addWidget(self.show_duplicates_check)

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

        self._detail_dialog: VacancyDetailDialog | None = None

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
            query = select(Vacancy)

            if not self.show_duplicates_check.isChecked():
                query = query.where(Vacancy.duplicate_of_id.is_(None))

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

                details_button = QPushButton("Ver mais")
                details_button.clicked.connect(
                    lambda _checked, vacancy_id=vacancy.id: self._show_details(vacancy_id)
                )
                self.table.setCellWidget(row, 6, details_button)

                open_button = QPushButton("Abrir")
                open_button.clicked.connect(
                    lambda _checked, vacancy_id=vacancy.id, url=vacancy.url: self._open_vacancy(vacancy_id, url)
                )
                self.table.setCellWidget(row, 7, open_button)

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

    def _show_details(self, vacancy_id: int) -> None:
        with get_session() as session:
            vacancy = session.get(Vacancy, vacancy_id)
            self._detail_dialog = VacancyDetailDialog(vacancy, self)
        self._detail_dialog.exec()

    def _open_vacancy(self, vacancy_id: int, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

        with get_session() as session:
            user = session.execute(select(User)).scalars().first()
            if user is None:
                return

            vacancy = session.get(Vacancy, vacancy_id)
            get_or_create_application(session, user, vacancy)
