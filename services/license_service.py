# services/license_service.py

import base64
import hashlib
import hmac
import json
import os
import platform
import sqlite3
import uuid
from datetime import datetime, timedelta


TRIAL_DAYS = 30
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# IMPORTANT:
# Hãy đổi SECRET_KEY này trước khi build exe.
# Không gửi SECRET_KEY cho người dùng.
SECRET_KEY = "Zz9r8y5x2w1v0u3t6s9q4p7o0n1m2l3k4j5h6g7f8e9d0c1b2a3z4y5x6w7v8u9t0s1r2q3p4o5n6m7l8k9j0h1g2f3e4d5c6b7a8z9y0x1w2v3u4t5s6r7q8p9o0n1m2l3k4j5h6g7f8e9d0c1b2a3z4y5x6w7v8u9t0s1r2q3p4o5n6m7l8k9j0h1g2f3e4d5c6b7a8z9y0x1w2v3u4t5s6r7q8p9o0n1m2l3k4j5h6g7f8e9d0c1b2a3z4y5x6w7v8u9t0s1r2q3p4o5n6m7l8k9j0h1g2f3e4d5c6b7a8z9y0x1w2v3u4t5s6r7q8p9o0n1m2l3k4j5h6g7f8e9d0c1b2a3z4y5x6w7v8u9t0s1r2q3p4o5n6m7l8k9j0h1g2f3e4d5c6b7a8z9y0x1w2v3u4t5s6r7q8p9o0n1m2l3k4j5h6g7f8e9d0c1b2a3z4y5x6w7v8u9t0s1r2q3p4o5n6m7l8k9j0h1g2f3e4d5c6b7a8z"

APP_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA"),
    "CharacterAttendance",
)


LICENSE_DB_PATH = os.path.join(
    APP_DATA_DIR,
    "license.db",
)


def get_license_connection():
    """
    Create and return SQLite connection for license database.

    License database is stored in:
        C:\\ProgramData\\CharacterAttendance\\license.db

    Returns:
        sqlite3.Connection:
            SQLite connection for license database.
    """
    os.makedirs(APP_DATA_DIR, exist_ok=True)

    return sqlite3.connect(LICENSE_DB_PATH)


def get_machine_id():
    """
    Generate a stable machine ID for current computer.

    Returns:
        str:
            Hashed machine ID.
    """
    raw_value = f"{platform.node()}-{platform.system()}-{uuid.getnode()}"

    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).hexdigest()


