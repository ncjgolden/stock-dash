from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import requests


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    name: str
    capabilities: tuple[str, ...]
    env_keys: tuple[str, ...] = field(default_factory=tuple)


PROVIDERS = (
    ProviderSpec(
        "opendart",
        "OpenDART",
        (
            "stock.profile",
            "stock.financials",
            "stock.disclosures",
            "stock.business_report",
        ),
        ("DART_CRTFC_KEY",),
    ),
    ProviderSpec(
        "data_go_kr_stock",
        "금융위원회 주식시세정보",
        ("stock.search", "stock.quote"),
        ("DATA_GO_KR_SERVICE_KEY",),
    ),
    ProviderSpec(
        "data_go_kr_index",
        "금융위원회 시장지수정보",
        ("market.kospi", "market.kosdaq"),
        ("DATA_GO_KR_SERVICE_KEY",),
    ),
)


def configured(spec: ProviderSpec) -> bool:
    return all(bool(os.getenv(key, "").strip()) for key in spec.env_keys)


def capabilities() -> set[str]:
    active = set()
    for spec in PROVIDERS:
        if configured(spec):
            active.update(spec.capabilities)
    return active


def _result(provider_id: str, status: str, detail: str, started: float):
    return {
        "provider_id": provider_id,
        "status": status,
        "detail": detail,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "checked_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S"),
    }


def health(spec: ProviderSpec) -> dict:
    started = time.perf_counter()
    if not configured(spec):
        return _result(spec.provider_id, "not_configured", "인증정보 미설정", started)

    try:
        if spec.provider_id == "opendart":
            key = os.getenv("DART_CRTFC_KEY", "").strip()
            response = requests.get(
                "https://opendart.fss.or.kr/api/company.json",
                params={"crtfc_key": key, "corp_code": "00126380"},
                timeout=(5, 12),
            )
            response.raise_for_status()
            payload = response.json()
            code = str(payload.get("status", ""))
            if code == "000":
                return _result(spec.provider_id, "ok", "연결·인증 정상", started)
            known = {
                "010": "키 미등록",
                "011": "키 사용 중지",
                "012": "IP 제한",
                "020": "호출 한도 초과",
                "013": "연결됨 · 자료 없음",
                "800": "기관 점검 중",
            }
            return _result(spec.provider_id, "error", known.get(code, f"응답코드 {code or '확인 필요'}"), started)

        if spec.provider_id == "data_go_kr_stock":
            key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
            response = requests.get(
                "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo",
                params={"serviceKey": key, "resultType": "json", "numOfRows": 1},
                timeout=(5, 12),
            )
            response.raise_for_status()
            payload = response.json()
            code = str(payload.get("response", {}).get("header", {}).get("resultCode", ""))
            if code in {"00", "0"}:
                return _result(spec.provider_id, "ok", "연결·인증 정상", started)
            return _result(spec.provider_id, "error", f"응답코드 {code or '확인 필요'}", started)

        if spec.provider_id == "data_go_kr_index":
            key = unquote(os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip())
            end = date.today()
            start = end - timedelta(days=10)
            response = requests.get(
                "https://apis.data.go.kr/1160100/GetMarketIndexInfoService_V2/getStockMarketIndex_V2",
                params={
                    "serviceKey": key,
                    "resultType": "json",
                    "numOfRows": 1000,
                    "beginBasDt": start.strftime("%Y%m%d"),
                    "endBasDt": end.strftime("%Y%m%d"),
                },
                timeout=(5, 12),
            )
            response.raise_for_status()
            payload = response.json()
            body = payload.get("response", {})
            code = str(body.get("header", {}).get("resultCode", ""))
            if code not in {"00", "0"}:
                return _result(spec.provider_id, "error", f"지수 API 응답코드 {code or '확인 필요'}", started)
            items = (body.get("body", {}).get("items") or {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            if not items:
                return _result(spec.provider_id, "error", "인증은 통과했으나 최근 지수 자료 없음", started)
            return _result(spec.provider_id, "ok", "지수 API 연결·인증 정상", started)

        return _result(spec.provider_id, "unknown", "진단 미구현", started)
    except requests.Timeout:
        return _result(spec.provider_id, "error", "응답 시간 초과", started)
    except requests.exceptions.SSLError:
        return _result(spec.provider_id, "error", "TLS 보안 연결 실패", started)
    except requests.ConnectionError:
        return _result(spec.provider_id, "error", "네트워크 연결 실패", started)
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return _result(spec.provider_id, "error", "정상 응답을 확인하지 못함", started)


def health_all() -> list[dict]:
    return [{**health(spec), "name": spec.name, "capabilities": list(spec.capabilities)} for spec in PROVIDERS]


def missing_capabilities(required: list[str] | tuple[str, ...]) -> list[str]:
    active = capabilities()
    return [cap for cap in required if cap not in active]
