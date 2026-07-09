# services/attendance_service.py

from datetime import datetime

from database.db import get_connection


MIN_CHECKIN_SECONDS = 3600
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_all_players():
    """
    Get all existing players from database.

    Returns:
        listExisting players.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name
        FROM players
        ORDER BY name
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
        }
        for row in rows
    ]


def get_player_by_id(conn, player_id):
    """
    Get player by ID.

    Args:
        conn:
            SQLite connection.
        player_id:
            Player ID.

    Returns:
        dict | None:
            Player data or None.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name
        FROM players
        WHERE id = ?
        """,
        (player_id,),
    )

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
    }


def get_or_create_player(conn, name):
    """
    Get player by name. Insert new player if not exists.

    This function is used for OCR attendance.
    OCR can still create new players automatically.

    Args:
        conn:
            SQLite database connection.
        name:
            Character name.

    Returns:
        tuple[int, bool]:
            player_id and is_new_player.
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
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


def has_checkin_within_one_hour(conn, player_id, checkin_time):
    """
    Check if player already has another check-in within 1 hour.

    Args:
        conn:
            SQLite database connection.
        player_id:
            Player ID.
        checkin_time:
            Target check-in time.

    Returns:
        tuple[bool, int | None]:
            is_conflict and remaining minutes.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT checkin_time
        FROM attendance_logs
        WHERE player_id = ?
        """,
        (player_id,),
    )

    rows = cursor.fetchall()

    for row in rows:
        existing_time = datetime.strptime(row[0], DATETIME_FORMAT)
        diff_seconds = abs((checkin_time - existing_time).total_seconds())

        if diff_seconds < MIN_CHECKIN_SECONDS:
            remaining_minutes = int((MIN_CHECKIN_SECONDS - diff_seconds) / 60)
            return True, remaining_minutes

    return False, None


def save_attendance_at(names, source_image, checkin_time):
    """
    Save attendance records at specific check-in time.

    Used by OCR attendance.
    OCR can create new players if new names appear.

    Args:
        names:
            List of character names.
        source_image:
            Source image path.
        checkin_time:
            datetime object.

    Returns:
        list:
            Processing results for UI table.
    """
    conn = get_connection()
    cursor = conn.cursor()

    checkin_time_text = checkin_time.strftime(DATETIME_FORMAT)

    results = []

    unique_names = []
    for name in names:
        name = name.strip()

        if name and name not in unique_names:
            unique_names.append(name)

    for name in unique_names:
        player_id, is_new_player = get_or_create_player(conn, name)

        is_conflict, remaining_minutes = has_checkin_within_one_hour(
            conn=conn,
            player_id=player_id,
            checkin_time=checkin_time,
        )

        if is_conflict:
            results.append(
                {
                    "name": name,
                    "status": "SKIP",
                    "note": (
                        "Đã có điểm danh gần thời gian này. "
                        f"Cần cách ít nhất 1 giờ. Còn khoảng {remaining_minutes} phút"
                    ),
                }
            )
            continue

        cursor.execute(
            """
            INSERT INTO attendance_logs (
                player_id,
                checkin_time,
                source_image
            )
            VALUES (?, ?, ?)
            """,
            (player_id, checkin_time_text, source_image),
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

    conn.commit()
    conn.close()

    return results


def save_attendance(names, source_image):
    """
    Save OCR attendance records using current time.

    Args:
        names:
            List of character names.
        source_image:
            Source image path.

    Returns:
        list:
            Processing results for UI table.
    """
    return save_attendance_at(
        names=names,
        source_image=source_image,
        checkin_time=datetime.now(),
    )


def save_manual_attendance_existing(player_id, checkin_time_text):
    """
    Save manual attendance for an existing player only.

    This function does NOT create new player.
    User must choose an existing player from the list.

    Args:
        player_id:
            Existing player ID.
        checkin_time_text:
            Check-in time string in format yyyy-MM-dd HH:mm:ss.

    Returns:
        list:
            Processing result for UI table.

    Raises:
        ValueError:
            If player does not exist or datetime format is invalid.
    """
    try:
        checkin_time = datetime.strptime(
            checkin_time_text,
            DATETIME_FORMAT,
        )
    except ValueError as error:
        raise ValueError(
            "Thời gian điểm danh không hợp lệ. "
            "Format đúng là yyyy-MM-dd HH:mm:ss"
        ) from error

    conn = get_connection()
    cursor = conn.cursor()

    player = get_player_by_id(conn, player_id)

    if not player:
        conn.close()
        raise ValueError(
            "Nhân vật không tồn tại trong database. "
            "Vui lòng chọn tên từ danh sách có sẵn."
        )

    is_conflict, remaining_minutes = has_checkin_within_one_hour(
        conn=conn,
        player_id=player_id,
        checkin_time=checkin_time,
    )

    if is_conflict:
        conn.close()

        return [
            {
                "name": player["name"],
                "status": "SKIP",
                "note": (
                    "Đã có điểm danh gần thời gian này. "
                    f"Cần cách ít nhất 1 giờ. Còn khoảng {remaining_minutes} phút"
                ),
            }
        ]

    cursor.execute(
        """
        INSERT INTO attendance_logs (
            player_id,
            checkin_time,
            source_image
        )
        VALUES (?, ?, ?)
        """,
        (
            player_id,
            checkin_time.strftime(DATETIME_FORMAT),
            "manual_existing_player",
        ),
    )

    conn.commit()
    conn.close()

    return [
        {
            "name": player["name"],
            "status": "SUCCESS",
            "note": "Đã điểm danh thủ công từ danh sách có sẵn",
        }
    ]