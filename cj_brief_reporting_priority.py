"""Review-only market-briefing priority selection with evidence safeguards.

Pure functions; observations must be supplied and verified outside this module.
A mode is a reporting priority, never a buy/sell signal.
"""
from __future__ import annotations

from datetime import date
from typing import Mapping

HOLDINGS = (
    "005930", "000660", "005380", "009150", "010120",
    "267260", "SOL_AI_SEMICONDUCTOR_TOP2_PLUS",
    "NVDA", "GOOGL", "ANET", "KO", "SCHD", "JEPI",
)
# May not be used to generate current holdings size or portfolio valuation.
HIGH_PRIORITY_CATEGORIES = ("regulatory", "guidance", "accounting",
                            "liquidity", "contract_loss", "governance")


def choose_reporting_mode(evidence: Mapping):
    """Require explicit verified 5-session evidence for de-escalation.

    Two separate cases: NVDA event is resolved and systemic industry
    contagion is demonstrably reduced. A mere rally never suffices.
    """
    required = (
        "nvidia_results_verified",
        "forward_guidance_verified",
        "business_continuity_verified",
        "no_major_nvidia_event_five_sessions",
        "contagion_eased_five_sessions",
    )
    unknown = [k for k in required if evidence.get(k) is not True]
    relapse = evidence.get("new_major_nvidia_risk") is True
    if relapse:
        return {"mode": "NVDA_SPECIAL", "reason": "NEW_MATERIAL_NVDA_RISK",
                "unverified": unknown, "trade_signal": False}
    if unknown:
        return {"mode": "NVDA_SPECIAL", "reason": "STABILIZATION_NOT_VERIFIED",
                "unverified": unknown, "trade_signal": False}
    return {"mode": "BALANCED_HOLDINGS", "reason": "ALL_STABILITY_CHECKS_VERIFIED",
            "unverified": [], "trade_signal": False}


def check_holdings_coverage(checked_symbols, material_events):
    """Require every holding to be screened, and promote all critical events.

    Checking is not proof that every event on Earth has been found.
    """
    checked = set(checked_symbols)
    missing = sorted(set(HOLDINGS) - checked)
    alerts = []
    for event in material_events:
        if event.get("symbol") not in HOLDINGS:
            raise ValueError("Unknown holding in material event")
        if event.get("verified") is not True:
            continue
        if event.get("category") in HIGH_PRIORITY_CATEGORIES and event.get("material") is True:
            alerts.append({"symbol": event["symbol"], "category": event["category"]})
    return {"screened_all": not missing, "missing": missing,
            "material_alerts": alerts, "trading_authorized": False}
