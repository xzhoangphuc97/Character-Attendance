from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Game Attendance Manager")
        self.resize(1200, 800)

        self.selected_image = None

        self.init_ui()

    def init_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_select = QPushButton("Chọn ảnh")
        self.btn_ocr = QPushButton("OCR & Điểm Danh")

        button_layout.addWidget(self.btn_select)
        button_layout.addWidget(self.btn_ocr)

        main_layout.addLayout(button_layout)

        # Preview + OCR
        content_layout = QHBoxLayout()

        self.image_label = QLabel("No image")
        self.image_label.setFixedSize(500, 300)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "border:1px solid gray;"
        )

        self.ocr_result = QTextEdit()

        content_layout.addWidget(self.image_label)
        content_layout.addWidget(self.ocr_result)

        main_layout.addLayout(content_layout)

        # Result table
        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Tên nhân vật",
                "Trạng thái",
                "Ghi chú"
            ]
        )

        main_layout.addWidget(self.table)

        self.btn_select.clicked.connect(
            self.select_image
        )

    def select_image(self):

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file_name:

            self.selected_image = file_name

            pixmap = QPixmap(file_name)

            pixmap = pixmap.scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio
            )

            self.image_label.setPixmap(pixmap)