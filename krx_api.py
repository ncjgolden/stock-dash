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
from urllib.parse import unquote

import requests
import streamlit as st


BASE_URL = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
TEST_CODES = {"005930", "000660"}


def _api_key() -> str | None:
    try:
        value = st.secrets.get("KRX_API_KEY")
    except Exception:
        value = None
    return unquote(str(value).strip()) if value else None


def _data_go_key() -> str | None:
    try:
        value = st.secrets.get("DATA_GO_KR_SERVICE_KEY")
    except Exception:
        value = None
    return unquote(str(value).strip()) if value else None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_data_go_price_history(code: str, days: int = 90) -> list[dict]:
    """Fetch raw KRX stock history from the official public-data API."""
    key = _data_go_key()
    if not key:
        return []
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    params = {
        "serviceKey": key,
        "resultType": "json",
        "numOfRows": 1000,
        "beginBasDt": start.strftime("%Y%m%d"),
        "endBasDt": end.strftime("%Y%m%d"),
        "likeSrtnCd": str(code).zfill(6),
    }
    try:
        payload = requests.get(url, params=params, timeout=(5, 15)).json()
        response = payload.get("response", {})
        if str(response.get("header", {}).get("resultCode")) not in ("00", "0"):
            return []
        items = (response.get("body", {}).get("items") or {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        rows = []
        for item in items:
            issue = str(item.get("srtnCd", "")).removeprefix("A").zfill(6)
            if issue != str(code).zfill(6):
                continue
            close = _clean_number(item.get("clpr"))
            if close is None:
                continue
            rows.append({
                "date": str(item.get("basDt")),
                "open": _clean_number(item.get("mkp")),
                "high": _clean_number(item.get("hipr")),
                "low": _clean_number(item.get("lopr")),
                "close": close,
                "change": _clean_number(item.get("vs")),
                "change_rate": _clean_number(item.get("fltRt")),
                "volume": _clean_number(item.get("trqu")),
                "trading_value": _clean_number(item.get("trPrc")),
                "market_cap": _clean_number(item.get("mrktTotAmt")),
                "shares": _clean_number(item.get("lstgStCnt")),
                "name": item.get("itmsNm"),
            })
        return sorted(rows, key=lambda x: x["date"])
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market_indices() -> list[dict]:
    """Fetch KOSPI/KOSDAQ index values from the official public-data API."""
    key = _data_go_key()
    if not key:
        return []
    url = "https://apis.data.go.kr/1160100/GetMarketIndexInfoService_V2/getStockMarketIndex_V2"
    params = {
        "serviceKey": key,
        "resultType": "json",
        "numOfRows": 100,
        "basDt": date.today().strftime("%Y%m%d"),
    }
    try:
        payload = requests.get(url, params=params, timeout=(5, 15)).json()
        response = payload.get("response", {})
        if str(response.get("header", {}).get("resultCode")) not in ("00", "0"):
            return []
        items = (response.get("body", {}).get("items") or {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        out = []
        for item in items:
            name = str(item.get("idxNm") or item.get("itmsNm") or item.get("indexName") or "")
            if name in ("코스피", "코스닥", "KOSPI", "KOSDAQ"):
                close = _clean_number(item.get("clpr"))
                rate = _clean_number(item.get("fltRt"))
                if close is not None:
                    out.append({"name": name, "close": close, "change_rate": rate, "date": item.get("basDt")})
        return out
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return []


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
def fetch_daily_market_data(code: str, days: int = 3) -> list[dict]:
    """Fetch a short recent KOSPI daily series for one issue.

    The KRX daily-trading API is date-based. The dashboard therefore loads a
    short recent window for fast rendering; longer technical history remains
    unavailable until a dedicated historical refresh is requested.
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
                timeout=2.5,
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
        rows = fetch_data_go_price_history(code, days=90)
        if not rows:
            rows = fetch_daily_market_data(code, days=3)
        if not rows:
            gaps = item.setdefault("data_gaps", [])
            note = "KRX 시장데이터 연결 실패 또는 승인된 API 데이터 없음"
            if note not in gaps:
                gaps.append(note)
            continue

        latest = rows[-1]
        item["prices"] = {
            "adjusted": False,
            "source": "공공데이터포털 금융위원회 KRX 주식시세정보 · 원시 종가",
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
