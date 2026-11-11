"""CJ read-only portfolio risk calculator. Input stays on the user's machine.

No brokerage credentials, order API, outbound requests or repository writes.
Explicit KRW FX rates required for USD holdings. No assumed current balances.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path


def positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + " must be a positive finite number")
    return float(value)


def nonnegative(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(label + " must be a nonnegative finite number")
    return float(value)


def snapshot(positions, cash, fx, *, observed_at):
    """Return KRW position exposure and account weights only with complete inputs.

    positions: [{account,symbol,quantity,price,currency,sector}].
    cash: [{account,amount,currency}]; FX {'KRW':1,'USD':...}.
    Missing cash/accounts/FX are errors; caller must validate 3-account completeness.
    """
    if not observed_at:
        raise ValueError("Timestamp mandatory")
    if not positions or not cash:
        raise ValueError("Complete positions and per-account cash records required")
    if fx.get("KRW") != 1:
        raise ValueError("KRW base FX must equal 1")
    cash_accounts = set()
    per_account = {}
    for item in cash:
        account = item["account"]
        if account in cash_accounts:
            raise ValueError("Duplicate account cash")
        cash_accounts.add(account)
        rate = positive(fx[item["currency"]], "FX rate")
        value = nonnegative(item["amount"], "cash") * rate
        per_account[account] = {"cash_krw": value, "positions_krw": 0.0}
    by_symbol = {}
    sector_values = {}
    for item in positions:
        account = item["account"]
        if account not in cash_accounts:
            raise ValueError("Cash record missing for account")
        rate = positive(fx[item["currency"]], "FX rate")
        value = positive(item["quantity"], "position quantity") * positive(item["price"], "price") * rate
        symbol = str(item["symbol"])
        if not symbol:
            raise ValueError("Symbol missing")
        per_account[account]["positions_krw"] += value
        if symbol not in by_symbol:
            by_symbol[symbol] = {"value_krw": 0.0, "by_account": {}}
        by_symbol[symbol]["value_krw"] += value
        by_symbol[symbol]["by_account"][account] = by_symbol[symbol]["by_account"].get(account, 0) + value
        # Sector tags need a look-through definition; untagged amounts are UNKNOWN, not 0.
        sector = item.get("sector", "UNKNOWN")
        sector_values[sector] = sector_values.get(sector, 0) + value
    for acc in per_account.values():
        acc["total_krw"] = acc["cash_krw"] + acc["positions_krw"]
    total = sum(acc["total_krw"] for acc in per_account.values())
    if total <= 0:
        raise ValueError("Portfolio NAV must be positive")
    for acc in per_account.values():
        acc["weight_pct"] = round(100 * acc["total_krw"] / total, 4)
    for item in by_symbol.values():
        item["weight_pct"] = round(100 * item["value_krw"] / total, 4)
    sector_weights = {name: round(100*value/total, 4) for name, value in sector_values.items()}
    return {"observed_at": observed_at, "total_nav_krw": total, "accounts": per_account,
            "holdings": by_symbol, "sector_weights_pct": sector_weights,
            "sector_exposure_complete": "UNKNOWN" not in sector_values,
            "warning": "Sector ETF holdings require look-through; tagged sector is not independently audited."}


def adjusted_index(history):
    """Cashflow-adjusted provisional return index, base=100.

    history: sorted [{date, nav_krw, external_flow_krw}], where the flow is
    assumed at the END of the observation interval. Daily/period NAV required;
    no cashflows omitted. This is a modified cashflow-adjusted approximation,
    not a broker-verified exact time-weighted return if intraday flows occurred.
    """
    if len(history) < 2:
        return {"status": "UNKNOWN", "reason": "At least two valuations required"}
    results, last_date, previous, index_value, peak = [], None, None, 100.0, 100.0
    for idx, row in enumerate(history):
        day = date.fromisoformat(row["date"])
        if last_date is not None and day <= last_date:
            raise ValueError("Valuation dates must be strictly increasing")
        nav = positive(row["nav_krw"], "nav_krw")
        flow = row.get("external_flow_krw")
        if isinstance(flow, bool) or not isinstance(flow, (int, float)) or not math.isfinite(flow):
            raise ValueError("Each observation needs a signed, finite external_flow_krw")
        if idx > 0:
            r = (nav - flow) / previous - 1
            if r <= -1:
                raise ValueError("Period return <= -100%; investigate missing data or flows")
            index_value *= 1+r
            peak = max(peak, index_value)
        dd = (index_value / peak - 1)*100
        results.append({"date": row["date"], "index": round(index_value, 6),
                        "drawdown_pct": round(dd, 6)})
        last_date, previous = day, nav
    mdd = min(r["drawdown_pct"] for r in results)
    current = results[-1]["drawdown_pct"]
    return {"status": "PROVISIONAL", "series": results,
            "current_drawdown_pct": current, "max_drawdown_pct": mdd,
            "review_minus_10_pct": current <= -10,
            "review_minus_20_pct": current <= -20,
            "warning": "Review thresholds are not orders; flow-at-end approximation, not exact TWR."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-input", required=True, help="Local JSON file, never commit")
    args = parser.parse_args()
    p = Path(args.private_input)
    payload = json.loads(p.read_text(encoding="utf-8"))
    # Deliberately do not print raw holdings, account numbers or valuation history.
    result = {}
    if "positions" in payload:
        s = snapshot(payload["positions"], payload["cash"], payload["fx"],
                     observed_at=payload["observed_at"])
        result["risk"] = {
            "observed_at": s["observed_at"],
            "total_nav_krw": s["total_nav_krw"],
            "top_weights_pct": sorted(
                [(symbol, v["weight_pct"]) for symbol, v in s["holdings"].items()],
                key=lambda x: -x[1])[:3],
            "sector_exposure_complete": s["sector_exposure_complete"],
            "sector_weights_pct": s["sector_weights_pct"],
        }
    if "valuation_history" in payload:
        index = adjusted_index(payload["valuation_history"])
        result["drawdown"] = {k: v for k, v in index.items() if k != "series"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
