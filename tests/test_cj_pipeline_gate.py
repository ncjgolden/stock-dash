import unittest
from datetime import date, timedelta

from cj_pipeline_gate import run_stages


def evidence():
    values = {"foreign_krw": 500000000, "institution_krw": -200000000,
              "individual_krw": -300000000}
    return {"asof": "2026-11-10", "unit": "KRW",
            "verification": "MATCHED_60_SESSIONS",
            "official_url": "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd",
            "windows": {str(n): {"status": "MATCHED", "values": {k: v*n for k,v in values.items()}}
                        for n in (5,20,60)}}


def accounts():
    return {"observed_at": "2026-11-10T16:30:00+09:00",
            "fx": {"KRW": 1, "USD": 1400},
            "cash": [{"account": a, "amount": 100, "currency": "KRW"}
                     for a in ("ISA", "GENERAL", "OVERSEAS")],
            "positions": [
                {"account": "ISA", "symbol": "005930", "quantity": 1,
                 "price": 100, "currency": "KRW"},
                {"account": "GENERAL", "symbol": "005930", "quantity": 2,
                 "price": 100, "currency": "KRW"},
                {"account": "OVERSEAS", "symbol": "NVDA", "quantity": 1,
                 "price": 10, "currency": "USD"}],
            "valuation_history": [
                {"date": "2026-11-09", "nav_krw": 100, "external_flow_krw": 0},
                {"date": "2026-11-10", "nav_krw": 200, "external_flow_krw": 100}]}


class GatedPipelineTests(unittest.TestCase):
    def test_no_evidence_never_auto_advances(self):
        r = run_stages()
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(len(r["stages"]), 1)
        self.assertIsNone(r["brief"])

    def test_partial_comparison_blocks_all_later_steps(self):
        e = evidence()
        e["windows"]["60"]["status"] = "UNKNOWN"
        r = run_stages(e, accounts())
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(len(r["stages"]), 1)

    def test_valid_comparison_without_accounts_reaches_only_public_stage(self):
        r = run_stages(evidence())
        self.assertEqual(r["status"], "PUBLIC_BRIEF_ONLY")
        self.assertIn("5거래일", r["brief"])
        self.assertIsNone(r["portfolio"])
        self.assertEqual(r["stages"][-1]["status"], "BLOCKED")

    def test_all_synthetic_fixtures_pass_nonproduction_gate(self):
        r = run_stages(evidence(), accounts())
        self.assertEqual(r["status"], "READY_FOR_MANUAL_REVIEW")
        self.assertTrue(r["portfolio"]["concentration_top3_pct"])
        self.assertFalse(r["portfolio"]["sector_exposure_complete"])
        self.assertEqual(r["portfolio"]["drawdown_pct"], 0)
        self.assertEqual(len(r["stages"]), 3)

    def test_invalid_account_data_stops_private_stage(self):
        a = accounts()
        del a["fx"]["USD"]
        r = run_stages(evidence(), a)
        self.assertEqual(r["status"], "PUBLIC_BRIEF_ONLY")
        self.assertIsNone(r["portfolio"])

    def test_unverified_label_is_rejected_even_with_values(self):
        e = evidence()
        e["verification"] = "UNVERIFIED"
        self.assertEqual(run_stages(e, accounts())["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
