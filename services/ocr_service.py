# services/ocr_service.py

import os
import re
from pathlib import Path

import cv2
import easyocr


GRID_ROWS = 6
GRID_COLS = 3

# Vùng bảng "Quân đoàn" theo tỉ lệ ảnh.
# Dựa trên screenshot bạn gửi.
PANEL_RATIO = {
    "x1": 0.145,
    "y1": 0.185,
    "x2": 0.855,
    "y2": 0.890,
}

# Vùng tên nhân vật trong từng ô thành viên.
NAME_REGION_RATIO = {
    "x1": 0.200,
    "y1": 0.050,
    "x2": 0.760,
    "y2": 0.420,
}

SAVE_DEBUG_CROPS = True
DEBUG_DIR = "debug/crops"

MODEL_DIR = "models/easyocr"

_reader = None


def get_reader():
    """
    Create EasyOCR reader only once.

    Returns:
        easyocr.Reader:
            EasyOCR reader instance.

    Raises:
        RuntimeError:
            If EasyOCR cannot download or load model.
    """
    global _reader

    if _reader is None:
        try:
            _reader = easyocr.Reader(
                ["en"],
                gpu=False,
                model_storage_directory=MODEL_DIR,
                download_enabled=True,
            )

        except Exception as error:
            raise RuntimeError(
                "EasyOCR không thể tải hoặc load model OCR.\n\n"
                "Nguyên nhân thường gặp:\n"
                "- Máy đang dùng proxy công ty.\n"
                "- Proxy yêu cầu authentication.\n"
                "- Không có internet để tải model lần đầu.\n\n"
                "Cách xử lý:\n"
                "1. Kết nối hotspot điện thoại rồi chạy app một lần.\n"
                "2. Hoặc cấu hình HTTP_PROXY / HTTPS_PROXY trong PowerShell.\n"
                "3. Hoặc copy model EasyOCR vào folder models/easyocr.\n\n"
                f"Lỗi gốc:\n{error}"
            )

    return _reader


def clean_character_name(raw_text):
    """
    Clean OCR text and return character name.

    Args:
        raw_text:
            Raw OCR text.

    Returns:
        str | None:
            Clean character name or None.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    text = text.replace("|", "I")
    text = text.replace("!", "I")
    text = text.replace("‘", "")
    text = text.replace("’", "")
    text = text.replace("`", "")
    text = text.replace("“", "")
    text = text.replace("”", "")
    text = text.replace(":", "")
    text = text.replace(";", "")
    text = text.replace(",", "")

    text = re.sub(
        r"[^a-zA-Z0-9À-ỹĐđ._\-\[\] ]+",
        "",
        text,
    )

    text = re.sub(r"\s+", "", text)

    invalid_keywords = [
        "Cap",
        "Cấp",
        "Vitri",
        "Vịtrí",
        "KinhHo",
        "KínhHồ",
        "DiaPhu",
        "ĐịaPhủ",
        "NgaMy",
        "NgaMỵ",
        "VoDang",
        "VõĐang",
        "CaiBang",
        "CáiBang",
        "TieuDao",
        "TiêuDao",
        "TinhTuc",
        "TinhTúc",
        "ThienSon",
        "ThiênSơn",
        "DuongMon",
        "ĐườngMôn",
        "TongSo",
        "Tổngsố",
        "ThanhVien",
        "Thànhviên",
    ]

    for keyword in invalid_keywords:
        if keyword.lower() in text.lower():
            return None

    if len(text) < 3:
        return None

    return text


def preprocess_name_crop(name_crop):
    """
    Preprocess crop image before OCR.

    Args:
        name_crop:
            OpenCV crop image.

    Returns:
        OpenCV image:
            Processed image.
    """
    resized = cv2.resize(
        name_crop,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC,
    )

    return resized


def ocr_single_name(name_crop):
    """
    OCR one member name crop by EasyOCR.

    Args:
        name_crop:
            OpenCV image crop.

    Returns:
        str | None:
            Detected character name.
    """
    reader = get_reader()

    processed = preprocess_name_crop(name_crop)

    results = reader.readtext(
        processed,
        detail=1,
        paragraph=False,
    )

    candidates = []

    for item in results:
        bbox, text, confidence = item

        name = clean_character_name(text)

        if name:
            candidates.append(
                {
                    "name": name,
                    "confidence": confidence,
                }
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["confidence"],
        reverse=True,
    )

    return candidates[0]["name"]


def extract_member_names(image_path):
    """
    Extract guild member names from screenshot.

    Layout:
        3 columns x 6 rows.

    Args:
        image_path:
            Image file path.

    Returns:
        list:
            Detected member names.
    """
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Không thể đọc ảnh: {image_path}")

    image_height, image_width = image.shape[:2]

    panel_x1 = int(image_width * PANEL_RATIO["x1"])
    panel_y1 = int(image_height * PANEL_RATIO["y1"])
    panel_x2 = int(image_width * PANEL_RATIO["x2"])
    panel_y2 = int(image_height * PANEL_RATIO["y2"])

    panel = image[panel_y1:panel_y2, panel_x1:panel_x2]

    panel_height, panel_width = panel.shape[:2]

    cell_width = panel_width // GRID_COLS
    cell_height = panel_height // GRID_ROWS

    if SAVE_DEBUG_CROPS:
        Path(DEBUG_DIR).mkdir(parents=True, exist_ok=True)
        cv2.imwrite(os.path.join(DEBUG_DIR, "panel.png"), panel)

    names = []

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            cell_x1 = col * cell_width
            cell_y1 = row * cell_height
            cell_x2 = cell_x1 + cell_width
            cell_y2 = cell_y1 + cell_height

            cell = panel[cell_y1:cell_y2, cell_x1:cell_x2]

            cell_h, cell_w = cell.shape[:2]

            name_x1 = int(cell_w * NAME_REGION_RATIO["x1"])
            name_y1 = int(cell_h * NAME_REGION_RATIO["y1"])
            name_x2 = int(cell_w * NAME_REGION_RATIO["x2"])
            name_y2 = int(cell_h * NAME_REGION_RATIO["y2"])

            name_crop = cell[name_y1:name_y2, name_x1:name_x2]

            if SAVE_DEBUG_CROPS:
                cv2.imwrite(
                    os.path.join(DEBUG_DIR, f"cell_r{row + 1}_c{col + 1}.png"),
                    cell,
                )
                cv2.imwrite(
                    os.path.join(DEBUG_DIR, f"name_r{row + 1}_c{col + 1}.png"),
                    name_crop,
                )

            name = ocr_single_name(name_crop)

            if name and name not in names:
                names.append(name)

    return names