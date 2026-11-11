"""CJ briefing: validated KRX investor net-trading flows (KRW), read-only.

Optional data adapter: pykrx. It uses public site data, not an official KRX API.
No user accounts, holdings, order endpoints, or scheduled jobs are accessed.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

WINDOWS = (5, 20, 60)
COLUMNS = {"foreign": "외국인합계", "institution": "기관합계", "individual": "개인"}
DEFAULT_TARGETS = {"KOSPI": "KOSPI", "KOSDAQ": "KOSDAQ",
                   "삼성전자": "005930", "SK하이닉스": "000660"}


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _valid_number(value):
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def summarize(rows, reference_dates, *, asof):
    """Return exact 5/20/60-session net sums in KRW or None, never partial sums.

    rows: mapping date -> {'foreign': integer KRW, 'institution': ..., 'individual': ...}
    reference_dates: sorted session dates from KOSPI market (not calendar days).
    Missing, duplicate, invalid, or inconsistent observations invalidate their windows.
    """
    asof = _date(asof)
    days = sorted({_date(d) for d in reference_dates if _date(d) <= asof})
    if not days:
        return {"asof": None, "status": "UNKNOWN", "windows": {}}
    seen = set()
    normalized = {}
    invalid = set()
    for raw_day, values in rows:
        day = _date(raw_day)
        if day in seen:
            invalid.add(day)
        seen.add(day)
        if not isinstance(values, dict) or any(
                key not in values or not _valid_number(values[key]) for key in COLUMNS):
            invalid.add(day)
            continue
        normalized[day] = {key: int(values[key]) if float(values[key]).is_integer()
                           else float(values[key]) for key in COLUMNS}
    windows = {}
    for count in WINDOWS:
        part = days[-count:] if len(days) >= count else []
        complete = bool(part) and all(d in normalized and d not in invalid for d in part)
        windows[str(count)] = (
            {key + "_krw": sum(normalized[d][key] for d in part) for key in COLUMNS}
            if complete else None
        )
    last = days[-1]
    return {"asof": last.isoformat(), "status": "COMPLETE" if all(windows.values()) else "PARTIAL",
            "unit": "KRW", "windows": windows,
            "observations": len(normalized),
            "reference_sessions": len(days)}


def _records(df):
    result = []
    for idx, row in df.iterrows():
        values = {key: row.get(column) for key, column in COLUMNS.items()}
        result.append((idx, values))
    return result


def collect(*, asof, now=None, targets=None, stock_api=None):
    """Read pykrx data. Never label same-day data final before 18:00 KST."""
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    local = now.astimezone(ZoneInfo("Asia/Seoul"))
    asof = _date(asof)
    if asof > local.date():
        raise ValueError("Future asof date is not allowed")
    if asof == local.date() and local.hour < 18:
        raise ValueError("Same-day KRX investor flow is not final before 18:00 KST")
    if (local.date() - asof).days > 7:
        raise ValueError("Source date is over seven calendar days old")
    if stock_api is None:
        try:
            from pykrx import stock as stock_api
        except ImportError as exc:
            raise RuntimeError("Install optional pykrx: pip install -r requirements-brief.txt") from exc
    targets = targets or DEFAULT_TARGETS
    since = (asof - timedelta(days=135)).strftime("%Y%m%d")
    end = asof.strftime("%Y%m%d")

    # The market calendar is the common denominator: never silently add an
    # incomplete security time series to a 60-session 'total'.
    reference = stock_api.get_market_trading_value_by_date(since, end, "KOSPI", on="순매수")
    reference_dates = list(reference.index)
    if not reference_dates:
        raise RuntimeError("KRX session reference missing; do not publish flows")
    last_reference = max(_date(d) for d in reference_dates)
    if (asof - last_reference).days > 7:
        raise RuntimeError("KRX market reference stale; do not publish flows")
    results = {}
    for name, code in targets.items():
        try:
            frame = (reference if code == "KOSPI" else stock_api.get_market_trading_value_by_date(
                since, end, code, on="순매수"))
            results[name] = summarize(_records(frame), reference_dates, asof=asof)
            # Reject mismatched latest market/session dates, rather than imply
            # last week's trading is today's close.
            if last_reference != asof and asof.weekday() < 5:
                results[name]["status"] = "STALE_REFERENCE"
                results[name]["windows"] = {str(w): None for w in WINDOWS}
        except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as error:
            results[name] = {"status": "UNKNOWN", "error": type(error).__name__,
                             "windows": {str(w): None for w in WINDOWS}}
    return {
        "requested_asof": asof.isoformat(),
        "market_asof": last_reference.isoformat(),
        "collected_at_kst": local.isoformat(),
        "data_kind": "investor_net_trading_value",
        "unit": "KRW",
        "provider": "pykrx (public site data; NOT official KRX API)",
        "finality": "POST_18_KST_SOURCE_CHECK_REQUIRED",
        "results": results,
        "notice": "Validate critical numbers against KRX data; unavailable windows are UNKNOWN.",
    }


def main():
    parser = argparse.ArgumentParser(description="Read-only investor-flow evidence for CJ briefs")
    parser.add_argument("--asof", required=True, help="Korean trading date YYYY-MM-DD")
    args = parser.parse_args()
    print(json.dumps(collect(asof=args.asof), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
