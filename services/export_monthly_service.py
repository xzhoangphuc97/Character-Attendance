# services/export_monthly_service.py

import calendar
import os

import pandas as pd

from database.db import get_connection


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")


def export_monthly_excel(year, month):
    """
    Export monthly attendance summary to Excel.

    The Excel file contains:
        1. Monthly Summary:
            Character name with count of check-ins per day and monthly total.

        2. Attendance Rate:
            Character name with number of present days and total check-ins.

        3. Raw Data:
            All attendance records in selected month.

    Args:
        year:
            Target year.
        month:
            Target month.

    Returns:
        str:
            Output Excel file path.
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)

    month_prefix = f"{year}-{month:02d}"
    last_day = calendar.monthrange(year, month)[1]

    conn = get_connection()

    query = """
        SELECT
            p.name AS character_name,
            a.checkin_time AS checkin_time
        FROM attendance_logs a
        JOIN players p
            ON p.id = a.player_id
        WHERE substr(a.checkin_time, 1, 7) = ?
        ORDER BY p.name, a.checkin_time
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(month_prefix,),
    )

    conn.close()

    output_file = os.path.join(
        EXPORT_DIR,
        f"attendance_monthly_{month_prefix}.xlsx",
    )

    day_columns = [f"{day:02d}" for day in range(1, last_day + 1)]

    if df.empty:
        monthly_summary_df = pd.DataFrame(
            columns=["Tên nhân vật"] + day_columns + ["Tổng"]
        )

        attendance_rate_df = pd.DataFrame(
            columns=[
                "Tên nhân vật",
                "Số ngày có mặt",
                "Tổng số lần điểm danh",
            ]
        )

        raw_data_df = pd.DataFrame(
            columns=[
                "Tên nhân vật",
                "Thời gian điểm danh",
                "Ngày",
                "Giờ",
            ]
        )

        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            monthly_summary_df.to_excel(
                writer,
                sheet_name="Monthly Summary",
                index=False,
            )

            attendance_rate_df.to_excel(
                writer,
                sheet_name="Attendance Rate",
                index=False,
            )

            raw_data_df.to_excel(
                writer,
                sheet_name="Raw Data",
                index=False,
            )

        return output_file

    df["day"] = df["checkin_time"].str[8:10]
    df["time_only"] = df["checkin_time"].str[11:19]

    monthly_summary_df = pd.pivot_table(
        df,
        index="character_name",
        columns="day",
        values="checkin_time",
        aggfunc="count",
        fill_value=0,
    )

    for day in day_columns:
        if day not in monthly_summary_df.columns:
            monthly_summary_df[day] = 0

    monthly_summary_df = monthly_summary_df[day_columns]
    monthly_summary_df["Tổng"] = monthly_summary_df.sum(axis=1)

    monthly_summary_df = monthly_summary_df.reset_index()
    monthly_summary_df = monthly_summary_df.rename(
        columns={
            "character_name": "Tên nhân vật",
        }
    )

    attendance_rate_df = (
        df.groupby("character_name")
        .agg(
            present_days=("day", "nunique"),
            total_checkins=("checkin_time", "count"),
        )
        .reset_index()
    )

    attendance_rate_df = attendance_rate_df.rename(
        columns={
            "character_name": "Tên nhân vật",
            "present_days": "Số ngày có mặt",
            "total_checkins": "Tổng số lần điểm danh",
        }
    )

    raw_data_df = df[
        [
            "character_name",
            "checkin_time",
            "day",
            "time_only",
        ]
    ].copy()

    raw_data_df = raw_data_df.rename(
        columns={
            "character_name": "Tên nhân vật",
            "checkin_time": "Thời gian điểm danh",
            "day": "Ngày",
            "time_only": "Giờ",
        }
    )

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        monthly_summary_df.to_excel(
            writer,
            sheet_name="Monthly Summary",
            index=False,
        )

        attendance_rate_df.to_excel(
            writer,
            sheet_name="Attendance Rate",
            index=False,
        )

        raw_data_df.to_excel(
            writer,
            sheet_name="Raw Data",
            index=False,
        )

    return output_file