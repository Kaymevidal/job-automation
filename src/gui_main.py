import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.core.logger import log_startup
from src.database.migrations import run_migrations
from src.gui.main_window import MainWindow

STYLE_PATH = Path(__file__).resolve().parent / "gui" / "style.qss"


def main() -> int:
    log_startup()
    run_migrations()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
