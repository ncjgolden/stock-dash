"""KRX Open API market-data adapter for StockDash.

The adapter is intentionally small and conservative:
- Uses the official KRX Open API.
- Reads only market data; no order/trading actions.
- Keeps API keys in Streamlit Secrets.
- Returns an empty result when the key/service is unavailable so the dashboard
  can continue showing verified research instead of inventing market values.
"""

from __future__ import annotations

from datetime import date, timedelta

import requests
import streamlit as st


BASE_URL = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
TEST_CODES = {"005930", "000660"}


def _api_key() -> str | None:
    try:
        value = st.secrets.get("KRX_API_KEY")
    except Exception:
        return None
    return str(value).strip() if value else None


def _clean_number(value):
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _date_range(days: int):
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_daily_market_data(code: str, days: int = 365) -> list[dict]:
    """Fetch a bounded recent KOSPI daily series for one issue.

    KRX's daily-trading API is date-based, so this makes one request per
    calendar date. Results are cached for one hour to keep Streamlit reloads
    practical.
    """
    code = str(code).zfill(6)
    if code not in TEST_CODES:
        return []

    key = _api_key()
    if not key:
        return []

    start, end = _date_range(days)
    rows: list[dict] = []
    session = requests.Session()
    headers = {"AUTH_KEY": key}

    cursor = start
    while cursor <= end:
        params = {"basDd": cursor.strftime("%Y%m%d")}
        try:
            response = session.get(
                BASE_URL,
                params=params,
                headers=headers,
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            cursor += timedelta(days=1)
            continue

        for item in payload.get("OutBlock_1", []) or []:
            if str(item.get("ISU_CD", "")).zfill(6) != code:
                continue
            rows.append(
                {
                    "date": cursor.isoformat(),
                    "open": _clean_number(item.get("TDD_OPNPRC")),
                    "high": _clean_number(item.get("TDD_HGPRC")),
                    "low": _clean_number(item.get("TDD_LWPRC")),
                    "close": _clean_number(item.get("TDD_CLSPRC")),
                    "change": _clean_number(item.get("CMPPREVDD_PRC")),
                    "change_rate": _clean_number(item.get("FLUC_RT")),
                    "volume": _clean_number(item.get("ACC_TRDVOL")),
                    "trading_value": _clean_number(item.get("ACC_TRDVAL")),
                    "market_cap": _clean_number(item.get("MKTCAP")),
                    "shares": _clean_number(item.get("LIST_SHRS")),
                    "name": item.get("ISU_NM"),
                }
            )
            break

        cursor += timedelta(days=1)

    return sorted(rows, key=lambda x: x["date"])


def _attach_derived_earnings(item: dict) -> None:
    """Create a small transparent earnings history from published cumulative data."""
    financial = item.get("financial") or {}
    current_period = financial.get("period")
    prior_period = financial.get("prior_period")
    values = (
        current_period, prior_period,
        financial.get("revenue"), financial.get("prior_revenue"),
        financial.get("operating_profit"), financial.get("prior_operating_profit"),
    )
    if not all(x not in (None, "") for x in values):
        return
    item["earnings_history"] = [
        {"year": str(prior_period)[:7], "revenue": financial["prior_revenue"], "profit": financial["prior_operating_profit"]},
        {"year": str(current_period)[:7], "revenue": financial["revenue"], "profit": financial["operating_profit"]},
    ]


def load_market_bundle(research: dict) -> dict:
    """Attach KRX test data to Samsung Electronics and SK hynix records."""

    for code in TEST_CODES:
        item = research.get(code)
        if not item:
            continue

        _attach_derived_earnings(item)
        rows = fetch_daily_market_data(code)
        if not rows:
            gaps = item.setdefault("data_gaps", [])
            note = "KRX 시장데이터 연결 실패 또는 승인된 API 데이터 없음"
            if note not in gaps:
                gaps.append(note)
            continue

        latest = rows[-1]
        item["prices"] = {
            "adjusted": False,
            "source": "한국거래소 KRX Open API · 유가증권 일별매매정보",
            "rows": rows,
        }
        item["price_snapshot"] = {
            "price": latest.get("close"),
            "price_date": latest.get("date"),
            "market_cap": latest.get("market_cap"),
            "shares": latest.get("shares"),
        }
        item["change"] = latest.get("change_rate")
        _attach_derived_earnings(item)

        valuation = item.get("valuation")
        if isinstance(valuation, dict):
            valuation["current_price"] = latest.get("close")
            valuation["price_date"] = latest.get("date")

        gaps = item.setdefault("data_gaps", [])
        gaps[:] = [
            g for g in gaps
            if "주가" not in str(g) and "시장데이터" not in str(g)
        ]

    return research
