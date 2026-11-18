import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

from cj_market_trends import clean_rows, summarize, collect


KST = timezone(timedelta(hours=9))


def fixture_prices(count=61, start=date(2026, 8, 1)):
    # Simulated sequential dates; tests the session index, not holiday data.
    return [(start+timedelta(days=n), 100+n) for n in range(count)]


class TrendTests(unittest.TestCase):
    def test_5_20_60_returns_and_averages(self):
        rows=fixture_prices()
        r=summarize(rows,asof="2026-09-30",now=datetime(2026,10,1,10,tzinfo=KST),market="KR")
        self.assertEqual(r["status"],"DATA_ONLY")
        self.assertAlmostEqual(r["returns_pct"]["5"],(160/155-1)*100,places=4)
        self.assertAlmostEqual(r["returns_pct"]["60"],60.0)
        self.assertEqual(r["ma"]["20"],150.5)

    def test_insufficient_history_not_zero(self):
        rows=fixture_prices(20)
        r=summarize(rows,asof="2026-08-20",now=datetime(2026,8,21,12,tzinfo=KST),market="KR")
        self.assertIsNone(r["returns_pct"]["60"])
        self.assertIsNone(r["returns_pct"]["20"])
        self.assertEqual(r["status"],"PARTIAL")

    def test_non_finite_duplicate_and_zero_fail(self):
        rows=fixture_prices(3)
        with self.assertRaises(ValueError):
            clean_rows(rows+[rows[-1]],asof="2026-08-10")
        with self.assertRaises(ValueError):
            clean_rows([(date(2026,8,1),float("nan"))],asof="2026-08-10")
        with self.assertRaises(ValueError):
            clean_rows([(date(2026,8,1),0)],asof="2026-08-10")

    def test_kr_same_day_unconfirmed_before_18(self):
        r=summarize(fixture_prices(),asof="2026-09-30",
                    now=datetime(2026,9,30,16,30,tzinfo=KST),market="KR")
        self.assertEqual(r["status"],"UNCONFIRMED_TODAY")
        self.assertIsNone(r["returns_pct"]["5"])

    def test_us_today_never_closed_by_inference(self):
        r=summarize(fixture_prices(),asof="2026-09-30",
                    now=datetime(2026,9,30,23,tzinfo=KST),market="US")
        self.assertEqual(r["status"],"UNCONFIRMED_US_SESSION")

    def test_future_and_stale_requests_fail(self):
        with self.assertRaises(ValueError):
            summarize(fixture_prices(),asof="2026-10-02",
                      now=datetime(2026,10,1,20,tzinfo=KST),market="KR")
        with self.assertRaises(ValueError):
            summarize(fixture_prices(),asof="2026-09-30",
                      now=datetime(2026,10,20,20,tzinfo=KST),market="KR")

    def test_provider_failure_unknown(self):
        import pandas as pd
        fdr=Mock()
        fdr.DataReader.side_effect=ValueError("temporary")
        r=collect(market="KR",asof="2026-09-30",
                  now=datetime(2026,10,1,20,tzinfo=KST),fdr=fdr,
                  symbols={"삼성전자":("FDR","005930")})
        self.assertEqual(r["results"]["삼성전자"]["status"],"UNKNOWN")
        self.assertNotIn("temporary",str(r))

    def test_no_future_closes_included(self):
        rows=[(date(2026,9,30),100),(date(2026,10,1),1000)]
        r=summarize(rows,asof="2026-09-30",
                    now=datetime(2026,10,1,20,tzinfo=KST),market="KR")
        self.assertEqual(r["close"],100)


if __name__=="__main__":
    unittest.main()
