from PyQt6.QtCore import QThread, pyqtSignal
from sqlalchemy import select

from src.database.database import get_session
from src.database.models import User
from src.scoring.compatibility import score_pending_vacancies
from src.scrapers import sync_all


class PipelineWorker(QThread):
    log = pyqtSignal(str)
    finished_ok = pyqtSignal(bool, str)

    def run(self) -> None:
        try:
            with get_session() as session:
                synced = sync_all(session)
            self.log.emit(f"{synced} vagas novas sincronizadas")

            with get_session() as session:
                users = session.execute(select(User)).scalars().all()

            if not users:
                self.log.emit("Nenhum perfil cadastrado, pulando pontuacao")
                self.finished_ok.emit(True, "Pipeline concluido")
                return

            for user in users:
                with get_session() as session:
                    user = session.get(User, user.id)
                    scored = score_pending_vacancies(session, user)
                self.log.emit(f"{scored} vagas pontuadas para {user.name}")

            self.finished_ok.emit(True, "Pipeline concluido")
        except Exception as e:
            self.finished_ok.emit(False, str(e))
