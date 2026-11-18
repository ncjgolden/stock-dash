"""Compare daily pykrx investor flows with user-exported official KRX daily CSV.

Read-only, fail-closed. A verified label applies only to compared dates/columns,
not to the completeness of a market-wide dataset or the timing of official release.
"""
import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from cj_investor_flow import COLUMNS, WINDOWS, _date, _valid_number, summarize

OFFICIAL_HOSTS = {"data.krx.co.kr", "openapi.krx.co.kr", "kind.krx.co.kr"}
KEYS = tuple(COLUMNS)


def official_source(url):
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS


def parse_csv(path, target):
    """CSV with date,target,foreign_krw,institution_krw,individual_krw.

    Official export requires a user-specified source URL outside the file.
    All numeric cells are integer KRW. No anonymized estimates are accepted.
    """
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"date", "target", *(x + "_krw" for x in KEYS)}
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("Missing required official CSV columns")
        for row in reader:
            if row["target"] != target:
                continue
            day = _date(row["date"])
            if day in result:
                raise ValueError("Duplicate official CSV date")
            values = {}
            for key in KEYS:
                raw = (row[key + "_krw"] or "").strip()
                if not raw or not raw.lstrip("-").isdigit():
                    raise ValueError("Official CSV amounts must be integer KRW")
                values[key] = int(raw)
            result[day] = values
    if not result:
        raise ValueError("Official CSV contains no matching target")
    return result


def reconcile(pykrx_rows, official_rows, reference_dates, *, asof, official_url):
    if not official_source(official_url):
        raise ValueError("An HTTPS official KRX source URL is required")
    asof = _date(asof)
    sessions = sorted({_date(day) for day in reference_dates if _date(day) <= asof})
    ours = {}
    duplicates = set()
    for raw_day, values in pykrx_rows:
        day = _date(raw_day)
        if day in ours:
            duplicates.add(day)
        ours[day] = values
    report = {"asof": asof.isoformat(), "official_url": official_url,
              "verification": "UNVERIFIED", "unit": "KRW", "windows": {}}
    for n in WINDOWS:
        span = sessions[-n:] if len(sessions) >= n else []
        if (not span or span[-1] != asof or any(
                day in duplicates or day not in ours or day not in official_rows
                for day in span)):
            report["windows"][str(n)] = {"status": "UNKNOWN", "values": None}
            continue
        if any(not isinstance(ours[d], dict)
               or any(k not in ours[d] or not _valid_number(ours[d][k])
                      or float(ours[d][k]) != official_rows[d][k] for k in KEYS)
               for d in span):
            report["windows"][str(n)] = {"status": "MISMATCH", "values": None}
            continue
        # All rows matched the official export. Never sum partial observations.
        official_series = [(d, official_rows[d]) for d in span]
        sums = summarize(official_series, span, asof=asof)["windows"][str(n)]
        report["windows"][str(n)] = {"status": "MATCHED", "values": sums}
    report["verification"] = (
        "MATCHED_60_SESSIONS" if report["windows"]["60"]["status"] == "MATCHED"
        else "PARTIAL_OR_FAILED"
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--official-csv", required=True)
    ap.add_argument("--official-url", required=True)
    args = ap.parse_args()
    from pykrx import stock
    asof = date.fromisoformat(args.asof)
    from datetime import timedelta
    since, end = (asof-timedelta(days=135)).strftime("%Y%m%d"), asof.strftime("%Y%m%d")
    ref = stock.get_market_trading_value_by_date(since, end, "KOSPI", on="순매수")
    data = stock.get_market_trading_value_by_date(since, end, args.target, on="순매수")
    rows = [(idx, {key: row.get(col) for key, col in COLUMNS.items()})
            for idx, row in data.iterrows()]
    official = parse_csv(args.official_csv, args.target)
    report = reconcile(rows, official, list(ref.index), asof=asof,
                       official_url=args.official_url)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["verification"] != "MATCHED_60_SESSIONS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
