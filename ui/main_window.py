# ui/main_window.py

from PySide6.QtCore import Qt, QDateTime, QDate, QStringListModel
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.attendance_service import (
    get_all_players,
    save_attendance,
    save_manual_attendance_existing,
)
from services.export_service import export_daily_detail_excel
from services.export_monthly_service import (
    export_monthly_excel as export_monthly_summary_excel,
)
from services.license_service import (
    apply_license_key,
    get_license_status,
)
from services.ocr_service import extract_member_names


class MainWindow(QMainWindow):
    """
    Main window for Character Attendance application.

    Features:
        - Select one game screenshot image.
        - Preview selected image.
        - Detect guild member names from image.
        - Save OCR attendance records into SQLite database.
        - Manual attendance by selecting existing player only.
        - Prevent creating new player from manual attendance.
        - Skip check-in if another check-in is less than 1 hour apart.
        - Export daily attendance detail to Excel.
        - Export monthly attendance summary to Excel.
        - 30-day trial license per machine.
        - Lock attendance features after license expiration.
    """

    def __init__(self):
        super().__init__()

        self.selected_image = None

        self.setWindowTitle("Character Attendance")
        self.resize(1300, 900)

        self.build_ui()

    def build_ui(self):
        """
        Build main UI layout.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # =========================
        # Title
        # =========================
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
        # License information
        # =========================
        license_layout = QHBoxLayout()

        self.license_status_label = QLabel()
        self.license_status_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.license_status_label.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #333333;
            }
            """
        )

        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText(
            "Nhập license key để gia hạn..."
        )

        self.btn_apply_license = QPushButton("Kích hoạt / Gia hạn")
        self.btn_apply_license.setFixedHeight(35)

        license_layout.addWidget(self.license_status_label)
        license_layout.addWidget(self.license_key_input)
        license_layout.addWidget(self.btn_apply_license)

        main_layout.addLayout(license_layout)

        # =========================
        # Main buttons
        # =========================
        button_layout = QHBoxLayout()

        self.btn_select_image = QPushButton("Chọn ảnh")
        self.btn_process = QPushButton("Điểm danh ảnh QĐ")
        self.btn_clear = QPushButton("Clear")

        self.btn_select_image.setFixedHeight(40)
        self.btn_process.setFixedHeight(40)
        self.btn_clear.setFixedHeight(40)

        button_layout.addWidget(self.btn_select_image)
        button_layout.addWidget(self.btn_process)
        button_layout.addWidget(self.btn_clear)

        main_layout.addLayout(button_layout)

        # =========================
        # Manual attendance input
        # =========================
        manual_layout = QHBoxLayout()

        self.manual_player_combo = QComboBox()
        self.manual_player_combo.setEditable(True)
        self.manual_player_combo.setInsertPolicy(QComboBox.NoInsert)
        self.manual_player_combo.setPlaceholderText(
            "Chọn hoặc tìm tên nhân vật..."
        )

        self.player_completer_model = QStringListModel()
        self.player_completer = QCompleter(self.player_completer_model)
        self.player_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.player_completer.setFilterMode(Qt.MatchContains)

        self.manual_player_combo.setCompleter(self.player_completer)

        self.manual_time_input = QDateTimeEdit()
        self.manual_time_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.manual_time_input.setDateTime(QDateTime.currentDateTime())
        self.manual_time_input.setCalendarPopup(True)

        self.btn_manual_checkin = QPushButton("Thêm điểm danh thủ công")
        self.btn_manual_checkin.setFixedHeight(35)

        self.btn_reload_players = QPushButton("Reload danh sách")
        self.btn_reload_players.setFixedHeight(35)

        manual_layout.addWidget(QLabel("Tên nhân vật có sẵn:"))
        manual_layout.addWidget(self.manual_player_combo)
        manual_layout.addWidget(QLabel("Thời gian:"))
        manual_layout.addWidget(self.manual_time_input)
        manual_layout.addWidget(self.btn_manual_checkin)
        manual_layout.addWidget(self.btn_reload_players)

        main_layout.addLayout(manual_layout)

        # =========================
        # Export daily Excel
        # =========================
        export_daily_layout = QHBoxLayout()

        self.export_date_input = QDateEdit()
        self.export_date_input.setDisplayFormat("yyyy-MM-dd")
        self.export_date_input.setDate(QDate.currentDate())
        self.export_date_input.setCalendarPopup(True)

        self.btn_export_daily = QPushButton("Xuất Excel theo ngày")
        self.btn_export_daily.setFixedHeight(35)

        export_daily_layout.addWidget(QLabel("Ngày xuất Excel:"))
        export_daily_layout.addWidget(self.export_date_input)
        export_daily_layout.addWidget(self.btn_export_daily)

        main_layout.addLayout(export_daily_layout)

        # =========================
        # Export monthly Excel
        # =========================
        export_monthly_layout = QHBoxLayout()

        self.export_month_input = QDateEdit()
        self.export_month_input.setDisplayFormat("yyyy-MM")
        self.export_month_input.setDate(QDate.currentDate())
        self.export_month_input.setCalendarPopup(True)

        self.btn_export_monthly = QPushButton("Xuất Excel theo tháng")
        self.btn_export_monthly.setFixedHeight(35)

        export_monthly_layout.addWidget(QLabel("Tháng xuất Excel:"))
        export_monthly_layout.addWidget(self.export_month_input)
        export_monthly_layout.addWidget(self.btn_export_monthly)

        main_layout.addLayout(export_monthly_layout)

        # =========================
        # Image preview and OCR result
        # =========================
        content_layout = QHBoxLayout()

        self.image_preview = QLabel("Chưa chọn ảnh")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setFixedSize(600, 300)
        self.image_preview.setStyleSheet(
            """
            QLabel {
                border: 1px solid gray;
                background-color: #f5f5f5;
            }
            """
        )

        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText(
            "Danh sách tên detect được sẽ hiển thị ở đây..."
        )
        self.ocr_text.setFixedHeight(300)

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
        self.result_table.setColumnWidth(1, 260)
        self.result_table.setColumnWidth(2, 160)
        self.result_table.setColumnWidth(3, 720)

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

        
        summary_layout = QHBoxLayout()

        summary_layout.addWidget(self.summary_label)

        contact_label = QLabel("Hoàng Phúc | Hỗ trợ: Zalo 098 128 5695")
        contact_label.setAlignment(Qt.AlignRight)
        contact_label.setStyleSheet("""
            color: #666666;
            font-size: 10pt;
        """)

        summary_layout.addStretch()
        summary_layout.addWidget(contact_label)

        main_layout.addLayout(summary_layout)


        # =========================
        # Events
        # =========================
        self.btn_select_image.clicked.connect(self.select_image)
        self.btn_process.clicked.connect(self.process_attendance)
        self.btn_clear.clicked.connect(self.clear_screen)
        self.btn_manual_checkin.clicked.connect(self.process_manual_attendance)
        self.btn_export_daily.clicked.connect(self.export_daily_excel)
        self.btn_export_monthly.clicked.connect(self.export_monthly_excel)
        self.btn_reload_players.clicked.connect(self.load_players_to_combo)
        self.btn_apply_license.clicked.connect(self.apply_license)

        self.load_players_to_combo()
        self.refresh_license_status()

    def refresh_license_status(self):
        """
        Refresh license status and enable/disable attendance features.
        """
        status = get_license_status()

        machine_id = status["machine_id"]
        expires_at = status["expires_at"]
        remaining_days = status["remaining_days"]
        is_active = status["is_active"]

        if is_active:
            self.license_status_label.setText(
                "License: ACTIVE | "
                f"Còn {remaining_days} ngày | "
                f"Hết hạn: {expires_at} | "
                f"Machine ID: {machine_id}"
            )

            self.btn_process.setEnabled(True)
            self.btn_manual_checkin.setEnabled(True)

        else:
            self.license_status_label.setText(
                "License: EXPIRED | "
                f"Hết hạn: {expires_at} | "
                f"Machine ID: {machine_id}"
            )

            self.btn_process.setEnabled(False)
            self.btn_manual_checkin.setEnabled(False)

    def apply_license(self):
        """
        Apply license key from input and refresh license status.
        """
        license_key = self.license_key_input.text().strip()

        if not license_key:
            QMessageBox.warning(
                self,
                "Thiếu license key",
                "Vui lòng nhập license key.",
            )
            return

        try:
            status = apply_license_key(license_key)

            self.license_key_input.clear()
            self.refresh_license_status()

            QMessageBox.information(
                self,
                "Gia hạn thành công",
                "License đã được gia hạn thành công.\n\n"
                f"Hạn mới: {status['expires_at']}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "License key không hợp lệ",
                str(error),
            )

    def ensure_license_active(self):
        """
        Ensure license is active before attendance actions.

        Returns:
            bool:
                True if license is active, otherwise False.
        """
        status = get_license_status()

        if status["is_active"]:
            return True

        QMessageBox.warning(
            self,
            "License đã hết hạn",
            "Bản dùng thử 30 ngày đã hết hạn.\n\n"
            "Tính năng điểm danh đã bị khóa.\n"
            "Vui lòng nhập license key do chủ app cung cấp để gia hạn.",
        )

        self.refresh_license_status()
        return False

    def load_players_to_combo(self):
        """
        Load existing players from database to searchable combo box.
        """
        players = get_all_players()

        self.manual_player_combo.clear()
        self.player_completer_model.setStringList([])

        self.manual_player_combo.addItem("Chọn/tìm tên nhân vật...", None)

        player_names = []

        for player in players:
            self.manual_player_combo.addItem(
                player["name"],
                player["id"],
            )
            player_names.append(player["name"])

        self.player_completer_model.setStringList(player_names)
        self.manual_player_combo.setCurrentIndex(0)

    def get_selected_manual_player_id(self):
        """
        Get selected player ID from combo box.

        Returns:
            int | None:
                Selected player ID or None.
        """
        current_text = self.manual_player_combo.currentText().strip()

        if not current_text:
            return None

        for index in range(self.manual_player_combo.count()):
            item_text = self.manual_player_combo.itemText(index).strip()
            item_data = self.manual_player_combo.itemData(index)

            if item_text.lower() == current_text.lower() and item_data is not None:
                return item_data

        return None

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
        """
        if not self.ensure_license_active():
            return

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
            self.load_players_to_combo()
            self.refresh_license_status()

        except Exception as error:
            self.ocr_text.setText(f"Lỗi OCR:\n{error}")

            QMessageBox.critical(
                self,
                "Lỗi OCR / Điểm danh",
                str(error),
            )

    def process_manual_attendance(self):
        """
        Process manual attendance by selecting existing player only.
        """
        if not self.ensure_license_active():
            return

        player_id = self.get_selected_manual_player_id()

        checkin_time_text = self.manual_time_input.dateTime().toString(
            "yyyy-MM-dd HH:mm:ss"
        )

        if player_id is None:
            QMessageBox.warning(
                self,
                "Chưa chọn nhân vật",
                "Vui lòng chọn tên nhân vật có sẵn trong danh sách.\n\n"
                "Không thể nhập tên mới ở phần điểm danh thủ công.",
            )
            return

        try:
            results = save_manual_attendance_existing(
                player_id=player_id,
                checkin_time_text=checkin_time_text,
            )

            selected_name = self.manual_player_combo.currentText().strip()

            self.ocr_text.setText(
                "Điểm danh thủ công từ danh sách có sẵn:\n"
                f"{selected_name}\n\n"
                "Thời gian:\n"
                f"{checkin_time_text}"
            )

            self.show_results(results)

            self.manual_player_combo.setCurrentIndex(0)
            self.manual_time_input.setDateTime(QDateTime.currentDateTime())
            self.refresh_license_status()

        except Exception as error:
            QMessageBox.critical(
                self,
                "Lỗi điểm danh thủ công",
                str(error),
            )

    def export_daily_excel(self):
        """
        Export daily attendance detail to Excel.
        """
        target_date = self.export_date_input.date().toString("yyyy-MM-dd")

        try:
            output_file = export_daily_detail_excel(target_date)

            QMessageBox.information(
                self,
                "Xuất Excel theo ngày thành công",
                f"Đã tạo file Excel:\n{output_file}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Lỗi xuất Excel theo ngày",
                str(error),
            )

    def export_monthly_excel(self):
        """
        Export monthly attendance summary to Excel.
        """
        selected_date = self.export_month_input.date()

        year = selected_date.year()
        month = selected_date.month()

        try:
            output_file = export_monthly_summary_excel(
                year=year,
                month=month,
            )

            QMessageBox.information(
                self,
                "Xuất Excel theo tháng thành công",
                f"Đã tạo file Excel:\n{output_file}",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Lỗi xuất Excel theo tháng",
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

        self.manual_player_combo.setCurrentIndex(0)
        self.manual_time_input.setDateTime(QDateTime.currentDateTime())
        self.export_date_input.setDate(QDate.currentDate())
        self.export_month_input.setDate(QDate.currentDate())

        self.reset_summary()
        self.refresh_license_status()

    def reset_summary(self):
        """
        Reset summary label.
        """
        self.summary_label.setText(
            "Tổng: 0 | Thành công: 0 | Bỏ qua: 0 | Nhân vật mới: 0"
        )