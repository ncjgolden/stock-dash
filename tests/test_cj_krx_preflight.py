import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from cj_krx_preflight import preflight


class KRXPreflightTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 12, 16, tzinfo=timezone(timedelta(hours=9)))

    def test_no_secret_no_files_fails_closed(self):
        value = preflight(now=self.now, env={})
        self.assertEqual(value["release_gate"], "BLOCKED")
        self.assertFalse(value["market_data_validated"])
        self.assertEqual(value["price_reconciliation"], "NOT_RUN")
        self.assertFalse(value["krx_openapi_access_key_configured_locally"])
        self.assertFalse(value["chatgpt_automation_connected"])

    def test_key_present_only_signals_configured_not_approved(self):
        value = preflight(now=self.now, env={"KRX_AUTH_KEY": "do-not-disclose"})
        self.assertTrue(value["krx_openapi_access_key_configured_locally"])
        self.assertFalse(value["openapi_entitlement_confirmed"])
        self.assertNotIn("do-not-disclose", str(value))
        self.assertEqual(value["release_gate"], "BLOCKED")

    def test_independently_named_matching_files_are_not_auto_approved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            public = root / "public.csv"
            official = root / "reference.csv"
            start = date(2026, 8, 1)
            rows = [((start + timedelta(days=i)).isoformat(), "005930", 100+i)
                    for i in range(61)]
            for path in (public, official):
                with path.open("w", newline="", encoding="utf8") as f:
                    writer = csv.writer(f)
                    writer.writerow(("date", "symbol", "close"))
                    writer.writerows(rows)
            value = preflight(
                now=self.now, env={}, symbol="005930", asof="2026-09-30",
                public_csv=public, official_csv=official)
            self.assertEqual(value["price_reconciliation"], "MATCHED_NEEDS_ORIGIN_REVIEW")
            self.assertEqual(value["compared_sessions"], 61)
            self.assertFalse(value["market_data_validated"])
            self.assertEqual(value["release_gate"], "BLOCKED")

    def test_malformed_file_is_blocked_without_leaking_content(self):
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "a.csv"
            second = Path(td) / "b.csv"
            first.write_text("unsafe financial text", encoding="utf8")
            second.write_text("unsafe private data", encoding="utf8")
            value = preflight(now=self.now, env={},
                              public_csv=first, official_csv=second,
                              asof="2026-11-11")
            self.assertEqual(value["price_reconciliation"], "BLOCKED")
            self.assertNotIn("unsafe financial", str(value))
            self.assertNotIn("unsafe private", str(value))


if __name__ == "__main__":
    unittest.main()
