"""Optional KRX Open API official daily-close adapter, for private/local use only.

Requires user's individually approved KRX AUTH_KEY; does not download investor
flows (KRX day-trading quote endpoints do not supply investor categories).
Nothing is uploaded, logged, stored, or posted to ChatGPT by this module.
"""
from __future__ import annotations

import argparse
import csv
import os
from datetime import date, timedelta
from pathlib import Path

ENDPOINT = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"


def _parse_price(raw):
    import math
    cleaned = str(raw).strip().replace(",", "")
    try:
        value = float(cleaned)
    except (TypeError, ValueError):
        raise ValueError("KRX official close is nonnumeric") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError("KRX official close is invalid")
    return value


def parse_official_response(payload, *, expected_date, symbol):
    """Parse KRX OpenAPI daily market rows, strictly matching date & stock code."""
    if not isinstance(payload, dict):
        raise ValueError("Unexpected KRX response type")
    items = payload.get("OutBlock_1")
    if not isinstance(items, list):
        raise ValueError("Missing KRX OutBlock_1 list")
    matches = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_code = str(item.get("ISU_CD", "")).strip()
        # ISU_CD may be standard short ticker or ISIN; never guess a match.
        if raw_code != symbol:
            continue
        observed = str(item.get("BAS_DD", "")).replace("-", "").strip()
        if observed != expected_date.strftime("%Y%m%d"):
            raise ValueError("Official price date mismatch")
        matches.append(_parse_price(item.get("TDD_CLSPRC")))
    if len(matches) != 1:
        raise ValueError("Missing or duplicate KRX official stock/date")
    return matches[0]


def fetch_official_daily_close(day, symbol, *, auth_key=None, session=None):
    """One approved service/date; raises if key, response or symbol invalid."""
    day = date.fromisoformat(str(day))
    if not (len(symbol) == 6 and symbol.isascii() and symbol.isdigit()):
        raise ValueError("Six digit numeric Korean ticker required")
    key = auth_key or os.getenv("KRX_AUTH_KEY")
    if not key:
        raise RuntimeError("KRX_AUTH_KEY not configured locally; no official comparison possible")
    if session is None:
        import requests
        session = requests
    response = session.get(
        ENDPOINT,
        params={"basDd": day.strftime("%Y%m%d")},
        headers={"AUTH_KEY": key, "Accept": "application/json"},
        timeout=15,
    )
    if response.status_code != 200:
        # Do not include HTTP response body or request headers in diagnostics.
        raise RuntimeError("KRX API did not return HTTP 200")
    try:
        return parse_official_response(response.json(), expected_date=day, symbol=symbol)
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("KRX API returned unusable or unapproved data") from None


def collect_official_prices(*, symbol, end, lookback_calendar_days=110,
                            fetcher=fetch_official_daily_close):
    """Manual research tool; never silently fill missing trading sessions.

    This daily endpoint requires one call per date. Limit requests; never
    assume weekends/holidays are valid market dates. Caller handles rate limits.
    """
    if lookback_calendar_days < 1 or lookback_calendar_days > 125:
        raise ValueError("Lookback must be 1..125 calendar days")
    end = date.fromisoformat(str(end))
    values = []
    errors = 0
    for offset in range(lookback_calendar_days, -1, -1):
        d = end - timedelta(days=offset)
        if d.weekday() > 4:
            continue
        try:
            close = fetcher(d, symbol)
        except (ValueError, RuntimeError, OSError):
            errors += 1
            continue
        values.append((d.isoformat(), close))
    return {"symbol": symbol, "asof": end.isoformat(),
            "rows": values, "skipped_or_failed_sessions": errors,
            "verified_origin": "CLAIMED_KRX_API_CHECK_ACCESS_AND_ENTITLEMENT",
            "note": "Missing official trading dates must be checked manually; do not use as final until validated."}


def main():
    parser = argparse.ArgumentParser(description="Local KRX official stock close export; no public logs")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--out", required=True, help="Private output path outside repository")
    args = parser.parse_args()
    if not os.getenv("KRX_AUTH_KEY"):
        raise SystemExit("KRX_AUTH_KEY missing: no official data read performed")
    output = collect_official_prices(symbol=args.symbol, end=args.asof)
    out = Path(args.out)
    if out.exists():
        raise SystemExit("Refusing to overwrite existing official CSV")
    # Refuse export inside a Git working tree to reduce accidental disclosure.
    import subprocess
    cwd = Path.cwd().resolve()
    if out.resolve().is_relative_to(cwd):
        raise SystemExit("Official CSV must be outside repository directory")
    if len(output["rows"]) < 61:
        raise SystemExit("Not enough historical official sessions; output omitted")
    with out.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "close"])
        for d, close in output["rows"]:
            writer.writerow([d, args.symbol, close])
    print("Official export completed locally; source, days and units still require manual review.")


if __name__ == "__main__":
    main()
