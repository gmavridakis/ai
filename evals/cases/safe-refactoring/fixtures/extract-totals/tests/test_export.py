import json
import os
import unittest

from billing.export import export_csv

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "data", "invoices.json")) as fh:
    ROWS = json.load(fh)


class ExportCsvTests(unittest.TestCase):
    def test_month_is_required(self):
        with self.assertRaises(ValueError):
            export_csv(ROWS, {})

    def test_bad_month_format(self):
        with self.assertRaises(ValueError):
            export_csv(ROWS, {"month": "09/2026"})

    def test_unknown_country(self):
        with self.assertRaises(ValueError):
            export_csv(ROWS, {"month": "2026-09", "country": "XX"})

    def test_issued_includes_paid(self):
        out = export_csv(ROWS, {"month": "2026-09"})
        self.assertIn("INV-1002", out)
        self.assertNotIn("CN-0007", out)
        self.assertNotIn("INV-1005", out)

    def test_header_and_grand_line(self):
        out = export_csv(ROWS, {"month": "2026-09", "country": "DE"})
        lines = out.splitlines()
        self.assertEqual(lines[0], "number,date,customer,country,status,net,vat,gross")
        self.assertEqual(lines[-1], "GRAND,2026-09,,,1 lines,310.50,58.99,369.49")

    def test_rows_sorted_by_date_then_number(self):
        out = export_csv(ROWS, {"month": "2026-09"})
        numbers = [l.split(",")[0] for l in out.splitlines()[1:] if l.startswith("INV")]
        self.assertEqual(numbers, ["INV-1001", "INV-1002", "INV-1003", "INV-1004", "INV-1006"])


if __name__ == "__main__":
    unittest.main()
