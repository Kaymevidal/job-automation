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

from src.core.constants import ScraperSource
from src.database.database import get_session
from src.database.models import Vacancy
from src.gui.search_worker import SearchWorker

COLUMNS = ["Titulo", "Empresa", "Local", "Fonte", "Score", "Abrir"]
COLUMN_WIDTHS = {2: 160, 3: 100, 4: 70, 5: 85}

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

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(self.search_edit, 1)
        filter_bar.addWidget(self.search_button)
        filter_bar.addWidget(self.source_combo)
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

        self.refresh()

    def refresh(self) -> None:
        with get_session() as session:
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

            min_score = self.min_score_combo.currentData()
            if min_score is not None:
                query = query.where(Vacancy.compatibility_score >= min_score)

            query = query.order_by(Vacancy.compatibility_score.desc().nullslast(), Vacancy.scraped_at.desc())
            vacancies = session.execute(query).scalars().all()

            self.table.setRowCount(len(vacancies))
            for row, vacancy in enumerate(vacancies):
                score = f"{vacancy.compatibility_score:.2f}" if vacancy.compatibility_score is not None else "-"
                source_label = SOURCE_LABELS.get(vacancy.source, vacancy.source.value)
                values = [vacancy.title, vacancy.company, vacancy.location or "-", source_label, score]
                for col, value in enumerate(values):
                    self.table.setItem(row, col, QTableWidgetItem(value))

                open_button = QPushButton("Abrir")
                open_button.clicked.connect(lambda _checked, url=vacancy.url: QDesktopServices.openUrl(QUrl(url)))
                self.table.setCellWidget(row, len(COLUMNS) - 1, open_button)

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
