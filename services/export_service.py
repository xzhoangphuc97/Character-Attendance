# services/export_service.py

import os
import sys
from datetime import datetime

import pandas as pd

from database.db import get_connection


def get_base_dir():
    """
    Lấy thư mục gốc:
    - Nếu chạy bằng file .exe (PyInstaller): thư mục chứa file .exe
    - Nếu chạy bằng Python script: thư mục chứa file .py
    """
    if getattr(sys, 'frozen', False):  # đang chạy từ file .exe
        return os.path.dirname(sys.executable)
    else:  # chạy bằng Python script
        return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
EXPORT_DIR = os.path.join(BASE_DIR, "exports")


def export_daily_detail_excel(target_date):
    """
    Export daily attendance detail to Excel.

    Excel columns:
        - Tên nhân vật
        - Số lần điểm danh
        - Thời gian điểm danh

    Args:
        target_date:
            Date string in format yyyy-MM-dd.

    Returns:
        str:
            Output Excel file path.

    Raises:
        ValueError:
            If target_date has invalid format.
    """
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(
            "Ngày không hợp lệ. Format đúng là yyyy-MM-dd"
        ) from error

    os.makedirs(EXPORT_DIR, exist_ok=True)

    conn = get_connection()

    query = """
        SELECT
            p.name AS character_name,
            a.checkin_time AS checkin_time
        FROM attendance_logs a
        JOIN players p ON p.id = a.player_id
        WHERE substr(a.checkin_time, 1, 10) = ?
        ORDER BY p.name, a.checkin_time
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(target_date,),
    )

    conn.close()

    output_file = os.path.join(
        EXPORT_DIR,
        f"attendance_daily_detail_{target_date}.xlsx",
    )

    if df.empty:
        empty_df = pd.DataFrame(
            columns=[
                "Tên nhân vật",
                "Số lần điểm danh",
                "Thời gian điểm danh",
            ]
        )

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            empty_df.to_excel(
                writer,
                sheet_name="Daily Detail",
                index=False,
            )

        return output_file

    df["checkin_time_only"] = df["checkin_time"].str[11:19]

    summary_df = (
        df.groupby("character_name")
        .agg(
            total_checkins=("checkin_time", "count"),
            checkin_times=("checkin_time_only", lambda values: ", ".join(values)),
        )
        .reset_index()
    )

    summary_df = summary_df.rename(
        columns={
            "character_name": "Tên nhân vật",
            "total_checkins": "Số lần điểm danh",
            "checkin_times": "Thời gian điểm danh",
        }
    )

    raw_df = df.rename(
        columns={
            "character_name": "Tên nhân vật",
            "checkin_time": "Thời gian điểm danh đầy đủ",
            "checkin_time_only": "Giờ điểm danh",
        }
    )

    raw_df = raw_df[
        [
            "Tên nhân vật",
            "Thời gian điểm danh đầy đủ",
            "Giờ điểm danh",
        ]
    ]

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        summary_df.to_excel(
            writer,
            sheet_name="Daily Summary",
            index=False,
        )

        raw_df.to_excel(
            writer,
            sheet_name="Raw Data",
            index=False,
        )

    return output_file
