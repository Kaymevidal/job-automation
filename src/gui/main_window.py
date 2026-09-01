from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QVBoxLayout, QWidget

from src.core.config import APP_NAME
from src.gui.applications_tab import ApplicationsTab
from src.gui.pipeline import PipelineWorker
from src.gui.profile_tab import ProfileTab
from src.gui.vacancies_tab import VacanciesTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1000, 700)

        self.vacancies_tab = VacanciesTab()
        self.applications_tab = ApplicationsTab()
        self.profile_tab = ProfileTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.vacancies_tab, "Vagas")
        self.tabs.addTab(self.applications_tab, "Candidaturas")
        self.tabs.addTab(self.profile_tab, "Perfil")

        self.run_button = QPushButton("Buscar e Processar Vagas")
        self.run_button.clicked.connect(self._run_pipeline)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(500)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.log_output)
        splitter.setSizes([550, 150])

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.run_button)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self.worker: PipelineWorker | None = None

    def _run_pipeline(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return

        self.run_button.setEnabled(False)
        self.log_output.appendPlainText("Iniciando pipeline...")

        self.worker = PipelineWorker()
        self.worker.log.connect(self.log_output.appendPlainText)
        self.worker.finished_ok.connect(self._on_pipeline_finished)
        self.worker.start()

    def _on_pipeline_finished(self, success: bool, message: str) -> None:
        self.log_output.appendPlainText(message)
        self.run_button.setEnabled(True)

        self.vacancies_tab.refresh()
        self.applications_tab.refresh()

        if not success:
            QMessageBox.warning(self, "Erro no pipeline", message)
