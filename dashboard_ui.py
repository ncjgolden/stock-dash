"""Final dark investment-cockpit UI for StockDash."""
from __future__ import annotations

from datetime import date
import html

import altair as alt
import pandas as pd
import streamlit as st


UP = "#6FCB2F"
DOWN = "#3D8FEA"
BLUE = "#4A9BE8"
RED = "#E45B5B"
GOLD = "#D5B35C"
BG = "#0D0F0E"
PANEL = "#151816"
PANEL_2 = "#1A1D1A"
BORDER = "#303430"
TEXT = "#F2F3EE"
MUTED = "#929991"


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _pct(a, b):
    a, b = _num(a), _num(b)
    return (a / b - 1) * 100 if a is not None and b not in (None, 0) else None


def _snapshot(item, fallback_name):
    f = item.get("financial") or {}
    v = item.get("valuation") or {}
    flow = item.get("flow") or {}
    prices = (item.get("prices") or {}).get("rows") or []
    price = v.get("current_price") or (prices[-1].get("close") if prices else None)
    return {
        "name": item.get("name") or fallback_name,
        "code": item.get("code", ""),
        "price": price,
        "price_snapshot": item.get("price_snapshot") or {},
        "change": item.get("change"),
        "summary": (item.get("summary") or {}).get("text", ""),
        "earnings_history": item.get("earnings_history") or [],
        "valuation_anchors": item.get("valuation_anchors") or [],
        "peers": item.get("peers") or {},
        "rev": _pct(f.get("revenue"), f.get("prior_revenue")),
        "op": _pct(f.get("operating_profit"), f.get("prior_operating_profit")),
        "net": _pct(f.get("net_income"), f.get("prior_net_income")),
        "op_value": f.get("operating_profit"),
        "revenue_value": f.get("revenue"),
        "net_value": f.get("net_income"),
        "period": f.get("period"),
        "foreign": flow.get("foreign"),
        "institution": flow.get("institution"),
        "flow_unit": flow.get("unit"),
        "fair": v.get("base"),
        "fair_low": v.get("low"),
        "fair_high": v.get("high"),
        "prices": prices,
        "business": (item.get("business") or {}).get("text", ""),
        "gaps": item.get("data_gaps") or [],
        "source": f.get("source") or (item.get("summary") or {}).get("source"),
        "as_of": item.get("as_of"),
        "sector": item.get("sector") or item.get("industry") or "",
        "basis": f.get("basis") or "미확인",
    }


def _fmt(v, suffix="원"):
    if v is None:
        return "미확인"
    try:
        return f"{float(v):,.0f}{suffix}"
    except (TypeError, ValueError):
        return str(v)


def _pct_text(v):
    return f"{v:+.1f}%" if v is not None else "미확인"


def _flow_text(v, unit):
    return f"{v:+,.0f} {unit or ''}".strip() if v is not None else "미확인"


def _margin(snapshot):
    op = _num(snapshot.get("op_value"))
    rev = _num(snapshot.get("revenue_value"))
    return op / rev * 100 if op is not None and rev not in (None, 0) else None


def _sector_from_focus(focus):
    text = f'{focus.get("name", "")} {focus.get("business", "")} {focus.get("sector", "")}'.lower()
    if any(k in text for k in ["반도체", "memory", "dram", "nand", "hbm", "sk하이닉스", "삼성전자"]):
        return "반도체"
    if any(k in text for k in ["자동차", "전장", "차량"]):
        return "자동차"
    if any(k in text for k in ["바이오", "제약", "의약"]):
        return "바이오"
    if any(k in text for k in ["방산", "방위", "항공"]):
        return "방산"
    if any(k in text for k in ["은행", "금융", "보험", "증권"]):
        return "금융"
    if any(k in text for k in ["배터리", "2차전지", "전지"]):
        return "2차전지"
    if any(k in text for k in ["조선", "선박", "해양"]):
        return "조선"
    if any(k in text for k in ["전력", "전기", "가스", "유틸리티"]):
        return "유틸리티"
    if any(k in text for k in ["인터넷", "플랫폼", "게임", "검색"]):
        return "인터넷"
    return "미분류"


