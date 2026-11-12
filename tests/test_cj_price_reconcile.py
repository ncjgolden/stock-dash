import unittest
from datetime import date, timedelta

from cj_price_reconcile import compare_daily, source_host_allowed


class OfficialPriceReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.series = [(date(2026, 8, 1) + timedelta(days=i), 100.0+i)
                       for i in range(61)]
        self.url = "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd"

    def test_matching_61_point_series(self):
        res = compare_daily(self.series, self.series,
                            asof=self.series[-1][0], official_url=self.url)
        self.assertEqual(res["status"], "MATCHED_SERIES")
        self.assertEqual(res["sessions"], 61)

    def test_mismatch_blocks(self):
        changed = list(self.series)
        changed[-1] = (changed[-1][0], 9999.0)
        res = compare_daily(changed, self.series,
                            asof=self.series[-1][0], official_url=self.url)
        self.assertEqual(res["status"], "MISMATCH")

    def test_missing_or_stale_history_blocks(self):
        res = compare_daily(self.series[:-1], self.series,
                            asof=self.series[-1][0], official_url=self.url)
        self.assertEqual(res["status"], "UNKNOWN")
        self.assertEqual(res["reason"], "INSUFFICIENT_HISTORY")
        res = compare_daily(self.series, self.series,
                            asof=self.series[-1][0] + timedelta(days=1),
                            official_url=self.url)
        self.assertEqual(res["status"], "UNKNOWN")
        self.assertEqual(res["reason"], "REFERENCE_ASOF_MISMATCH")

    def test_spoofed_domain_is_not_official(self):
        self.assertFalse(source_host_allowed("https://data.krx.co.kr.evil.example/file"))
        self.assertFalse(source_host_allowed("http://data.krx.co.kr/file"))
        with self.assertRaises(ValueError):
            compare_daily(self.series, self.series,
                          asof=self.series[-1][0],
                          official_url="https://data.krx.co.kr.evil.example")

    def test_duplicate_session_rejected(self):
        with self.assertRaises(ValueError):
            compare_daily(self.series + self.series[-1:], self.series,
                          asof=self.series[-1][0], official_url=self.url)


if __name__ == "__main__":
    unittest.main()
