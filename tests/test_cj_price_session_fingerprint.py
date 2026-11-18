import hashlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from cj_price_session_fingerprint import fingerprint, rows_from_csv


class PriceSessionFingerprintTests(unittest.TestCase):
    def setUp(self):
        start = date(2026, 8, 1)
        self.rows = [((start+timedelta(days=i)).isoformat(), 1000+i)
                     for i in range(61)]
        self.asof = self.rows[-1][0]

    def test_stable_reproducible_fingerprint(self):
        r = fingerprint(self.rows, symbol="005930", asof=self.asof)
        block = "".join(f"{d},{v}\n" for d, v in self.rows)
        self.assertEqual(r["counts"]["61"]["sha256"],
                         hashlib.sha256(block.encode()).hexdigest())
        self.assertEqual(r, fingerprint(self.rows[::-1], symbol="005930", asof=self.asof))
        self.assertEqual(r["status"], "HASH_ONLY_UNVERIFIED")

    def test_one_price_change_mismatches_all_affected_blocks(self):
        changed = list(self.rows)
        d, p = changed[-1]
        changed[-1] = (d, p+1)
        a = fingerprint(self.rows, symbol="005930", asof=self.asof)
        b = fingerprint(changed, symbol="005930", asof=self.asof)
        for n in ("5", "20", "61"):
            self.assertNotEqual(a["counts"][n]["sha256"], b["counts"][n]["sha256"])

    def test_incomplete_duplicate_or_decimal_rejected(self):
        with self.assertRaises(ValueError):
            fingerprint(self.rows[:60], symbol="005930", asof=self.asof)
        with self.assertRaises(ValueError):
            fingerprint(self.rows+self.rows[-1:], symbol="005930", asof=self.asof)
        bad = list(self.rows)
        bad[-1] = (bad[-1][0], "100.123")
        with self.assertRaises(ValueError):
            fingerprint(bad, symbol="005930", asof=self.asof)

    def test_csv_filters_other_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "example.csv"
            p.write_text("date,symbol,close\n2026-11-11,005930,200\n2026-11-11,000660,300\n",
                         encoding="utf-8")
            self.assertEqual(rows_from_csv(p, "005930"), [("2026-11-11","200")])


if __name__ == "__main__":
    unittest.main()
