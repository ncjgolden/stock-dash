import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cj_price_evidence_review import review


class EvidenceReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.public = root / "public.csv"
        self.official = root / "krx.csv"
        start = __import__("datetime").date(2026, 8, 1)
        rows = [((start + timedelta(days=i)).isoformat(), "005930", 100+i)
                for i in range(61)]
        for path in (self.public, self.official):
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["date", "symbol", "close"])
                w.writerows(rows)
        self.when = datetime(2026, 10, 1, 20, tzinfo=timezone(timedelta(hours=9)))

    def inspect(self, **overrides):
        opts = dict(public_path=self.public, reference_path=self.official,
                    symbol="005930", asof="2026-09-30",
                    official_url="https://data.krx.co.kr/", now=self.when)
        opts.update(overrides)
        return review(**opts)

    def test_matching_files_never_auto_approve(self):
        r = self.inspect()
        self.assertEqual(r["status"], "MATCHED_NEEDS_ORIGIN_REVIEW")
        self.assertEqual(r["compared_sessions"], 61)
        self.assertFalse(r["reference_origin_confirmed"])
        self.assertFalse(r["usable_in_automatic_chatgpt_briefing"])
        self.assertEqual(len(r["reference_file_sha256"]), 64)

    def test_same_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "different paths"):
            self.inspect(reference_path=self.public)

    def test_single_price_mismatch_is_blocked(self):
        with self.official.open("a", encoding="utf-8") as f:
            f.write("2026-10-01,005930,9999\n")
        r = self.inspect(asof="2026-10-01", now=self.when)
        self.assertEqual(r["status"], "BLOCKED")

    def test_not_a_real_official_host_rejected(self):
        with self.assertRaises(ValueError):
            self.inspect(official_url="https://data.krx.co.kr.evil.example/")

    def test_future_asof_rejected(self):
        with self.assertRaises(ValueError):
            self.inspect(asof="2026-11-11")


if __name__ == "__main__":
    unittest.main()
