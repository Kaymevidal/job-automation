from PyQt6.QtCore import QThread, pyqtSignal

from src.integrations.company_email import find_company_email


class EmailLookupWorker(QThread):
    finished_ok = pyqtSignal(str)

    def __init__(self, company: str, vacancy_title: str) -> None:
        super().__init__()
        self.company = company
        self.vacancy_title = vacancy_title

    def run(self) -> None:
        try:
            email = find_company_email(self.company, self.vacancy_title)
        except Exception:
            email = None
        self.finished_ok.emit(email or "")
