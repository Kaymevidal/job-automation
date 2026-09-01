from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from sqlalchemy import select

from src.core.constants import ScraperSource
from src.database.database import get_session
from src.database.models import Vacancy

COLUMNS = ["Titulo", "Empresa", "Local", "Fonte", "Score", "Abrir"]

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


class VacanciesTab(QWidget):
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
            vacancies = session.execute(
                select(Vacancy).order_by(Vacancy.compatibility_score.desc().nullslast(), Vacancy.scraped_at.desc())
            ).scalars().all()

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

            self.table.resizeColumnsToContents()
