from PyQt6.QtCore import QThread, pyqtSignal

from src.database.database import get_session
from src.database.models import Application
from src.documents.cover_letter import generate_cover_letter_for_application


class CoverLetterWorker(QThread):
    finished_ok = pyqtSignal(bool, str)

    def __init__(self, application_id: int) -> None:
        super().__init__()
        self.application_id = application_id

    def run(self) -> None:
        try:
            with get_session() as session:
                application = session.get(Application, self.application_id)
                generate_cover_letter_for_application(session, application)
            self.finished_ok.emit(True, "")
        except Exception as e:
            self.finished_ok.emit(False, str(e))
