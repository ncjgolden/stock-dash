import unittest
from datetime import date
from unittest.mock import Mock

from cj_krx_official_price import (
    parse_official_response, fetch_official_daily_close, collect_official_prices
)


class OfficialKRXPriceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 11, 11)
        self.payload = {"OutBlock_1": [
            {"BAS_DD": "20261111", "ISU_CD": "005930", "TDD_CLSPRC": "93,100"},
            {"BAS_DD": "20261111", "ISU_CD": "000660", "TDD_CLSPRC": "201,000"},
        ]}

    def test_exact_date_and_symbol_validation(self):
        self.assertEqual(parse_official_response(
            self.payload, expected_date=self.day, symbol="005930"), 93100)
        with self.assertRaises(ValueError):
            parse_official_response(self.payload, expected_date=self.day, symbol="111111")
        bad = {"OutBlock_1": [dict(self.payload["OutBlock_1"][0], BAS_DD="20261110")]}
        with self.assertRaises(ValueError):
            parse_official_response(bad, expected_date=self.day, symbol="005930")

    def test_missing_key_does_not_attempt_network(self):
        session = Mock()
        with self.assertRaises(RuntimeError):
            fetch_official_daily_close(self.day, "005930", auth_key="", session=session)
        # Production environment secrets aren't required for test, unless accidentally configured.
        # The unit test never sends a real network request.
        session.get.assert_not_called()

    def test_injected_session_keeps_auth_header_private(self):
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = self.payload
        result = fetch_official_daily_close(self.day, "005930",
                                           auth_key="test_key_only", session=session)
        self.assertEqual(result, 93100)
        self.assertEqual(session.get.call_args.kwargs["headers"]["AUTH_KEY"], "test_key_only")

    def test_non_200_fails_without_body_logging(self):
        session = Mock()
        session.get.return_value.status_code = 401
        session.get.return_value.text = "a private secret"
        with self.assertRaisesRegex(RuntimeError, "did not return HTTP 200") as context:
            fetch_official_daily_close(self.day, "005930", auth_key="fake", session=session)
        self.assertNotIn("private secret", str(context.exception))

    def test_unexpected_schema_fails_closed(self):
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {"something": []}
        with self.assertRaises(RuntimeError):
            fetch_official_daily_close(self.day, "005930", auth_key="fake", session=session)

    def test_missed_holiday_does_not_get_fabricated(self):
        def fake_fetcher(d, symbol):
            if d.day == 11:
                raise RuntimeError("Exchange holiday")
            return 1000
        value = collect_official_prices(symbol="005930", end="2026-11-12",
                                       lookback_calendar_days=2, fetcher=fake_fetcher)
        self.assertEqual(len(value["rows"]), 1)
        self.assertEqual(value["skipped_or_failed_sessions"], 1)


if __name__ == "__main__":
    unittest.main()
