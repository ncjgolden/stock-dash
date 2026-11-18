import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from cj_krx_market_flow_offline import analyze

URL = "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT022"


class KRXMarketFlowOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "flows.csv"
        self.sessions = [date(2026, 8, 12) + timedelta(days=i) for i in range(61)]
        self.asof = self.sessions[-1].isoformat()
        self.rows = [(d.isoformat(), m, 100, -30, -70)
                     for m in ("KOSPI", "KOSDAQ") for d in self.sessions]
        self.save()

    def save(self):
        lines = ["date,market,foreign_krw,institution_krw,individual_krw"]
        lines += [f"{d},{m},{f},{i},{p}" for d, m, f, i, p in self.rows]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_report(self, **changes):
        args = {"asof": self.asof, "generated_at": self.asof+"T21:00:00+09:00",
                "source_url": URL, "finality": "FINAL"}
        args.update(changes)
        return analyze(self.path, **args)

    def test_exact_5_20_60_both_markets_and_not_approved(self):
        r = self.run_report()
        for m in ("KOSPI", "KOSDAQ"):
            self.assertEqual(r["results"][m]["windows"]["5"]["foreign_krw"], 500)
            self.assertEqual(r["results"][m]["windows"]["20"]["institution_krw"], -600)
            self.assertEqual(r["results"][m]["windows"]["60"]["individual_krw"], -4200)
        self.assertFalse(r["production_approved"])
        self.assertIn("SELF_REFERENTIAL", r["market_session_calendar"])

    def test_same_day_final_before_twenty_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report(generated_at=self.asof+"T18:30:00+09:00")

    def test_duplicate_session_rejected(self):
        self.rows.append(self.rows[-1])
        self.save()
        with self.assertRaises(ValueError):
            self.run_report()

    def test_missing_market_day_rejected(self):
        self.rows = [x for x in self.rows if not
                     (x[1] == "KOSDAQ" and x[0] == self.asof)]
        self.save()
        with self.assertRaises(ValueError):
            self.run_report()

    def test_wrong_unit_and_url_rejected(self):
        self.rows[-1] = (*self.rows[-1][:2], "1,000", -30, -70)
        self.save()
        with self.assertRaises(ValueError):
            self.run_report()
        self.rows[-1] = (*self.rows[-1][:2], 100, -30, -70)
        self.save()
        with self.assertRaises(ValueError):
            self.run_report(source_url="https://example.org/not-krx")

    def test_stale_day_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report(asof="2026-11-18")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report(generated_at=self.asof+"T21:00:00")


if __name__ == "__main__":
    unittest.main()
