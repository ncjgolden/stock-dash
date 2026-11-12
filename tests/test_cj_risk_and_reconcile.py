import unittest
from datetime import date, timedelta

from cj_official_reconcile import official_source, parse_csv, reconcile
from cj_portfolio_risk import snapshot, adjusted_index


class OfficialReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.days = [date(2026, 8, 1) + timedelta(days=i) for i in range(60)]
        self.rows = [(d, {"foreign": 1000, "institution": -400, "individual": -600})
                     for d in self.days]
        self.official = dict(self.rows)
        self.url = "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd"

    def test_official_host_allowlist(self):
        self.assertTrue(official_source(self.url))
        self.assertFalse(official_source("https://data.krx.co.kr.evil.invalid/file"))
        self.assertFalse(official_source("http://data.krx.co.kr/file"))

    def test_exact_reconciliation(self):
        r = reconcile(self.rows, self.official, self.days, asof=self.days[-1],
                      official_url=self.url)
        self.assertEqual(r["verification"], "MATCHED_60_SESSIONS")
        self.assertEqual(r["windows"]["60"]["values"]["foreign_krw"], 60000)

    def test_mismatch_fail_closed(self):
        official = dict(self.official)
        official[self.days[-1]] = dict(official[self.days[-1]], foreign=999)
        r = reconcile(self.rows, official, self.days, asof=self.days[-1],
                      official_url=self.url)
        self.assertEqual(r["windows"]["5"]["status"], "MISMATCH")
        self.assertIsNone(r["windows"]["5"]["values"])
        self.assertEqual(r["verification"], "PARTIAL_OR_FAILED")

    def test_missing_official_date_yields_unknown(self):
        official = dict(self.official)
        del official[self.days[-1]]
        r = reconcile(self.rows, official, self.days, asof=self.days[-1],
                      official_url=self.url)
        self.assertEqual(r["windows"]["20"]["status"], "UNKNOWN")

    def test_invalid_source_fails(self):
        with self.assertRaises(ValueError):
            reconcile(self.rows, self.official, self.days, asof=self.days[-1],
                      official_url="https://example.com/fake-official.csv")


class PortfolioRiskTests(unittest.TestCase):
    def test_duplicate_symbol_is_combined_across_accounts(self):
        p = [
            dict(account="ISA", symbol="005930", quantity=2, price=100,
                 currency="KRW", sector="semiconductor"),
            dict(account="GENERAL", symbol="005930", quantity=3, price=100,
                 currency="KRW", sector="semiconductor"),
            dict(account="OVERSEAS", symbol="NVDA", quantity=1, price=5,
                 currency="USD", sector="semiconductor"),
        ]
        cash = [dict(account=a, amount=100, currency="KRW") for a in
                ["ISA", "GENERAL", "OVERSEAS"]]
        r = snapshot(p, cash, {"KRW": 1, "USD": 1400},
                     observed_at="2026-11-11T16:30:00+09:00")
        self.assertEqual(r["holdings"]["005930"]["value_krw"], 500)
        self.assertEqual(r["holdings"]["NVDA"]["value_krw"], 7000)
        self.assertEqual(r["total_nav_krw"], 7800)

    def test_missing_cash_does_not_report_weight(self):
        with self.assertRaises(ValueError):
            snapshot([dict(account="GENERAL", symbol="AAA", quantity=1, price=100,
                           currency="KRW")],
                     [dict(account="ISA", amount=1, currency="KRW")],
                     {"KRW": 1}, observed_at="2026-11-11")

    def test_missing_fx_is_an_error(self):
        with self.assertRaises(KeyError):
            snapshot([dict(account="OVERSEAS", symbol="NVDA", quantity=1, price=10,
                           currency="USD")],
                     [dict(account=a, amount=0, currency="KRW") for a in ["ISA", "GENERAL", "OVERSEAS"]],
                     {"KRW": 1}, observed_at="2026-11-11")

    def test_cashflow_adjusted_index_not_cost_basis_loss(self):
        r = adjusted_index([
            dict(date="2026-11-09", nav_krw=100, external_flow_krw=0),
            dict(date="2026-11-10", nav_krw=200, external_flow_krw=100),
            dict(date="2026-11-11", nav_krw=170, external_flow_krw=0),
        ])
        self.assertEqual(r["series"][1]["index"], 100)
        self.assertEqual(r["current_drawdown_pct"], -15)
        self.assertTrue(r["review_minus_10_pct"])
        self.assertFalse(r["review_minus_20_pct"])

    def test_missing_flows_cannot_assume_zero(self):
        with self.assertRaises(ValueError):
            adjusted_index([dict(date="2026-11-09", nav_krw=100, external_flow_krw=0),
                            dict(date="2026-11-10", nav_krw=90)])


if __name__ == "__main__":
    unittest.main()
