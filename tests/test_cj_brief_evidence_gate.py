import unittest
from copy import deepcopy

from cj_brief_evidence_gate import validate_packet


class BriefEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.packet = {
            "report_at": "2026-11-17T18:30:00+09:00", "mode": "PM",
            "market_status": "OPEN", "market_calendar_source": "https://data.krx.co.kr/",
            "checked_markets": ["KOSPI", "KOSDAQ"],
            "readings": [{
                "name": "KOSPI", "value": 5100.50, "state": "FINAL",
                "source_type": "KRX", "source_url": "https://data.krx.co.kr/",
                "observed_at": "2026-11-17T15:30:00+09:00",
                "published_at": "2026-11-17T16:00:00+09:00",
            }],
        }

    def check_error(self, packet, expected):
        result = validate_packet(packet)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn(expected, result["errors"])
        self.assertFalse(result["production_approved"])

    def test_valid_synthetic_metadata_does_not_approve_production(self):
        result = validate_packet(self.packet)
        self.assertEqual(result["status"], "EVIDENCE_CHECKS_PASSED_NOT_OFFICIAL_APPROVAL")
        self.assertFalse(result["production_approved"])

    def test_holiday_without_calendar_is_rejected(self):
        p = deepcopy(self.packet)
        p["market_status"] = "CLOSED"
        p["market_calendar_source"] = ""
        self.check_error(p, "UNVERIFIED_HOLIDAY_DECLARATION")

    def test_unverified_external_provider_price_is_blocked(self):
        p = deepcopy(self.packet)
        p["readings"][0].update(
            symbol="005930", source_provider="FinanceDataReader")
        self.check_error(p, "KNOWN_KRX_FDR_MISMATCH")

    def test_future_publication_is_blocked(self):
        p = deepcopy(self.packet)
        p["readings"][0]["published_at"] = "2026-11-18T10:30:00+09:00"
        self.check_error(p, "FUTURE_EVIDENCE")

    def test_unknown_cannot_have_number(self):
        p = deepcopy(self.packet)
        p["readings"][0].update(state="UNKNOWN", value=52)
        self.check_error(p, "UNKNOWN_WITH_VALUE")

    def test_secondary_cannot_claim_official(self):
        p = deepcopy(self.packet)
        p["readings"][0].update(
            source_type="NEWS_KRX_CITED", source_confirmed_official=True)
        self.check_error(p, "SECONDARY_SOURCE_NOT_OFFICIAL")

    def test_eighteen_thirty_cannot_claim_final_krx_investor_flow(self):
        p = deepcopy(self.packet)
        p["readings"][0].update(name="KRX_STOCK_INVESTOR_FINAL")
        self.check_error(p, "BEFORE_KRX_FINAL_PUBLICATION")

    def test_direct_trading_is_blocked(self):
        p = deepcopy(self.packet)
        p["direct_trading_enabled"] = True
        self.check_error(p, "UNAUTHORIZED_TRADING")

    def test_pm_market_coverage_required(self):
        p = deepcopy(self.packet)
        p["checked_markets"] = ["KOSPI"]
        self.check_error(p, "MISSING_MARKET_COVERAGE")

    def test_naive_datetime_rejected(self):
        p = deepcopy(self.packet)
        p["report_at"] = "2026-11-17T18:30:00"
        self.check_error(p, "INVALID_REPORT_TIMESTAMP")

    def test_old_report_not_auto_linked(self):
        p = deepcopy(self.packet)
        p["chatgpt_integration_claimed"] = True
        self.check_error(p, "UNVERIFIED_CHATGPT_INTEGRATION")


if __name__ == "__main__":
    unittest.main()
