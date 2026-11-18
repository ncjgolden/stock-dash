import unittest
from cj_brief_reporting_priority import (
    HOLDINGS, choose_reporting_mode, check_holdings_coverage,
)

EVIDENCE = {
    "nvidia_results_verified": True,
    "forward_guidance_verified": True,
    "business_continuity_verified": True,
    "no_major_nvidia_event_five_sessions": True,
    "contagion_eased_five_sessions": True,
}


class ReportingPriorityTests(unittest.TestCase):
    def test_unverified_is_not_stable(self):
        self.assertEqual(
            choose_reporting_mode({})["reason"], "STABILIZATION_NOT_VERIFIED")

    def test_all_verified_returns_balanced(self):
        result = choose_reporting_mode(EVIDENCE)
        self.assertEqual(result["mode"], "BALANCED_HOLDINGS")
        self.assertFalse(result["trade_signal"])

    def test_new_risk_overrides_good_history(self):
        result = choose_reporting_mode(dict(EVIDENCE, new_major_nvidia_risk=True))
        self.assertEqual(result["reason"], "NEW_MATERIAL_NVDA_RISK")

    def test_one_false_prevents_exit(self):
        for name in EVIDENCE:
            e = dict(EVIDENCE)
            e[name] = False
            self.assertEqual(choose_reporting_mode(e)["mode"], "NVDA_SPECIAL")

    def test_all_holdings_screen_required(self):
        c = check_holdings_coverage(HOLDINGS, [])
        self.assertTrue(c["screened_all"])
        self.assertFalse(c["trading_authorized"])

    def test_non_nvda_material_event_emerges(self):
        events = [{"symbol": "010120", "verified": True,
                   "category": "contract_loss", "material": True}]
        c = check_holdings_coverage(HOLDINGS[:-1], events)
        self.assertFalse(c["screened_all"])
        self.assertIn("JEPI", c["missing"])
        self.assertEqual(c["material_alerts"][0]["symbol"], "010120")

    def test_unverified_rumor_is_not_alert(self):
        events = [{"symbol": "NVDA", "verified": False,
                   "category": "governance", "material": True}]
        self.assertFalse(check_holdings_coverage(HOLDINGS, events)["material_alerts"])


if __name__ == "__main__":
    unittest.main()
