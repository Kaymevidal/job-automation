import sys

from PyQt6.QtWidgets import QApplication

from src.core.logger import log_startup
from src.database.migrations import run_migrations
from src.gui.main_window import MainWindow


def main() -> int:
    log_startup()
    run_migrations()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