def _css():
    st.markdown(
        """<style>
.stApp{background:#0D0F0E!important;color:#F2F3EE}
[data-testid="stHeader"]{background:#0D0F0E}
.block-container{max-width:1480px!important;padding:0.7rem 1.1rem 2.8rem!important}
section[data-testid="stSidebar"]{background:#101210}
div[data-testid="stVerticalBlock"]>div{max-width:100%}
.sd-top{display:flex;align-items:center;gap:8px;white-space:nowrap;overflow:hidden;border-bottom:1px solid #252925;padding:4px 0 10px;margin-bottom:14px}
.sd-search-icon{width:42px;height:32px;border:1px solid #383C38;border-radius:8px;color:#A2AAA2;display:flex;align-items:center;justify-content:center;font-size:17px}
.sd-ticker{border:1px solid #303430;background:#151816;border-radius:7px;padding:7px 11px;font-size:10px;color:#C9CEC8}
.sd-ticker b{color:#F2F3EE}.sd-ticker.up{color:#6FCB2F}.sd-ticker.down{color:#E45B5B}
.sd-brand{font-size:25px;font-weight:950;letter-spacing:-.05em;color:#F3F4F0}
.sd-brand small{font-size:9px;color:#7F887F;letter-spacing:.12em;margin-left:8px}
.sd-date{margin-left:auto;font-size:9px;color:#737B73}
.sd-title{font-size:14px;font-weight:900;letter-spacing:-.03em;color:#DDE1DB;margin:15px 0 8px}
.sd-sub{font-size:9px;color:#7F887F;margin:-2px 0 8px}
.sd-hero{background:#171A18;border:1px solid #303430;border-radius:14px;padding:15px 18px;min-height:112px}
.sd-name{font-size:22px;font-weight:950;letter-spacing:-.05em;color:#F4F5F0}
.sd-code{font-size:9px;color:#818981;margin-top:2px}
.sd-price{font-size:28px;font-weight:950;color:#6FCB2F;margin:7px 0 0}
.sd-change{font-size:11px;font-weight:850;color:#6FCB2F}
.sd-badge{display:inline-block;background:#EAF4DF;color:#2E5F21;border-radius:6px;padding:4px 8px;font-size:8px;font-weight:900;margin:7px 3px 0 0}
.sd-badge.blue{background:#DCEBFA;color:#245F93}
.sd-card{background:#171A18;border:1px solid #303430;border-radius:14px;padding:15px;min-height:112px}
.sd-card-title{font-size:9px;color:#858D85}.sd-card-value{font-size:19px;font-weight:900;color:#F1F3EE;margin-top:6px}
.sd-card-note{font-size:8px;color:#858D85;margin-top:5px;line-height:1.45}
.sd-metric{background:#171A18;border:1px solid #303430;border-radius:11px;padding:12px;min-height:84px}
.sd-label{font-size:9px;color:#858D85;font-weight:800}.sd-value{font-size:18px;font-weight:950;margin-top:6px;letter-spacing:-.035em}.sd-note{font-size:8px;color:#7C847C;margin-top:3px}
.sd-panel{background:#171A18;border:1px solid #303430;border-radius:14px;padding:14px}
.sd-panel h4{font-size:12px;margin:0 0 8px;color:#E8EBE5}
.sd-chip{display:inline-block;background:#222722;border:1px solid #353A35;color:#B8C0B8;border-radius:5px;padding:4px 7px;font-size:8px;margin-right:4px}
.sd-strategy{background:#191C1A;border-radius:7px;border-left:4px solid #596259;padding:8px 10px;margin:6px 0}
.sd-strategy b{font-size:9px;color:#E6EAE4}.sd-strategy span{font-size:8px;color:#929A92;margin-left:7px;line-height:1.4}
.sd-radar{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.sd-radar-cell{background:#1B1E1B;border:1px solid #303430;border-radius:8px;padding:10px}.sd-radar-cell b{font-size:9px;display:block;color:#DDE1DB}.sd-radar-cell span{font-size:8px;color:#838B83}
.sd-scenario{border:1px solid #303430;border-radius:12px;padding:12px;min-height:108px}.sd-scenario.up{background:#EDF5E4;color:#315A24;border-color:#CFE3BC}.sd-scenario.neutral{background:#F0EEE7;color:#6A5A32;border-color:#E2D7B9}.sd-scenario.down{background:#F8E8E8;color:#853C3C;border-color:#E7C4C4}.sd-scenario b{font-size:10px}.sd-scenario strong{display:block;font-size:13px;margin:7px 0}.sd-scenario p{font-size:8px;line-height:1.5;margin:0}
.sd-section-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:10px}
.sd-business{font-size:9px;color:#A8B0A8;line-height:1.55}
.sd-map{background:#171A18;border:1px solid #303430;border-radius:14px;padding:14px}
.sd-map-head{display:flex;justify-content:space-between;align-items:end;margin-bottom:10px}.sd-map-title{font-size:13px;font-weight:900}.sd-map-note{font-size:8px;color:#7F887F}
.sd-map-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}.sd-sector{min-height:74px;border:1px solid #343934;background:#1D211E;border-radius:9px;padding:9px}.sd-sector.active{background:#263A20;border-color:#79A858}.sd-sector-name{font-size:10px;font-weight:900}.sd-sector-value{font-size:9px;font-weight:800;color:#A9B2A8;margin-top:9px}.sd-sector.active .sd-sector-value{color:#79D43D}.sd-sector-note{font-size:7px;color:#707970;margin-top:3px}
.sd-foot{font-size:8px;color:#727A72;line-height:1.5;margin-top:8px}
div[data-testid="stCaptionContainer"] p{color:#737B73!important;font-size:8px!important}
div[data-testid="stExpander"]{border-color:#303430!important;background:#151816!important}
div[data-testid="stExpander"] summary p{color:#A8B0A8!important}
div[data-testid="stDataFrame"]{border-color:#303430!important}
@media(max-width:900px){.sd-radar{grid-template-columns:repeat(2,1fr)}.sd-map-grid{grid-template-columns:repeat(2,1fr)}.sd-section-grid{grid-template-columns:1fr}}
</style>""",
        unsafe_allow_html=True,
    )


