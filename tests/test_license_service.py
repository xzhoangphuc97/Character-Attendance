import unittest

from services.license_service import (
    apply_license_key,
    generate_license_key,
    get_machine_id,
    reset_license_for_testing,
)


class LicenseServiceTests(unittest.TestCase):
    def setUp(self):
        reset_license_for_testing()

    def test_license_key_can_only_be_used_once(self):
        machine_id = get_machine_id()
        license_key = generate_license_key(machine_id, 30)

        first_status = apply_license_key(license_key)
        self.assertTrue(first_status["is_active"])

        with self.assertRaises(ValueError) as context:
            apply_license_key(license_key)

        self.assertIn("đã được sử dụng", str(context.exception))


if __name__ == "__main__":
    unittest.main()
