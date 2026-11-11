"""CJ staged readiness gate, with no credentials, private data or live trading.

Stages are intentionally sequential and fail closed:
  1. Data crosscheck with explicitly supplied KRX-export comparison evidence.
  2. Brief packet formatting only from passing comparison.
  3. Portfolio risk check only from complete locally supplied account snapshot.
No stage uploads private input or changes scheduled ChatGPT notifications.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from cj_brief_packet import concise
from cj_portfolio_risk import adjusted_index, snapshot


def run_stages(report=None, account_data=None, *, target="KOSPI"):
    stages = []
    result = {"status": "BLOCKED", "stages": stages,
              "brief": None, "portfolio": None,
              "warning": "Synthetic or user-supplied comparisons are not authenticated KRX exports."}
    if not isinstance(report, dict) or report.get("verification") != "MATCHED_60_SESSIONS":
        stages.append({"name": "official_daily_comparison", "status": "BLOCKED",
                       "reason": "60-session reconciled source not supplied"})
        return result
    windows = report.get("windows", {})
    if (report.get("unit") != "KRW"
            or any(windows.get(str(n), {}).get("status") != "MATCHED" for n in (5, 20, 60))
            or not report.get("official_url")
            or not report.get("asof")):
        stages.append({"name": "official_daily_comparison", "status": "BLOCKED",
                       "reason": "Incomplete provenance or window verification"})
        return result
    try:
        date.fromisoformat(report["asof"])
        # Full verification of the actual official export still requires trusted ingestion.
        brief = concise(report, target=target)
    except (ValueError, KeyError, TypeError):
        stages.append({"name": "official_daily_comparison", "status": "BLOCKED",
                       "reason": "Unrecognized evidence format"})
        return result
    stages.append({"name": "official_daily_comparison", "status": "PASSED_COMPARISON_ONLY"})
    result["brief"] = brief
    stages.append({"name": "brief_packet", "status": "READY_FOR_MANUAL_REVIEW"})
    if not isinstance(account_data, dict):
        stages.append({"name": "portfolio_risk", "status": "BLOCKED",
                       "reason": "Latest complete three-account data not supplied"})
        result["status"] = "PUBLIC_BRIEF_ONLY"
        return result
    try:
        snap = snapshot(account_data["positions"], account_data["cash"],
                        account_data["fx"], observed_at=account_data["observed_at"])
        hist = adjusted_index(account_data["valuation_history"])
        if hist["status"] != "PROVISIONAL":
            raise ValueError("Historical NAV/flows unavailable")
    except (KeyError, TypeError, ValueError):
        stages.append({"name": "portfolio_risk", "status": "BLOCKED",
                       "reason": "Portfolio snapshot or flow history invalid/incomplete"})
        result["status"] = "PUBLIC_BRIEF_ONLY"
        return result
    stages.append({"name": "portfolio_risk", "status": "READY_FOR_PRIVATE_REVIEW"})
    result["portfolio"] = {"asof": snap["observed_at"],
                           "concentration_top3_pct": sorted(
                               (item["weight_pct"] for item in snap["holdings"].values()),
                               reverse=True)[:3],
                           "sector_exposure_complete": snap["sector_exposure_complete"],
                           "drawdown_status": hist["status"],
                           "drawdown_pct": hist["current_drawdown_pct"],
                           "minus_10_review": hist["review_minus_10_pct"],
                           "minus_20_review": hist["review_minus_20_pct"]}
    result["status"] = "READY_FOR_MANUAL_REVIEW"
    return result


def main():
    parser = argparse.ArgumentParser(description="CJ staged readiness check (read-only)")
    parser.add_argument("--comparison-json", help="Locally reconciled KRX comparison JSON")
    parser.add_argument("--private-accounts-json", help="Private local JSON, NEVER commit/upload")
    parser.add_argument("--target", default="KOSPI")
    args = parser.parse_args()
    report = json.loads(Path(args.comparison_json).read_text(encoding="utf-8")) if args.comparison_json else None
    account_data = (json.loads(Path(args.private_accounts_json).read_text(encoding="utf-8"))
                    if args.private_accounts_json else None)
    outcome = run_stages(report, account_data, target=args.target)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    # No input is not a successful production gate; it is a safe demonstration.
    return 0 if outcome["status"] == "READY_FOR_MANUAL_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
