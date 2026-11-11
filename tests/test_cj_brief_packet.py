import unittest

from cj_brief_packet import concise


class BriefPacketTests(unittest.TestCase):
    def test_only_verified_windows_get_numbers(self):
        values = {"foreign_krw": 100_000_000, "institution_krw": -50_000_000,
                  "individual_krw": -50_000_000}
        report = {"asof": "2026-11-10", "verification": "PARTIAL_OR_FAILED",
                  "windows": {"5": {"status": "MATCHED", "values": values},
                              "20": {"status": "MISMATCH", "values": values},
                              "60": {"status": "UNKNOWN", "values": None}}}
        output = concise(report, target="005930")
        self.assertIn("5거래일: 외국인 +1.0", output)
        self.assertIn("20거래일: UNKNOWN", output)
        self.assertIn("60거래일: UNKNOWN", output)
        self.assertNotIn("20거래일: 외국인", output)

    def test_rejects_unscoped_ticker(self):
        with self.assertRaises(ValueError):
            concise({"windows": {}}, target="NVDA")


if __name__ == "__main__":
    unittest.main()
