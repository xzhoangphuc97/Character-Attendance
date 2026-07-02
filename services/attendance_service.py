# services/attendance_service.py

from datetime import datetime

from database.db import get_connection


MIN_CHECKIN_SECONDS = 3600


def get_or_create_player(conn, name):
    """
    Get player by name. Insert new player if not exists.

    Args:
        conn:
            SQLite database connection.
        name:
            Character name.

    Returns:
        tuple[int, bool]:
            player_id and is_new_player.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM players
        WHERE name = ?
        """,
        (name,),
    )

    row = cursor.fetchone()

    if row:
        player_id = row[0]

        cursor.execute(
            """
            UPDATE players
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, player_id),
        )

        return player_id, False

    cursor.execute(
        """
        INSERT INTO players (name, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (name, now, now),
    )

    return cursor.lastrowid, True


def get_last_checkin_time(conn, player_id):
    """
    Get latest check-in time of a player.

    Args:
        conn:
            SQLite database connection.
        player_id:
            Player ID.

    Returns:
        datetime | None:
            Latest check-in time or None.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT checkin_time
        FROM attendance_logs
        WHERE player_id = ?
        ORDER BY checkin_time DESC
        LIMIT 1
        """,
        (player_id,),
    )

    row = cursor.fetchone()

    if not row:
        return None

    return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")


def save_attendance(names, source_image):
    """
    Save attendance records.

    Rule:
        - If player is new, insert into players first.
        - If latest check-in is less than 1 hour, skip.
        - If latest check-in is greater than or equal to 1 hour, insert new record.

    Args:
        names:
            List of character names.
        source_image:
            Source image path.

    Returns:
        list:
            Processing results for UI table.
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")

    results = []

    unique_names = []
    for name in names:
        if name and name not in unique_names:
            unique_names.append(name)

    for name in unique_names:
        player_id, is_new_player = get_or_create_player(conn, name)
        last_checkin_time = get_last_checkin_time(conn, player_id)

        if last_checkin_time is None:
            cursor.execute(
                """
                INSERT INTO attendance_logs (
                    player_id,
                    checkin_time,
                    source_image
                )
                VALUES (?, ?, ?)
                """,
                (player_id, now_text, source_image),
            )

            results.append(
                {
                    "name": name,
                    "status": "NEW" if is_new_player else "SUCCESS",
                    "note": "Nhân vật mới + đã điểm danh"
                    if is_new_player
                    else "Đã điểm danh",
                }
            )

            continue

        diff_seconds = (now - last_checkin_time).total_seconds()

        if diff_seconds >= MIN_CHECKIN_SECONDS:
            cursor.execute(
                """
                INSERT INTO attendance_logs (
                    player_id,
                    checkin_time,
                    source_image
                )
                VALUES (?, ?, ?)
                """,
                (player_id, now_text, source_image),
            )

            results.append(
                {
                    "name": name,
                    "status": "SUCCESS",
                    "note": "Đã điểm danh",
                }
            )

        else:
            remaining_minutes = int((MIN_CHECKIN_SECONDS - diff_seconds) / 60)

            results.append(
                {
                    "name": name,
                    "status": "SKIP",
                    "note": f"Chưa đủ 1 giờ. Còn khoảng {remaining_minutes} phút",
                }
            )

    conn.commit()
    conn.close()

    return results