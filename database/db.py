# database/db.py

import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")


def get_connection():
    """
    Create and return SQLite connection.

    Returns:
        sqlite3.Connection:
            SQLite database connection.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    Initialize database tables.

    Tables:
        players:
            Store unique character names.

        attendance_logs:
            Store check-in records.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            checkin_time TEXT NOT NULL,
            source_image TEXT,
            FOREIGN KEY(player_id) REFERENCES players(id)
        )
        """
    )

    conn.commit()
    conn.close()