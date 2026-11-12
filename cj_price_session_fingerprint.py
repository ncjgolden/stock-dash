"""Reproducible SHA256 comparisons of 5/20/61 daily closing observations.

No proprietary daily price series uploaded or printed. Not official KRX approval.
Date-and-price digests match only when entire selected daily sequences match.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _price(value):
    if isinstance(value, bool):
        raise ValueError("Boolean close")
    try:
        number = float(str(value).replace(",", ""))
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Malformed close") from None
    if not math.isfinite(number) or number <= 0 or not number.is_integer():
        raise ValueError("Nonpositive, nonfinite or non-integer close")
    return int(number)


def fingerprint(rows, *, symbol, asof):
    asof = _day(asof)
    seen = set()
    clean = []
    for when, close in rows:
        d = _day(when)
        if d > asof:
            continue
        if d in seen:
            raise ValueError("Duplicate trading day")
        seen.add(d)
        clean.append((d, _price(close)))
    clean.sort()
    if len(clean) < 61 or clean[-1][0] != asof:
        raise ValueError("61 completed daily sessions ending on asof required")
    # Use all 61, and narrower blocks for diagnostic pinpointing.
    result = {"symbol": symbol, "asof": asof.isoformat(),
              "status": "HASH_ONLY_UNVERIFIED", "basis": "unadjusted_daily_close",
              "counts": {}}
    for n in (5, 20, 61):
        block = clean[-n:]
        payload = "".join(f"{d.isoformat()},{p}\n" for d, p in block)
        result["counts"][str(n)] = {
            "first_session": block[0][0].isoformat(),
            "last_session": block[-1][0].isoformat(),
            "sessions": n,
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }
    return result


def rows_from_csv(path, symbol):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        rdr = csv.DictReader(handle)
        if not {"date", "symbol", "close"}.issubset(rdr.fieldnames or []):
            raise ValueError("CSV needs date,symbol,close")
        return [(r["date"], r["close"]) for r in rdr if r["symbol"] == symbol]


def public_fdr_rows(symbol, asof, *, reader=None):
    if reader is None:
        import FinanceDataReader as fdr
        reader = fdr.DataReader
    cutoff = _day(asof)
    frame = reader(symbol, (cutoff-timedelta(days=145)).isoformat(),
                   (cutoff+timedelta(days=1)).isoformat())
    if frame is None or frame.empty or "Close" not in frame.columns:
        raise ValueError("FDR missing Close")
    return [(idx, row["Close"]) for idx, row in frame.iterrows()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--asof", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fdr", action="store_true")
    mode.add_argument("--local-csv")
    parser.add_argument("--inspect-tail", type=int, default=0,
                        help="Publish up to 5 recent public closes for diagnostic review")
    args = parser.parse_args()
    if args.inspect_tail < 0 or args.inspect_tail > 5:
        parser.error("--inspect-tail must be 0..5")
    if args.fdr:
        rows = public_fdr_rows(args.symbol, args.asof)
        provider = "FDR_PUBLIC_UNVERIFIED"
    else:
        rows = rows_from_csv(args.local_csv, args.symbol)
        provider = "LOCAL_FILE_ORIGIN_UNVERIFIED"
    result = fingerprint(rows, symbol=args.symbol, asof=args.asof)
    if args.inspect_tail:
        eligible = sorted((_day(d), _price(c)) for d, c in rows if _day(d) <= _day(args.asof))
        result["diagnostic_recent_closes"] = [
            {"date": d.isoformat(), "close": p} for d, p in eligible[-args.inspect_tail:]]
    result["provider"] = provider
    result["not_production_approved"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
