# main.py

import sys

from PySide6.QtWidgets import QApplication

from database.db import init_db
from services.license_service import initialize_trial_if_needed
from ui.main_window import MainWindow


def main():
    """
    Application entry point.
    """
    init_db()
    initialize_trial_if_needed()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()