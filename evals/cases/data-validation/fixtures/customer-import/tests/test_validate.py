import unittest

from importer.validate import validate_row


class ValidateRowTests(unittest.TestCase):
    def test_valid_row(self):
        out = validate_row({"name": "Maria", "email": "M@Example.com", "birth_date": "1990-05-14", "credit_limit": "5000"})
        self.assertEqual(out["email"], "m@example.com")
        self.assertEqual(out["credit_limit"], 5000)

    def test_missing_name(self):
        with self.assertRaises(ValueError):
            validate_row({"name": "", "email": "a@b.c", "birth_date": "1990-05-14", "credit_limit": "1"})


if __name__ == "__main__":
    unittest.main()