def _ticker_row():
    items = [
        ("KOSPI", "시장 데이터 연결 필요", ""),
        ("KOSDAQ", "시장 데이터 연결 필요", ""),
        ("S&P500", "시장 데이터 연결 필요", ""),
        ("SOX", "시장 데이터 연결 필요", ""),
        ("원/달러", "시장 데이터 연결 필요", ""),
    ]
    parts = ['<div class="sd-top"><div class="sd-search-icon">⌕</div>']
    for name, value, tone in items:
        parts.append(f'<div class="sd-ticker {tone}"><b>{html.escape(name)}</b> {html.escape(value)}</div>')
    parts.append(f'<div class="sd-date">{date.today().isoformat()}</div></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def _trend(item):
    rows = item.get("prices") or []
    if not rows:
        st.info("주가 시계열이 아직 연결되지 않았습니다. KRX/시세 API 승인 후 일봉·완료 주봉·RSI·MACD가 자동 표시됩니다.")
        return
    df = pd.DataFrame(rows)
    if "date" not in df or "close" not in df:
        st.info("주가 데이터 형식이 기술적 분석에 충분하지 않습니다.")
        return
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    if df.empty:
        st.info("표시할 주가 데이터가 없습니다.")
        return
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()
    chart = (
        alt.Chart(df.tail(252))
        .transform_fold(["close", "MA20", "MA60"], as_=["series", "value"])
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title="가격", scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title="지표"),
            tooltip=[alt.Tooltip("date:T", title="일자"), alt.Tooltip("series:N", title="지표"), alt.Tooltip("value:Q", title="값", format=",.0f")],
        )
        .properties(height=250)
        .configure_view(stroke=None)
        .configure_axis(gridColor="#2C312C", labelColor="#8B938B", titleColor="#8B938B")
    )
    st.altair_chart(chart, use_container_width=True)
    tech = _technical_stats(rows)
    if tech:
        position = f'{tech["position52"]:.1f}%' if tech.get("position52") is not None else "미확인"
        cols = st.columns(6)
        metrics = [
            ("20일선 대비", f'{(tech["latest"] / tech["ma20"] - 1) * 100:+.1f}%' if tech.get("ma20") else "미확인"),
            ("60일선 대비", f'{(tech["latest"] / tech["ma60"] - 1) * 100:+.1f}%' if tech.get("ma60") else "미확인"),
            ("RSI(14)", f'{tech["rsi14"]:.1f}' if tech.get("rsi14") is not None else "미확인"),
            ("MACD", f'{tech["macd"]:.1f}' if tech.get("macd") is not None else "미확인"),
            ("52주 위치", position),
            ("최근 거래량", f'{tech["volume"]:,.0f}' if tech.get("volume") is not None else "미확인"),
        ]
        for col, (title, value) in zip(cols, metrics):
            with col:
                _mini_metric(title, value, tech.get("latest_date", ""), "blue")




