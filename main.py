# main.py

import sys

from PySide6.QtWidgets import QApplication

from database.db import init_db
from ui.main_window import MainWindow


def main():
    """
    Application entry point.
    """
    init_db()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()