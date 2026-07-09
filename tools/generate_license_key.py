# tools/generate_license_key.py

import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

sys.path.append(BASE_DIR)

from services.license_service import generate_license_key


def main():
    """
    Generate license key.

    Usage:
        python tools/generate_license_key.py <machine_id> <days>

    Example:
        python tools/generate_license_key.py abc123 30
    """
    if len(sys.argv) != 3:
        print("Usage:")
        print("python tools/generate_license_key.py <machine_id> <days>")
        return

    machine_id = sys.argv[1]
    days = int(sys.argv[2])

    license_key = generate_license_key(
        machine_id=machine_id,
        extend_days=days,
    )

    print()
    print("LICENSE KEY:")
    print(license_key)
    print()


if __name__ == "__main__":
    main()