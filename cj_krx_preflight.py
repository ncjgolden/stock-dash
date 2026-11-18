"""Read-only preflight for CJ official source reconciliation.

Never contacts exchanges, never reads/prints credential values and never
promotes third-party market data to an officially validated briefing.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from cj_price_evidence_review import review

KRX_STOCK_API = "https://openapi.krx.co.kr/contents/OPP/USES/service/OPPUSES002_S2.cmd?BO_ID=JvJFzlAENzZlPBDNGAWC"
KRX_DATA_SYSTEM = "https://data.krx.co.kr/"


def preflight(*, public_csv=None, official_csv=None, symbol="005930",
              asof=None, official_url=KRX_DATA_SYSTEM, env=None, now=None):
    """Return explicit gates; absence of files/key leaves data blocked."""
    env = os.environ if env is None else env
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    if not (len(symbol) == 6 and symbol.isascii() and symbol.isdigit()):
        raise ValueError("Six-digit KRX ticker required")
    state = {
        "checked_at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "symbol": symbol,
        "krx_openapi_access_key_configured_locally": bool(env.get("KRX_AUTH_KEY")),
        "openapi_entitlement_confirmed": False,
        "krx_official_price_csv_supplied": bool(official_csv),
        "public_price_csv_supplied": bool(public_csv),
        "krx_investor_flow_data_supplied": False,
        "price_reconciliation": "NOT_RUN",
        "market_data_validated": False,
        "chatgpt_automation_connected": False,
        "release_gate": "BLOCKED",
        "next_actions": [],
        "references": {
            "official_price_api": KRX_STOCK_API,
            "official_investor_statistics": KRX_DATA_SYSTEM,
        },
    }

    if not state["krx_openapi_access_key_configured_locally"] and not official_csv:
        state["next_actions"].append(
            "Obtain approved KRX stock OpenAPI access OR download official price CSV")
    if bool(public_csv) != bool(official_csv):
        state["next_actions"].append(
            "Both independently sourced price CSV files are needed for comparison")
    if public_csv and official_csv:
        if not asof:
            state["next_actions"].append("Specify --asof for exact same-session comparison")
        else:
            try:
                result = review(
                    public_path=public_csv, reference_path=official_csv,
                    symbol=symbol, asof=asof, official_url=official_url, now=now)
            except (FileNotFoundError, OSError, ValueError, KeyError) as error:
                state["price_reconciliation"] = "BLOCKED"
                state["price_comparison_failure_type"] = type(error).__name__
            else:
                state["price_reconciliation"] = result["status"]
                state["compared_sessions"] = result["compared_sessions"]
                state["official_file_sha256"] = result["reference_file_sha256"]
                state["public_file_sha256"] = result["public_file_sha256"]
                state["next_actions"].append(
                    "Independently authenticate original KRX file, rights, units and corporate actions")
    if not state["krx_investor_flow_data_supplied"]:
        state["next_actions"].append(
            "Separately obtain official daily investor net-trading records from KRX Data System")
    state["next_actions"].append(
        "Do not include any new GitHub-derived numbers in scheduled ChatGPT briefs yet")
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="005930")
    parser.add_argument("--asof")
    parser.add_argument("--public-csv")
    parser.add_argument("--official-csv")
    parser.add_argument("--official-url", default=KRX_DATA_SYSTEM)
    args = parser.parse_args()
    print(json.dumps(preflight(
        symbol=args.symbol, asof=args.asof,
        public_csv=args.public_csv, official_csv=args.official_csv,
        official_url=args.official_url), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
