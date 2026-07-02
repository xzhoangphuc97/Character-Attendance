# ui/main_window.py

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.attendance_service import save_attendance
from services.ocr_service import extract_member_names


class MainWindow(QMainWindow):
    """
    Main window for Character Attendance application.

    Features:
        - Select one game screenshot image.
        - Preview selected image.
        - Detect guild member names from image.
        - Save attendance records into SQLite database.
        - Skip check-in if latest check-in is less than 1 hour.
        - Show OCR result and processing result in UI.
    """

    def __init__(self):
        super().__init__()

        self.selected_image = None

        self.setWindowTitle("Character Attendance")
        self.resize(1200, 750)

        self.build_ui()

    def build_ui(self):
        """
        Build main UI layout.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title = QLabel("Character Attendance")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            """
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
            }
            """
        )

        main_layout.addWidget(title)

        # =========================
        # Buttons
        # =========================
        button_layout = QHBoxLayout()

        self.btn_select_image = QPushButton("Chọn ảnh")
        self.btn_process = QPushButton("OCR & Điểm danh")
        self.btn_clear = QPushButton("Clear")

        self.btn_select_image.setFixedHeight(40)
        self.btn_process.setFixedHeight(40)
        self.btn_clear.setFixedHeight(40)

        button_layout.addWidget(self.btn_select_image)
        button_layout.addWidget(self.btn_process)
        button_layout.addWidget(self.btn_clear)

        main_layout.addLayout(button_layout)

        # =========================
        # Image preview and OCR result
        # =========================
        content_layout = QHBoxLayout()

        self.image_preview = QLabel("Chưa chọn ảnh")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setFixedSize(550, 320)
        self.image_preview.setStyleSheet(
            """
            QLabel {
                border: 1px solid gray;
                background-color: #f5f5f5;
            }
            """
        )

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText("Danh sách tên detect được sẽ hiển thị ở đây...")
        self.ocr_text.setFixedHeight(320)

        content_layout.addWidget(self.image_preview)
        content_layout.addWidget(self.ocr_text)

        main_layout.addLayout(content_layout)

        # =========================
        # Result table
        # =========================
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(
            [
                "STT",
                "Tên nhân vật",
                "Trạng thái",
                "Ghi chú",
            ]
        )

        self.result_table.setColumnWidth(0, 70)
        self.result_table.setColumnWidth(1, 250)
        self.result_table.setColumnWidth(2, 150)
        self.result_table.setColumnWidth(3, 600)

        main_layout.addWidget(self.result_table)

        # =========================
        # Summary
        # =========================
        self.summary_label = QLabel(
            "Tổng: 0 | Thành công: 0 | Bỏ qua: 0 | Nhân vật mới: 0"
        )
        self.summary_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
            }
            """
        )

        main_layout.addWidget(self.summary_label)

        # =========================
        # Events
        # =========================
        self.btn_select_image.clicked.connect(self.select_image)
        self.btn_process.clicked.connect(self.process_attendance)
        self.btn_clear.clicked.connect(self.clear_screen)

    def select_image(self):
        """
        Select one image from local computer.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh quân đoàn",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)",
        )

        if not file_path:
            return

        self.selected_image = file_path
        self.show_image_preview(file_path)

        self.ocr_text.clear()
        self.result_table.setRowCount(0)
        self.reset_summary()

    def show_image_preview(self, file_path):
        """
        Show selected image preview.

        Args:
            file_path:
                Image file path.
        """
        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            QMessageBox.warning(
                self,
                "Lỗi",
                "Không thể mở ảnh đã chọn.",
            )
            return

        scaled_pixmap = pixmap.scaled(
            self.image_preview.width(),
            self.image_preview.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.image_preview.setPixmap(scaled_pixmap)

    def process_attendance(self):
        """
        Process attendance from selected image.

        Flow:
            1. Extract guild member names from selected image.
            2. Show detected names in OCR text area.
            3. Save attendance records into SQLite database.
            4. Show processing result in result table.
        """
        if not self.selected_image:
            QMessageBox.warning(
                self,
                "Thiếu ảnh",
                "Vui lòng chọn ảnh trước khi điểm danh.",
            )
            return

        try:
            self.ocr_text.setText("Đang OCR ảnh quân đoàn...")
            self.result_table.setRowCount(0)
            self.reset_summary()

            names = extract_member_names(self.selected_image)

            if not names:
                self.ocr_text.setText(
                    "Không detect được tên nào.\n\n"
                    "Hãy kiểm tra folder debug/crops xem crop có đúng vùng tên chưa."
                )

                QMessageBox.warning(
                    self,
                    "Không tìm thấy thành viên",
                    "OCR không detect được tên thành viên nào.\n\n"
                    "Vui lòng kiểm tra folder debug/crops.",
                )
                return

            self.ocr_text.setText("\n".join(names))

            results = save_attendance(
                names=names,
                source_image=self.selected_image,
            )

            self.show_results(results)

        except Exception as error:
            self.ocr_text.setText(f"Lỗi OCR:\n{error}")

            QMessageBox.critical(
                self,
                "Lỗi OCR / Điểm danh",
                str(error),
            )

    def show_results(self, results):
        """
        Show attendance results in table.

        Args:
            results:
                List of attendance result dictionaries.
        """
        self.result_table.setRowCount(len(results))

        success_count = 0
        skip_count = 0
        new_count = 0

        for row_index, item in enumerate(results):
            name = item.get("name", "")
            status = item.get("status", "")
            note = item.get("note", "")

            if status == "SUCCESS":
                success_count += 1
            elif status == "SKIP":
                skip_count += 1
            elif status == "NEW":
                new_count += 1
                success_count += 1

            values = [
                row_index + 1,
                name,
                status,
                note,
            ]

            for column_index, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setTextAlignment(Qt.AlignCenter)

                self.result_table.setItem(
                    row_index,
                    column_index,
                    table_item,
                )

        self.summary_label.setText(
            f"Tổng: {len(results)} | "
            f"Thành công: {success_count} | "
            f"Bỏ qua: {skip_count} | "
            f"Nhân vật mới: {new_count}"
        )

    def clear_screen(self):
        """
        Clear selected image, OCR result, and result table.
        """
        self.selected_image = None
        self.image_preview.clear()
        self.image_preview.setText("Chưa chọn ảnh")
        self.ocr_text.clear()
        self.result_table.setRowCount(0)
        self.reset_summary()

    def reset_summary(self):
        """
        Reset summary label.
        """
        self.summary_label.setText(
            "Tổng: 0 | Thành công: 0 | Bỏ qua: 0 | Nhân vật mới: 0"
        )