def init_license_table():
    """
    Create license_info table if not exists.
    """
    conn = get_license_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS license_info (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS used_license_keys (
            license_hash TEXT PRIMARY KEY,
            used_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def mark_license_key_as_used(license_key):
    """
    Mark a license key as used so it cannot be applied again.

    Args:
        license_key:
            License key to mark as used.
    """
    init_license_table()

    license_hash = hashlib.sha256(
        license_key.encode("utf-8")
    ).hexdigest()

    conn = get_license_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM used_license_keys
        WHERE license_hash = ?
        """,
        (license_hash,),
    )

    if cursor.fetchone():
        conn.close()
        raise ValueError("License key này đã được sử dụng và không thể nhập lại.")

    cursor.execute(
        """
        INSERT INTO used_license_keys (license_hash, used_at)
        VALUES (?, ?)
        """,
        (license_hash, datetime.now().strftime(DATETIME_FORMAT)),
    )

    conn.commit()
    conn.close()


def get_license_value(key):
    """
    Get license value by key.

    Args:
        key:
            License info key.

    Returns:
        str | None:
            Stored value or None.
    """
    conn = get_license_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT value
        FROM license_info
        WHERE key = ?
        """,
        (key,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row[0]


def set_license_value(key, value):
    """
    Set license value.

    Args:
        key:
            License info key.
        value:
            License info value.
    """
    conn = get_license_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO license_info (key, value)
        VALUES (?, ?)
        """,
        (key, value),
    )

    conn.commit()
    conn.close()


def initialize_trial_if_needed():
    """
    Initialize 30-day trial for this machine if not initialized.
    """
    init_license_table()

    first_run_at = get_license_value("first_run_at")
    expires_at = get_license_value("expires_at")
    machine_id = get_license_value("machine_id")

    if first_run_at and expires_at and machine_id:
        return

    now = datetime.now()
    expire_time = now + timedelta(days=TRIAL_DAYS)

    set_license_value("machine_id", get_machine_id())
    set_license_value("first_run_at", now.strftime(DATETIME_FORMAT))
    set_license_value("expires_at", expire_time.strftime(DATETIME_FORMAT))


def get_license_status():
    """
    Get current license status.

    Returns:
        dict:
            License status information.
    """
    initialize_trial_if_needed()

    machine_id = get_license_value("machine_id")
    first_run_at = get_license_value("first_run_at")
    expires_at_text = get_license_value("expires_at")

    expires_at = datetime.strptime(
        expires_at_text,
        DATETIME_FORMAT,
    )

    now = datetime.now()

    is_active = now <= expires_at

    remaining_days = (expires_at.date() - now.date()).days

    if remaining_days < 0:
        remaining_days = 0

    return {
        "machine_id": machine_id,
        "first_run_at": first_run_at,
        "expires_at": expires_at_text,
        "is_active": is_active,
        "remaining_days": remaining_days,
        "license_db_path": LICENSE_DB_PATH,
    }


def create_signature(payload):
    """
    Create HMAC signature for license payload.

    Args:
        payload:
            License payload.

    Returns:
        str:
            Signature.
    """
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_license_key(machine_id, extend_days):
    """
    Generate license key for selected machine.

    Args:
        machine_id:
            Machine ID from user's app.
        extend_days:
            Number of days to extend.

    Returns:
        str:
            License key.
    """
    payload = {
        "machine_id": machine_id,
        "extend_days": int(extend_days),
        "issued_at": datetime.now().strftime(DATETIME_FORMAT),
    }

    signature = create_signature(payload)

    license_data = {
        "payload": payload,
        "signature": signature,
    }

    raw_key = json.dumps(
        license_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    return base64.urlsafe_b64encode(
        raw_key.encode("utf-8")
    ).decode("utf-8")


def apply_license_key(license_key):
    """
    Apply license key and extend expiration date.

    Args:
        license_key:
            License key provided by app owner.

    Returns:
        dict:
            New license status.

    Raises:
        ValueError:
            If license key is invalid.
    """
    initialize_trial_if_needed()

    try:
        decoded = base64.urlsafe_b64decode(
            license_key.encode("utf-8")
        ).decode("utf-8")

        license_data = json.loads(decoded)

        payload = license_data["payload"]
        signature = license_data["signature"]

    except Exception as error:
        raise ValueError("License key không hợp lệ.") from error

    expected_signature = create_signature(payload)

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("License key sai chữ ký hoặc đã bị chỉnh sửa.")

    current_machine_id = get_machine_id()

    if payload.get("machine_id") != current_machine_id:
        raise ValueError(
            "License key không dùng cho máy này.\n"
            "Vui lòng kiểm tra lại Machine ID."
        )

    extend_days = int(payload.get("extend_days", 0))

    if extend_days <= 0:
        raise ValueError("Số ngày gia hạn không hợp lệ.")

    mark_license_key_as_used(license_key)

    current_expires_at_text = get_license_value("expires_at")
    current_expires_at = datetime.strptime(
        current_expires_at_text,
        DATETIME_FORMAT,
    )

    now = datetime.now()

    base_time = current_expires_at

    if current_expires_at < now:
        base_time = now

    new_expires_at = base_time + timedelta(days=extend_days)

    set_license_value(
        "expires_at",
        new_expires_at.strftime(DATETIME_FORMAT),
    )

    return get_license_status()


def reset_license_for_testing():
    """
    Reset license data.

    Warning:
        Only use this function for development/testing.
    """
    conn = get_license_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM license_info
        """
    )

    conn.commit()
    conn.close()