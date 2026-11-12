import unittest
from datetime import datetime, timedelta, timezone

from cj_live_smoke import run


class LiveSmokeTests(unittest.TestCase):
    def test_reports_source_metadata_without_claiming_official_status(self):
        now = datetime(2026, 11, 11, 20, tzinfo=timezone(timedelta(hours=9)))
        def fake_trend(**kwargs):
            label = next(iter(kwargs["symbols"]))
            return {"results": {label: {"status": "DATA_ONLY",
                                       "asof": "2026-11-10",
                                       "returns_pct": {"60": 1.23},
                                       "source": "fixture"}}}
        def fake_flow(**kwargs):
            return {"market_asof": "2026-11-10",
                    "provider": "mock pykrx",
                    "results": {"삼성전자": {"status": "COMPLETE",
                                          "observations": 60,
                                          "windows": {"60": {"foreign_krw": 1}}}}}
        output = run(now=now, flow_fn=fake_flow, trend_fn=fake_trend)
        self.assertEqual(output["requested_asof"], "2026-11-10")
        self.assertEqual(output["connectivity"], "SOURCE_DATA_AVAILABLE_UNVERIFIED")
        self.assertFalse(output["usable_in_chatgpt_briefing"])
        self.assertEqual(output["official_krx_crosscheck"], "NOT_RUN")
        self.assertEqual(output["chatgpt_briefing_connection"], "NOT_CONFIGURED")
        self.assertFalse(output["account_data_used"])
        self.assertTrue(output["checks"]["kr_investor_flow"]["has_60_session_history"])
        self.assertNotIn("1.23", str(output))  # don't leak numerical price signals

    def test_provider_error_sanitized_and_workflow_continues(self):
        def failing(**kwargs):
            raise RuntimeError("unsafe private token must not appear")
        r = run(now=datetime(2026, 11, 11, 20,
                tzinfo=timezone(timedelta(hours=9))),
                flow_fn=failing, trend_fn=failing)
        self.assertEqual(r["checks"]["us_index_trend"]["status"], "UNKNOWN")
        self.assertEqual(r["connectivity"], "DEGRADED")
        self.assertFalse(r["usable_in_chatgpt_briefing"])
        self.assertNotIn("unsafe private token", str(r))


if __name__ == "__main__":
    unittest.main()
