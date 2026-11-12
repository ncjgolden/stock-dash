"""CJ manually sourced close-price evidence review, never an automatic production approval.

Input: two independently sourced normalized files, date,symbol,close.
Output: strict comparison and SHA-256 fingerprints, without trusting filenames,
user-supplied URL, or a self-declared official status as proof of origin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cj_price_reconcile import compare_daily, read_official_closes


def fingerprint(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(65536), b""):
            h.update(data)
    return h.hexdigest()


def review(*, public_path, reference_path, symbol, asof, official_url,
           now=None):
    """Local comparison, explicit provenance gap and safe fail-closed state."""
    public = Path(public_path).resolve(strict=True)
    reference = Path(reference_path).resolve(strict=True)
    if public == reference:
        raise ValueError("Public and official files must be different paths")
    if not public.is_file() or not reference.is_file():
        raise ValueError("Inputs must be regular files")
    local = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if local.tzinfo is None:
        raise ValueError("Timezone-aware now required")
    if date.fromisoformat(asof) > local.astimezone(ZoneInfo("Asia/Seoul")).date():
        raise ValueError("Future trading date")
    public_rows = read_official_closes(public, symbol)
    official_rows = read_official_closes(reference, symbol)
    comparison = compare_daily(
        public_rows, official_rows, asof=asof, official_url=official_url)
    # A perfect match alone does not prove KRX custody, source entitlement or
    # license compliance. Never return an 'approved for production' flag.
    return {
        "status": ("MATCHED_NEEDS_ORIGIN_REVIEW"
                   if comparison["status"] == "MATCHED_SERIES"
                   else "BLOCKED"),
        "comparison_status": comparison["status"],
        "reason": comparison.get("reason"),
        "compared_sessions": comparison.get("sessions", 0),
        "symbol": symbol,
        "asof": asof,
        "reference_url_claim": official_url,
        "public_file_sha256": fingerprint(public),
        "reference_file_sha256": fingerprint(reference),
        "reference_origin_confirmed": False,
        "corporate_actions_checked": False,
        "api_entitlement_checked": False,
        "usable_in_automatic_chatgpt_briefing": False,
        "next_action": ("Independently verify official CSV origin and quote conventions"
                        if comparison["status"] == "MATCHED_SERIES"
                        else "Resolve missing dates, mismatches or invalid source"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--public-csv", required=True)
    p.add_argument("--official-csv", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--asof", required=True)
    p.add_argument("--official-url", required=True)
    args = p.parse_args()
    result = review(
        public_path=args.public_csv, reference_path=args.official_csv,
        symbol=args.symbol, asof=args.asof, official_url=args.official_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "MATCHED_NEEDS_ORIGIN_REVIEW":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
