"""CJ optional market-trend evidence using public, unofficial data sources.

Prices are unadjusted daily CLOSE values in native quote units.
Never treat output as official, live, or broker-verified prices.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PERIODS = (5, 20, 60)
SOURCES = {
    "KR": {"KOSPI": ("FDR", "KS11"), "KOSDAQ": ("FDR", "KQ11"),
           "삼성전자": ("FDR", "005930"), "SK하이닉스": ("FDR", "000660")},
    "US": {"S&P500": ("YF", "^GSPC"), "NASDAQ": ("YF", "^IXIC"),
           "NVDA": ("YF", "NVDA"), "GOOGL": ("YF", "GOOGL"),
           "ANET": ("YF", "ANET")},
}


def day(value):
    return value.date() if isinstance(value, datetime) else value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def clean_rows(rows, *, asof):
    """Return validated chronological daily closes, or raise on corrupt data.

    Duplicate session dates or missing/nonfinite/negative closes are rejected.
    """
    asof = day(asof)
    values = {}
    for raw_day, raw_price in rows:
        d = day(raw_day)
        if d > asof:
            continue
        if d in values:
            raise ValueError("Duplicate close date")
        if isinstance(raw_price, bool):
            raise ValueError("Boolean price")
        try:
            p = float(raw_price)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Unusable close") from None
        if not math.isfinite(p) or p <= 0:
            raise ValueError("Nonpositive/nonfinite close")
        values[d] = p
    return sorted(values.items())


def summarize(rows, *, asof, now, market):
    """Exact session-indexed returns; None means UNKNOWN, not a 0% return."""
    if market not in ("KR", "US"):
        raise ValueError("Unknown market")
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    clock = now.astimezone(ZoneInfo("Asia/Seoul"))
    asof = day(asof)
    if asof > clock.date():
        raise ValueError("Future asof")
    if (clock.date() - asof).days > 7:
        raise ValueError("As-of is stale")
    clean = clean_rows(rows, asof=asof)
    if not clean:
        return {"status": "UNKNOWN", "asof": None, "returns_pct": {}, "ma": {}}
    last_day, last = clean[-1]
    if (asof - last_day).days > 7:
        return {"status": "UNKNOWN", "asof": last_day.isoformat(),
                "returns_pct": {str(n): None for n in PERIODS}, "ma": {}}
    if market == "KR" and last_day == clock.date() and clock.hour < 18:
        return {"status": "UNCONFIRMED_TODAY", "asof": last_day.isoformat(),
                "returns_pct": {str(n): None for n in PERIODS}, "ma": {}}
    # A US session bearing today's Korean date could still be open.
    # Do not accept it without an independent closing/market-calendar check.
    if market == "US" and last_day >= clock.date():
        return {"status": "UNCONFIRMED_US_SESSION", "asof": last_day.isoformat(),
                "returns_pct": {str(n): None for n in PERIODS}, "ma": {}}
    prices = [p for _, p in clean]
    returns = {str(n): round((last / prices[-n-1] - 1)*100, 4)
               if len(prices) >= n+1 else None for n in PERIODS}
    moving = {str(n): round(sum(prices[-n:]) / n, 6)
              if len(prices) >= n else None for n in (20, 60)}
    return {"status": "DATA_ONLY" if all(x is not None for x in returns.values())
            else "PARTIAL", "asof": last_day.isoformat(), "close": last,
            "returns_pct": returns, "ma": moving, "unit": "native quote units",
            "validation": "UNOFFICIAL_SOURCE_NOT_CROSSCHECKED"}


def _rows(frame):
    if frame is None or frame.empty or "Close" not in frame.columns:
        raise ValueError("Missing daily Close column")
    return [(d, row["Close"]) for d, row in frame.iterrows()]


def collect(*, market, asof, now=None, fdr=None, yf=None, symbols=None):
    """Best effort market evidence. No private records, writes or orders."""
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if now.tzinfo is None:
        raise ValueError("Timezone-aware now required")
    asof = day(asof)
    if asof > now.astimezone(ZoneInfo("Asia/Seoul")).date():
        raise ValueError("Future asof")
    targets = symbols or SOURCES[market]
    since = (asof - timedelta(days=135)).isoformat()
    until = (asof + timedelta(days=1)).isoformat()
    results = {}
    for label, (source, symbol) in targets.items():
        try:
            if source == "FDR":
                if fdr is None:
                    import FinanceDataReader as fdr
                frame = fdr.DataReader(symbol, since, until)
            elif source == "YF":
                if yf is None:
                    import yfinance as yf
                frame = yf.Ticker(symbol).history(start=since, end=until,
                                                  interval="1d", auto_adjust=False)
            else:
                raise ValueError("Unsupported provider")
            result = summarize(_rows(frame), asof=asof, now=now, market=market)
            result.update({"source": "FinanceDataReader" if source=="FDR" else "yfinance",
                           "symbol": symbol})
            results[label] = result
        except (ImportError, ValueError, KeyError, TypeError, RuntimeError, OSError) as error:
            results[label] = {"status": "UNKNOWN", "source": source, "symbol": symbol,
                              "error": type(error).__name__}
    return {"market": market, "requested_asof": asof.isoformat(),
            "collected_at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
            "results": results,
            "disclaimer": "Public data, NOT official KRX/SEC verified; returns not trading instructions."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=("KR","US"), required=True)
    parser.add_argument("--asof", required=True)
    args = parser.parse_args()
    print(json.dumps(collect(market=args.market, asof=args.asof),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
