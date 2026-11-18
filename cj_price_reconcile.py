"""Compare public daily closes against independently exported official close data.

No downloading or claims of verified provenance: user must independently verify
official CSV source, session conventions, corporate actions and quote units.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from cj_market_trends import clean_rows, day

OFFICIAL_DOMAINS = {"data.krx.co.kr", "openapi.krx.co.kr", "www.nasdaq.com", "www.nyse.com",
                    "www.spglobal.com", "www.cboe.com"}


def source_host_allowed(url):
    p = urlsplit(url)
    return p.scheme == "https" and p.hostname in OFFICIAL_DOMAINS and not p.username and not p.password


def read_official_closes(path, symbol):
    """Normalized CSV: date,symbol,close; must be manually reconciled to source units."""
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"date", "symbol", "close"}.issubset(reader.fieldnames or ()):
            raise ValueError("Missing required columns date,symbol,close")
        for item in reader:
            if item["symbol"] == symbol:
                rows.append((day(item["date"]), item["close"]))
    if not rows:
        raise ValueError("No matching symbol")
    return clean_rows(rows, asof=max(day(x) for x, _ in rows))


def compare_daily(public_rows, official_rows, *, asof, official_url, min_sessions=61,
                  rtol=0.00001):
    """Fail closed on mismatches, missing sessions, stale endpoint, split-adjustment."""
    if not source_host_allowed(official_url):
        raise ValueError("Official publication URL required; address alone is not provenance proof")
    if min_sessions < 2:
        raise ValueError("At least two sessions required")
    cutoff = day(asof)
    public = clean_rows(public_rows, asof=cutoff)
    official = clean_rows(official_rows, asof=cutoff)
    report = {"asof": cutoff.isoformat(), "status": "UNVERIFIED",
              "official_url": official_url, "sessions": 0,
              "reason": None, "note": "Source URL not proof that CSV is authentic."}
    if len(official) < min_sessions or len(public) < min_sessions:
        report.update(status="UNKNOWN", reason="INSUFFICIENT_HISTORY")
        return report
    ref = official[-min_sessions:]
    if ref[-1][0] != cutoff:
        report.update(status="UNKNOWN", reason="REFERENCE_ASOF_MISMATCH")
        return report
    lookup = dict(public)
    if any(d not in lookup for d, _ in ref):
        report.update(status="UNKNOWN", reason="MISSING_PUBLIC_SESSIONS")
        return report
    report["sessions"] = len(ref)
    errors = [(d, lookup[d], v) for d, v in ref
              if not math.isclose(lookup[d], v, rel_tol=rtol, abs_tol=1e-8)]
    if errors:
        report.update(status="MISMATCH", reason="PRICE_UNIT_OR_CORPORATE_ACTION_OR_SOURCE")
        return report
    report.update(status="MATCHED_SERIES", reason=None)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--public-csv", required=True, help="Normalized local CSV")
    p.add_argument("--official-csv", required=True, help="Normalized local official export")
    p.add_argument("--symbol", required=True)
    p.add_argument("--official-url", required=True)
    p.add_argument("--asof", required=True)
    args = p.parse_args()
    a = read_official_closes(args.public_csv, args.symbol)
    b = read_official_closes(args.official_csv, args.symbol)
    result = compare_daily(a, b, asof=args.asof, official_url=args.official_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "MATCHED_SERIES":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