def _strategy(snapshot):
    checks = []
    rev, op, net = snapshot["rev"], snapshot["op"], snapshot["net"]
    if rev is not None and op is not None:
        if rev > 0 and op > 0:
            checks.append(("펀더멘털", "매출·영업이익 동반 증가가 다음 실적에도 이어지는지 확인", "good"))
        elif rev > 0:
            checks.append(("펀더멘털", "매출 증가가 이익 증가로 연결되는지 원가·가격 요인을 확인", "watch"))
        else:
            checks.append(("펀더멘털", "매출·이익 둔화 원인과 회복 조건을 다음 공시에서 확인", "caution"))
    else:
        checks.append(("펀더멘털", "동일 기준 전년 대비 실적 자료 확보 후 변화 방향 확인", "caution"))
    checks.append(("수급", "외국인·기관 흐름과 주가 변화를 같은 기간에 비교", "watch" if snapshot["foreign"] is not None or snapshot["institution"] is not None else "caution"))
    checks.append(("밸류에이션", "참고가와 현재가의 차이를 평가 가정·성장 지속성과 함께 검토", "watch" if snapshot["fair"] is not None else "caution"))
    checks.append(("모멘텀", "일봉·완료 주봉·거래량 신호가 같은 방향인지 확인", "watch"))
    checks.append(("리스크", "실적·환율·원가·고객·정책 등 핵심 가정의 훼손 여부 확인", "caution"))
    return checks


