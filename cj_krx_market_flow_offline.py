"""Read-only offline KRX investor-flow aggregation from a NORMALIZED CSV.

Input format: date,market,foreign_krw,institution_krw,individual_krw
All net flows are KRW integer values, never units of 100 million KRW.
An export claimed to be KRX is NOT automatically source-authenticated.
The reference session calendar is self-contained in the CSV, so computed
windows stay RESEARCH_ONLY until independently reconciled to KRX sessions.
"""
import argparse
import csv
import json
import re
from datetime import date, datetime, time
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from cj_investor_flow import WINDOWS, summarize

KST = ZoneInfo("Asia/Seoul")
MARKETS = ("KOSPI", "KOSDAQ")
FIELDS = ("date", "market", "foreign_krw", "institution_krw", "individual_krw")
INT = re.compile(r"-?(0|[1-9][0-9]*)\Z")


def read_normalized_csv(path):
    markets = {market: {} for market in MARKETS}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Expected exact CSV header: " + ",".join(FIELDS))
        for row in reader:
            try:
                d = date.fromisoformat(row["date"])
            except (TypeError, ValueError):
                raise ValueError("Invalid ISO date") from None
            market = row["market"]
            if market not in MARKETS:
                raise ValueError("Only KOSPI and KOSDAQ markets allowed")
            if d in markets[market]:
                raise ValueError("Duplicate date within a market")
            values = {}
            for investor in ("foreign", "institution", "individual"):
                raw = row[investor + "_krw"]
                if not isinstance(raw, str) or INT.fullmatch(raw) is None:
                    raise ValueError("Net purchases must be integer KRW without commas")
                values[investor] = int(raw)
            markets[market][d] = values
    return markets


def analyze(path, *, asof, generated_at, source_url, finality):
    try:
        asof_date = date.fromisoformat(asof)
        ts = datetime.fromisoformat(generated_at).astimezone(KST)
    except (ValueError, TypeError):
        raise ValueError("Invalid asof or generated_at") from None
    if datetime.fromisoformat(generated_at).tzinfo is None:
        raise ValueError("generated_at requires a timezone")
    url = urlsplit(source_url)
    if not (url.scheme == "https" and url.hostname == "data.krx.co.kr"):
        raise ValueError("KRX source URL required")
    if asof_date > ts.date():
        raise ValueError("Data asof is in the future")
    if finality not in ("PROVISIONAL", "FINAL"):
        raise ValueError("finality must be PROVISIONAL or FINAL")
    if (finality == "FINAL" and asof_date == ts.date()
            and ts.time() < time(20)):
        raise ValueError("Cannot claim same-day investor flow FINAL before 20:00 KST")
    markets = read_normalized_csv(path)
    dates = [set(markets[m]) for m in MARKETS]
    if not dates[0] or not dates[1] or dates[0] != dates[1]:
        raise ValueError("Market session dates absent or inconsistent")
    if max(dates[0]) != asof_date:
        raise ValueError("Latest trading session does not equal asof")
    result = {}
    sessions = sorted(dates[0])
    for market in MARKETS:
        rows = sorted(markets[market].items())
        result[market] = summarize(rows, sessions, asof=asof_date)
    return {
        "asof": asof, "export_observed_at": ts.isoformat(), "source_url": source_url,
        "source_claim": "USER_DECLARED_KRX_EXPORT",
        "source_authentication": "NOT_INDEPENDENTLY_VERIFIED",
        "market_session_calendar": "SELF_REFERENTIAL_NOT_CROSSCHECKED",
        "finality": finality, "unit": "KRW",
        "status": "RESEARCH_ONLY_NEEDS_INDEPENDENT_KRX_SESSION_RECONCILIATION",
        "production_approved": False,
        "results": result,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--asof", required=True)
    p.add_argument("--generated-at", required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument("--finality", choices=("PROVISIONAL", "FINAL"), required=True)
    args = p.parse_args()
    report = analyze(args.file, asof=args.asof, generated_at=args.generated_at,
                     source_url=args.source_url, finality=args.finality)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
