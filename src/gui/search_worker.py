from PyQt6.QtCore import QThread, pyqtSignal

from src.database.database import get_session
from src.scrapers import sync_all


DEEP_SEARCH_PAGES = 3


class SearchWorker(QThread):
    finished_ok = pyqtSignal(bool, str, int)

    def __init__(self, query: str, pages: int = DEEP_SEARCH_PAGES) -> None:
        super().__init__()
        self.query = query
        self.pages = pages

    def run(self) -> None:
        try:
            with get_session() as session:
                created = sync_all(session, self.query, pages=self.pages)
            self.finished_ok.emit(True, "Busca concluida", created)
        except Exception as e:
            self.finished_ok.emit(False, str(e), 0)
