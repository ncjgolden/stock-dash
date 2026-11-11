"""One-shot public-data connectivity diagnostics for the CJ briefing project.

External providers are untrusted public sources. This test reports metadata,
never labels values official, and never publishes portfolio/account details.
"""
from __future__ import annotations

import argparse
import json
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

    report = {"checked_at_kst": local.isoformat(),
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
    if args.fail_on_unknown and any(
            value["status"] in {"UNKNOWN", "PARTIAL", "STALE_REFERENCE"}
            for value in report["checks"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
