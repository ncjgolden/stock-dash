"""Fail-closed checks for externally sourced CJ market briefing inputs.

This gates structured evidence, not AI prose or end-to-end ChatGPT delivery.
No market access, orders, credentials, or portfolio balances.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
APPROVED_TYPES = {"KRX", "DART", "SEC", "COMPANY_IR", "OFFICIAL_GOV"}
EXTERNAL_TYPES = {"NEWS_KRX_CITED", "BROKER_KRX_CITED"}
ALL_TYPES = APPROVED_TYPES | EXTERNAL_TYPES
VALID_STATES = {"FINAL", "PROVISIONAL", "UNKNOWN"}
BANNED_FDR_KR_STOCKS = {"005930"}
REQUIRED_MARKETS = {"KOSPI", "KOSDAQ"}


def _parse_time(value):
    instant = datetime.fromisoformat(str(value))
    if instant.tzinfo is None:
        raise ValueError("Timestamp must be timezone aware")
    return instant.astimezone(KST)


def validate_packet(packet):
    """Validate evidence without asserting trading-day or official verification."""
    errors = []
    try:
        report_at = _parse_time(packet["report_at"])
    except (KeyError, ValueError, TypeError):
        return {"status": "BLOCKED", "errors": ["INVALID_REPORT_TIMESTAMP"],
                "production_approved": False}
    mode = packet.get("mode")
    if mode not in ("AM", "PM"):
        errors.append("INVALID_MODE")
    if packet.get("market_status") not in ("OPEN", "CLOSED", "UNKNOWN"):
        errors.append("INVALID_MARKET_STATUS")
    if packet.get("market_status") == "CLOSED" and not packet.get("market_calendar_source"):
        errors.append("UNVERIFIED_HOLIDAY_DECLARATION")
    if packet.get("market_status") == "OPEN" and not packet.get("market_calendar_source"):
        errors.append("UNVERIFIED_OPEN_DECLARATION")
    readings = packet.get("readings", [])
    if not isinstance(readings, list):
        readings = []
        errors.append("INVALID_READINGS")
    seen = set()
    for reading in readings:
        if not isinstance(reading, dict):
            errors.append("INVALID_READING")
            continue
        name = reading.get("name")
        if not name or name in seen:
            errors.append("DUPLICATE_OR_MISSING_METRIC")
        seen.add(name)
        state = reading.get("state")
        if state not in VALID_STATES:
            errors.append("INVALID_STATE")
            continue
        if state == "UNKNOWN":
            if reading.get("value") is not None:
                errors.append("UNKNOWN_WITH_VALUE")
            continue
        if reading.get("value") is None:
            errors.append("MISSING_VALUE")
        if reading.get("source_type") not in ALL_TYPES or not reading.get("source_url"):
            errors.append("MISSING_SOURCE")
        try:
            published = _parse_time(reading["published_at"])
            observed = _parse_time(reading["observed_at"])
        except (KeyError, ValueError, TypeError):
            errors.append("INVALID_EVIDENCE_TIMESTAMP")
            continue
        if published > report_at or observed > report_at:
            errors.append("FUTURE_EVIDENCE")
        if observed.date() > report_at.date():
            errors.append("FUTURE_MARKET_SESSION")
        if (reading.get("source_type") in EXTERNAL_TYPES
                and reading.get("source_confirmed_official") is True):
            errors.append("SECONDARY_SOURCE_NOT_OFFICIAL")
        if (reading.get("symbol") in BANNED_FDR_KR_STOCKS
                and reading.get("source_provider") == "FinanceDataReader"):
            errors.append("KNOWN_KRX_FDR_MISMATCH")
        if reading.get("name") == "KRX_STOCK_INVESTOR_FINAL" and (
                state == "FINAL" and published.date() == report_at.date()
                and report_at.time() < time(20, 0)):
            errors.append("BEFORE_KRX_FINAL_PUBLICATION")
    if mode == "PM" and packet.get("market_status") == "OPEN":
        if not REQUIRED_MARKETS.issubset(set(packet.get("checked_markets", []))):
            errors.append("MISSING_MARKET_COVERAGE")
    if packet.get("direct_trading_enabled"):
        errors.append("UNAUTHORIZED_TRADING")
    if packet.get("chatgpt_integration_claimed"):
        errors.append("UNVERIFIED_CHATGPT_INTEGRATION")
    return {"status": "BLOCKED" if errors else "EVIDENCE_CHECKS_PASSED_NOT_OFFICIAL_APPROVAL",
            "errors": sorted(set(errors)), "production_approved": False,
            "checked_metrics": len(readings)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, help="Private/local JSON input")
    args = parser.parse_args()
    with open(args.packet, encoding="utf-8") as fp:
        packet = json.load(fp)
    result = validate_packet(packet)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
