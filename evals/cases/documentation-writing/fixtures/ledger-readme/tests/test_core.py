import unittest
from pathlib import Path

from ledger.core import summarise

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample.csv"


class SummariseTests(unittest.TestCase):
    def test_counts_rows(self):
        count, _ = summarise(str(SAMPLE))
        self.assertEqual(count, 3)

    def test_totals_to_two_decimals(self):
        _, total = summarise(str(SAMPLE))
        self.assertEqual(total, 120.5)
