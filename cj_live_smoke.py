"""One-shot public-data connectivity diagnostics for the CJ briefing project.

External providers are untrusted public sources. This test reports metadata,
never labels values official, and never publishes portfolio/account details.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cj_investor_flow import collect as collect_flow
from cj_market_trends import collect as collect_trend


def run(*, now=None, flow_fn=collect_flow, trend_fn=collect_trend):
    now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    local = now.astimezone(ZoneInfo("Asia/Seoul"))
    # Use the previous calendar day, not the current incomplete session.
    # This is a connectivity experiment, not proof of an exchange trading day.
    asof = (local.date() - timedelta(days=1)).isoformat()
    checks = {}

    def check(name, fn):
        try:
            result = fn()
            checks[name] = result
        except Exception as exc:
            # Sanitized errors: never log raw URLs, keys, or request payloads.
            checks[name] = {"status": "UNKNOWN", "reason": type(exc).__name__}

    check("kr_stock_trend", lambda: trend_fn(
        market="KR", asof=asof, now=now,
        symbols={"삼성전자": ("FDR", "005930")}))
    check("us_index_trend", lambda: trend_fn(
        market="US", asof=asof, now=now,
        symbols={"S&P500": ("YF", "^GSPC")}))
    check("kr_investor_flow", lambda: flow_fn(
        asof=asof, now=now, targets={"삼성전자": "005930"}))

    def digest(name):
        data = checks[name]
        if data.get("status") == "UNKNOWN":
            return {"status": "UNKNOWN", "reason": data.get("reason", "ProviderError")}
        entries = data.get("results", {})
        if not entries:
            return {"status": "UNKNOWN", "reason": "EMPTY_RESPONSE"}
        item = next(iter(entries.values()))
        return {"status": item.get("status", "UNKNOWN"),
                "asof": item.get("asof") or data.get("market_asof"),
                "observations": item.get("observations"),
                "has_60_session_history": (
                    (item.get("windows") or {}).get("60") is not None
                    if name == "kr_investor_flow" else
                    (item.get("returns_pct") or {}).get("60") is not None),
                "source": item.get("source") or data.get("provider"),
                "error_type": item.get("error")}

    good = {"DATA_ONLY", "COMPLETE", "MATCHED_60_SESSIONS"}
    source_ok = {name: (data.get("status") in good and
                        data.get("has_60_session_history") is True)
                 for name, data in
                 ((name, digest(name)) for name in checks)}
    report = {"connectivity": ("SOURCE_DATA_AVAILABLE_UNVERIFIED"
                               if all(source_ok.values()) else "DEGRADED"),
              "usable_in_chatgpt_briefing": False,
              "checked_at_kst": local.isoformat(),
              "requested_asof": asof,
              "checks": {name: digest(name) for name in checks},
              "official_krx_crosscheck": "NOT_RUN",
              "chatgpt_briefing_connection": "NOT_CONFIGURED",
              "account_data_used": False,
              "interpretation": "Research connectivity check only, NOT verified live investment figures."}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-unknown", action="store_true")
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # GitHub can mark a diagnostic run successful even with failed providers.
    # Surface degraded data explicitly without falsely describing it as a
    # code/test failure. Public summary contains metadata only.
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        status = report["connectivity"]
        lines = [
            "### CJ public market connectivity (not investment validation)",
            f"**Data-source state: {status}**",
            "",
            "| Source | Availability | 60 observations |",
            "|---|---|---|",
        ]
        for name, item in report["checks"].items():
            lines.append(f'| {name} | {item["status"]} | {item["has_60_session_history"]} |')
        lines.extend(["", "KRX official reconciliation: NOT_RUN",
                      "ChatGPT automatic data integration: NOT_CONFIGURED"])
        with Path(summary).open("a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
    if report["connectivity"] == "DEGRADED":
        print("::warning::CJ source connectivity DEGRADED; unit test success does not approve data.")
    if args.fail_on_unknown and any(
            value["status"] in {"UNKNOWN", "PARTIAL", "STALE_REFERENCE"}
            for value in report["checks"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
