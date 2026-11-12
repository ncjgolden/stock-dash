import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

from cj_investor_flow import summarize, collect


def days(n):
    first = date(2026, 7, 1)
    out = []
    while len(out) < n:
        day = first + timedelta(days=len(out) + (len(out) // 5) * 2)
        # Simulated trading sessions, not real exchange holiday calendar
        out.append(day)
    return out


class FlowTests(unittest.TestCase):
    def test_exact_5_20_60_windows_and_signs(self):
        ds = days(60)
        rows = [(d, {"foreign": 100, "institution": -20, "individual": -80})
                for d in reversed(ds)]
        outcome = summarize(rows, ds, asof=ds[-1])
        self.assertEqual(outcome["status"], "COMPLETE")
        self.assertEqual(outcome["windows"]["5"]["foreign_krw"], 500)
        self.assertEqual(outcome["windows"]["20"]["institution_krw"], -400)
        self.assertEqual(outcome["windows"]["60"]["individual_krw"], -4800)

    def test_missing_day_makes_only_affected_windows_unknown(self):
        ds = days(60)
        rows = [(d, {"foreign": 100, "institution": -20, "individual": -80})
                for d in ds if d != ds[52]]
        outcome = summarize(rows, ds, asof=ds[-1])
        self.assertIsNotNone(outcome["windows"]["5"])
        self.assertIsNone(outcome["windows"]["20"])
        self.assertIsNone(outcome["windows"]["60"])

    def test_missing_60_sessions_is_not_fake_60_day_sum(self):
        ds = days(20)
        rows = [(d, {"foreign": 0, "institution": 0, "individual": 0})
                for d in ds]
        outcome = summarize(rows, ds, asof=ds[-1])
        self.assertIsNotNone(outcome["windows"]["20"])
        self.assertIsNone(outcome["windows"]["60"])

    def test_duplicate_and_non_finite_are_not_silently_summed(self):
        ds = days(60)
        rows = [(d, {"foreign": 1, "institution": 0, "individual": -1})
                for d in ds]
        rows.append(rows[-1])
        outcome = summarize(rows, ds, asof=ds[-1])
        self.assertIsNone(outcome["windows"]["5"])
        rows = rows[:-1]
        rows[-1] = (rows[-1][0], {"foreign": float("nan"), "institution": 0, "individual": 0})
        self.assertIsNone(summarize(rows, ds, asof=ds[-1])["windows"]["5"])

    def test_no_pre_20_same_day_final_data(self):
        with self.assertRaisesRegex(ValueError, "before 20"):
            collect(asof="2026-11-11", now=datetime(2026, 11, 11, 19, 30,
                                                  tzinfo=timezone(timedelta(hours=9))),
                    stock_api=Mock())

    def test_future_and_stale_dates_blocked(self):
        now = datetime(2026, 11, 11, 20, tzinfo=timezone(timedelta(hours=9)))
        with self.assertRaises(ValueError):
            collect(asof="2026-11-12", now=now, stock_api=Mock())
        with self.assertRaises(ValueError):
            collect(asof="2026-10-31", now=now, stock_api=Mock())


if __name__ == "__main__":
    unittest.main()