def _technical_stats(rows):
    """Calculate transparent technical indicators when an OHLCV series is available."""
    if not rows:
        return {}
    df = pd.DataFrame(rows).copy()
    if "date" not in df or "close" not in df:
        return {}
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ("close", "open", "high", "low", "volume", "trading_value"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date")
    if df.empty:
        return {}
    close = df["close"]
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    low52 = close.tail(252).min()
    high52 = close.tail(252).max()
    latest = close.iloc[-1]
    return {
        "latest": latest,
        "latest_date": df["date"].iloc[-1].date().isoformat(),
        "ma20": ma20.iloc[-1] if pd.notna(ma20.iloc[-1]) else None,
        "ma60": ma60.iloc[-1] if pd.notna(ma60.iloc[-1]) else None,
        "rsi14": rsi.iloc[-1] if pd.notna(rsi.iloc[-1]) else None,
        "macd": macd.iloc[-1] if pd.notna(macd.iloc[-1]) else None,
        "signal": signal.iloc[-1] if pd.notna(signal.iloc[-1]) else None,
        "low52": low52,
        "high52": high52,
        "position52": ((latest - low52) / (high52 - low52) * 100) if high52 != low52 else None,
        "volume": df["volume"].iloc[-1] if "volume" in df and pd.notna(df["volume"].iloc[-1]) else None,
        "trading_value": df["trading_value"].iloc[-1] if "trading_value" in df and pd.notna(df["trading_value"].iloc[-1]) else None,
    }


def _earnings_history_table(focus):
    history = focus.get("earnings_history") or []
    if len(history) < 2:
        return None
    rows = []
    for item in history:
        revenue = _num(item.get("revenue"))
        profit = _num(item.get("profit"))
        rows.append({
            "기간": item.get("year"),
            "매출(억원)": revenue,
            "영업이익(억원)": profit,
            "영업이익률": profit / revenue * 100 if revenue not in (None, 0) and profit is not None else None,
        })
    return pd.DataFrame(rows)


def _industry_map(focus):
    sectors = ["반도체", "전력·유틸리티", "방산·우주", "자동차", "인터넷·플랫폼", "2차전지", "바이오", "조선", "금융·보험", "철강·소재"]
    focus_sector = _sector_from_focus(focus)
    cells = []
    for name in sectors:
        active = name == focus_sector or (focus_sector == "유틸리티" and name == "전력·유틸리티") or (focus_sector == "인터넷" and name == "인터넷·플랫폼") or (focus_sector == "금융" and name == "금융·보험")
        cells.append(
            f'<div class="sd-sector {"active" if active else ""}">'
            f'<div class="sd-sector-name">{html.escape(name)}</div>'
            f'<div class="sd-sector-value">{"현재 종목" if active else "데이터 연결 필요"}</div>'
            f'<div class="sd-sector-note">sector.performance</div></div>'
        )
    return "".join(cells)


def _mini_metric(title, value, note="", tone="normal"):
    tone_color = {"up": UP, "down": RED, "blue": BLUE, "good": UP}.get(tone, TEXT)
    st.markdown(
        f'<div class="sd-metric"><div class="sd-label">{html.escape(title)}</div>'
        f'<div class="sd-value" style="color:{tone_color}">{html.escape(str(value))}</div>'
        f'<div class="sd-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def render_decision_dashboard(research: dict) -> None:
    """Final dashboard: market context -> stock position -> evidence -> conditional strategy -> industry map."""
    _css()
    snapshots = [_snapshot(x, x.get("name", "종목")) for x in research.values()]
    _ticker_row()

    st.markdown(
        f'<div style="display:flex;align-items:end;justify-content:space-between;margin-bottom:8px">'
        f'<div><span class="sd-brand">STOCK-DASH</span><small class="sd-brand"><small>투자분석 · 투자전략</small></small></div>'
        f'<div class="sd-date">데이터 기준일은 각 카드에 별도 표시</div></div>',
        unsafe_allow_html=True,
    )

    if not snapshots:
        st.info("조사된 종목이 없습니다. 종목을 추가하면 투자분석 화면이 채워집니다.")
        return

    selected_code = st.session_state.get("selected_code")
    by_code = {x["code"]: x for x in snapshots}
    focus = by_code.get(selected_code) or sorted(snapshots, key=lambda x: x.get("as_of") or "", reverse=True)[0]
    raw = research.get(focus["code"], {})

    st.markdown('<div class="sd-title">① 분석 종목 · 현재 위치</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4, gap="small")
    with a:
        focus_change = f"{focus['change']:+.2f}%" if focus["change"] is not None else "일간 등락 미확인"
        st.markdown(
            f'<div class="sd-hero"><div class="sd-name">{html.escape(focus["name"])}</div>'
            f'<div class="sd-code">{html.escape(focus["code"])} · {html.escape(focus.get("sector") or _sector_from_focus(focus))}</div>'
            f'<div class="sd-price">{html.escape(_fmt(focus["price"]))}</div>'
            f'<div class="sd-change">{html.escape(focus_change)}</div>'
            f'<span class="sd-badge">분석 대상</span><span class="sd-badge blue">데이터 기반</span></div>',
            unsafe_allow_html=True,
        )
    tech = _technical_stats(focus.get("prices") or [])
    position = f'{tech["position52"]:.1f}%' if tech.get("position52") is not None else "미확인"
    market_state = (
        "상승 추세" if tech.get("ma20") is not None and tech.get("ma60") is not None and tech["latest"] > tech["ma20"] > tech["ma60"]
        else "하락 추세" if tech.get("ma20") is not None and tech.get("ma60") is not None and tech["latest"] < tech["ma20"] < tech["ma60"]
        else "신호 혼합/확인 필요"
    ) if tech else "가격 데이터 연결 필요"
    volume_text = f'{tech["trading_value"]:,.0f}' if tech.get("trading_value") is not None else (
        f'{tech["volume"]:,.0f}' if tech.get("volume") is not None else "미확인"
    )
    for col, title, value, note in [
        (b, "52주 가격 위치", position, "52주 최저=0% · 최고=100%"),
        (c, "시장 상태", market_state, "20일선·60일선 기준"),
        (d, "거래대금 / 거래량", volume_text, "최근 거래일 기준"),
    ]:
        with col:
            st.markdown(
                f'<div class="sd-card"><div class="sd-card-title">{html.escape(title)}</div>'
                f'<div class="sd-card-value">{html.escape(value)}</div><div class="sd-card-note">{html.escape(note)}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="sd-title">② 핵심 투자지표</div>', unsafe_allow_html=True)
    vals = [
        ("매출 성장률", _pct_text(focus["rev"]), f'{focus.get("period") or "기간 미확인"} / 전년 대비'),
        ("영업이익 성장률", _pct_text(focus["op"]), f'{focus.get("period") or "기간 미확인"} / 전년 대비'),
        ("영업이익률", _pct_text(_margin(focus)), "영업이익 ÷ 매출"),
        ("외국인 수급", _flow_text(focus["foreign"], focus["flow_unit"]), "조사기간 순매수"),
        ("기관 수급", _flow_text(focus["institution"], focus["flow_unit"]), "조사기간 순매수"),
        ("적정가 참고", _fmt(focus["fair"]), "평가모형 참고값"),
    ]
    cols = st.columns(6, gap="small")
    for col, (title, value, note) in zip(cols, vals):
        with col:
            tone = "up" if isinstance(value, str) and value.startswith("+") else "blue" if title == "적정가 참고" else "normal"
            _mini_metric(title, value, note, tone)

    st.markdown('<div class="sd-title">③ 가격·기술적 분석 · ④ 투자판단 레이더</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, .85], gap="small")
    with left:
        st.markdown(
            '<div class="sd-panel"><h4>가격·기술적 분석</h4>'
            '<span class="sd-chip">일봉</span><span class="sd-chip">완료 주봉</span>'
            '<span class="sd-chip">추세</span><span class="sd-chip">RSI(14)</span>'
            '<span class="sd-chip">MACD</span><span class="sd-chip">20MA 대비</span></div>',
            unsafe_allow_html=True,
        )
        _trend(raw)
    with right:
        st.markdown('<div class="sd-panel"><h4>투자판단 레이더</h4>', unsafe_allow_html=True)
        for title, text_value, kind in _strategy(focus):
            border = {"good": UP, "caution": RED, "watch": BLUE}.get(kind, GOLD)
            st.markdown(
                f'<div class="sd-strategy" style="border-left-color:{border}"><b>{html.escape(title)}</b>'
                f'<span>{html.escape(text_value)}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sd-title">⑤ 투자전략 시나리오</div>', unsafe_allow_html=True)
    st.markdown('<div class="sd-sub">확률을 임의로 부여하지 않고, 조건이 충족될 때 다시 확인할 항목을 보여줍니다.</div>', unsafe_allow_html=True)
    scenarios = [
        ("up", "🟢 상승 조건", "실적 개선 지속", "매출·영업이익 증가와 수급 개선이 확인되면 다음 실적·업종 상대강도를 재확인"),
        ("neutral", "🟡 중립 조건", "현재 수준 유지", "실적은 유지되지만 가치·수급 신호가 엇갈리면 핵심 가격대와 다음 공시를 관찰"),
        ("down", "🔴 하락 조건", "핵심 가정 훼손", "이익 감소·수요 둔화·주요 리스크가 확인되면 하락 원인과 회복 조건을 재평가"),
    ]
    cols = st.columns(3, gap="small")
    for col, (klass, title, label, body) in zip(cols, scenarios):
        with col:
            st.markdown(
                f'<div class="sd-scenario {klass}"><b>{html.escape(title)}</b><strong>{html.escape(label)}</strong>'
                f'<p>{html.escape(body)}</p></div>', unsafe_allow_html=True
            )

    st.markdown('<div class="sd-title">⑥ 실적·기업분석 · 시장 수급</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, .85], gap="small")
    with left:
        f = raw.get("financial") or {}
        st.markdown('<div class="sd-panel"><h4>실적 트렌드</h4>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sd-business"><b>매출</b> {_fmt(f.get("revenue"), "")}'
            f' &nbsp; <b>영업이익</b> {_fmt(f.get("operating_profit"), "")}'
            f' &nbsp; <b>영업이익률</b> {_pct_text(_margin(focus))}'
            f'<br><br>{html.escape(focus["business"] or "공식 사업보고서 기반 기업 설명이 없습니다.")}'
            f'<br><br><b>핵심 요약</b> {html.escape(focus.get("summary") or "별도 조사 요약 없음")}</div>',
            unsafe_allow_html=True,
        )
        earnings_df = _earnings_history_table(focus)
        if earnings_df is not None:
            st.markdown("<br><b style='font-size:9px'>연도별 실적 추이</b>", unsafe_allow_html=True)
            st.dataframe(earnings_df, hide_index=True, use_container_width=True)
        peers = raw.get("peers") or {}
        if peers.get("rows"):
            st.markdown("<br><b style='font-size:9px'>경쟁사 영업이익 비교</b>", unsafe_allow_html=True)
            rows = [{"기업": x.get("name"), "영업이익": x.get("operating_profit"), "기간": peers.get("period")} for x in peers["rows"]]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        flow = raw.get("flow") or {}
        st.markdown('<div class="sd-panel"><h4>시장 수급</h4>', unsafe_allow_html=True)
        _mini_metric("외국인", _flow_text(flow.get("foreign"), flow.get("unit")), "순매수", "up")
        _mini_metric("기관", _flow_text(flow.get("institution"), flow.get("unit")), "순매수", "blue")
        _mini_metric("개인", "데이터 연결 필요", "시장 전체 투자자별 수급", "down")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sd-title">⑦ 업종별 투자지도</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sd-map"><div class="sd-map-head"><div class="sd-map-title">INDUSTRY INVESTMENT MAP</div>'
        f'<div class="sd-map-note">현재 종목 업종 · {html.escape(_sector_from_focus(focus))}</div></div>'
        f'<div class="sd-map-grid">{_industry_map(focus)}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sd-foot">데이터 기준일 · ' + html.escape(focus.get("as_of") or "미확인") +
        ' · 출처 · ' + html.escape(focus.get("source") or "미확인") +
        ' · 계산 기준 · ' + html.escape(focus.get("basis") or "미확인") +
        ' · 시장/업종 실시간 값은 연결된 공식·검증 가능한 provider가 있을 때만 표시합니다.</div>',
        unsafe_allow_html=True,
    )

    gaps = focus["gaps"]
    with st.expander("데이터 신뢰도 · 미확인/추가 확인 항목"):
        if gaps:
            for gap in gaps:
                st.write("• " + str(gap))
        else:
            st.write("현재 조사 결과에서 별도 미확인 항목이 없습니다.")
        st.caption("전략 영역은 매수·매도 명령이 아니라, 확인된 지표와 조건을 구조화한 화면입니다.")


__all__ = ["render_decision_dashboard"]
