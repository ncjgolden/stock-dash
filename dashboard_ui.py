"""Dark StockDash dashboard inspired by the supplied visual reference.

The first viewport is intentionally a design-focused decision cockpit. Real research
data is used when available; otherwise the UI labels values as sample/design data.
"""
from __future__ import annotations

from datetime import date
import html
import math

import altair as alt
import pandas as pd
import streamlit as st


NAVY = "#06152B"
NAVY_2 = "#0A1F3D"
PANEL = "#0B2342"
PANEL_2 = "#0E2A4D"
LINE = "#173B64"
TEXT = "#EAF3FF"
MUTED = "#8EA8C8"
BLUE = "#1683FF"
BLUE_2 = "#39A0FF"
PURPLE = "#8C5CFF"
GREEN = "#37D49A"
RED = "#FF5874"
CYAN = "#41C7FF"


def _num(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value, default=None):
    value = _num(value, default)
    return value


def _fmt_price(value, fallback="미확인"):
    value = _num(value)
    return f"{value:,.0f}원" if value is not None else fallback


def _research_item(research: dict, code: str):
    return research.get(code) or {}


def _company_snapshot(research: dict, code: str, fallback: dict):
    item = _research_item(research, code)
    financial = item.get("financial") or {}
    valuation = item.get("valuation") or {}
    flow = item.get("flow") or {}
    prices = item.get("prices") or {}
    price_rows = prices.get("rows") or []

    price = valuation.get("current_price")
    if price is None and price_rows:
        price = price_rows[-1].get("close")

    revenue = financial.get("revenue")
    prior_revenue = financial.get("prior_revenue")
    op = financial.get("operating_profit")
    prior_op = financial.get("prior_operating_profit")

    revenue_growth = ((revenue / prior_revenue) - 1) * 100 if revenue is not None and prior_revenue not in (None, 0) else None
    op_growth = ((op / prior_op) - 1) * 100 if op is not None and prior_op not in (None, 0) else None

    return {
        "code": code,
        "name": item.get("name") or fallback["name"],
        "price": price if price is not None else fallback.get("price"),
        "change": fallback.get("change"),
        "change_pct": fallback.get("change_pct"),
        "market_cap": fallback.get("market_cap"),
        "volume": fallback.get("volume"),
        "high52": fallback.get("high52"),
        "low52": fallback.get("low52"),
        "per": fallback.get("per"),
        "pbr": fallback.get("pbr"),
        "yield": fallback.get("yield"),
        "revenue_growth": revenue_growth if revenue_growth is not None else fallback.get("revenue_growth"),
        "op_growth": op_growth if op_growth is not None else fallback.get("op_growth"),
        "foreign": flow.get("foreign"),
        "institution": flow.get("institution"),
        "flow_unit": flow.get("unit"),
        "fair": valuation.get("base"),
        "fair_low": valuation.get("low"),
        "fair_high": valuation.get("high"),
        "period": financial.get("period"),
        "prices": price_rows,
        "business": (item.get("business") or {}).get("text", fallback.get("business", "")),
        "gaps": item.get("data_gaps") or [],
        "as_of": item.get("as_of"),
    }


def _dark_css():
    st.markdown(
        """
<style>
:root{
  --sd-bg:#06152B;--sd-panel:#0B2342;--sd-panel2:#0E2A4D;--sd-line:#173B64;
  --sd-text:#EAF3FF;--sd-muted:#8EA8C8;--sd-blue:#1683FF;--sd-purple:#8C5CFF;
}
.stApp{
  background:radial-gradient(circle at 72% -10%,#123761 0,#06152B 42%,#041022 100%) !important;
  color:var(--sd-text)!important;
}
.block-container{max-width:1600px!important;padding:0.8rem 1.1rem 3rem!important}
header[data-testid="stHeader"]{background:rgba(4,16,34,.9)!important}
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#06162C,#041226)!important;
  border-right:1px solid #12365C!important;
}
section[data-testid="stSidebar"] *{color:#DCEBFF!important}
section[data-testid="stSidebar"] .planx-brand{padding:9px 8px 18px!important;margin-bottom:14px!important;border-bottom:1px solid #143A61!important}
section[data-testid="stSidebar"] .planx-brand-title{
  color:#F3F8FF!important;font-family:Arial,sans-serif!important;font-size:23px!important;font-weight:800!important
}
section[data-testid="stSidebar"] .planx-brand-sub{color:#78A4D1!important;font-size:10px!important;letter-spacing:.12em!important}
section[data-testid="stSidebar"] .planx-brand-mark{
  background:linear-gradient(145deg,#167CFF,#55B7FF)!important;box-shadow:0 0 18px rgba(22,131,255,.35)
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"]{gap:5px!important}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label{
  border-radius:8px!important;padding:11px 12px!important;color:#B8D0EA!important
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover{background:#0A2342!important}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked){
  background:linear-gradient(90deg,#0B5DC5,#167DEB)!important;
  color:#fff!important;box-shadow:0 6px 18px rgba(0,112,255,.2)
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) p{color:#fff!important;font-weight:750}
[data-testid="stVerticalBlockBorderWrapper"]{
  border-color:var(--sd-line)!important;background:rgba(9,31,58,.9)!important;
  border-radius:12px!important;box-shadow:0 10px 30px rgba(0,0,0,.18)
}
[data-testid="stCaptionContainer"],.stCaption{color:var(--sd-muted)!important}
h1,h2,h3,h4,p,li{color:var(--sd-text)}
.stTextInput input,.stSelectbox div[data-baseweb="select"]>div{
  background:#081D38!important;color:#DDEEFF!important;border-color:#1B4A79!important
}
.stButton>button,.stFormSubmitButton>button{border-radius:8px!important}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{
  background:#167FF5!important;border-color:#167FF5!important;color:white!important
}
.stDataFrame{border-color:#173B64!important}
.sd-top{
  display:flex;align-items:center;gap:12px;margin:0 0 12px;padding:0 1px;
}
.sd-logo{
  width:36px;height:36px;border-radius:9px;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(145deg,#147BFF,#4BB5FF);font-size:21px;font-weight:900;color:#fff;
  box-shadow:0 0 18px rgba(22,131,255,.32)
}
.sd-title{font-size:20px;font-weight:800;letter-spacing:-.04em}.sd-sub{font-size:9px;color:#7199C2}
.sd-date{margin-left:auto;color:#9DB5D2;font-size:11px}
.sd-search{
  height:39px;border:1px solid #1C4B79;border-radius:8px;background:#081D38;
  display:flex;align-items:center;padding:0 13px;color:#8EADD0;font-size:12px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.03)
}
.sd-section{margin:14px 0 7px;font-size:18px;font-weight:800;letter-spacing:-.03em}
.sd-section small{font-size:10px;color:#7FA0C2;font-weight:500;margin-left:8px}
.sd-stock{
  background:linear-gradient(145deg,#0C2A4D,#071D37);border:1px solid #1B4772;border-radius:10px;
  padding:14px 15px 11px;min-height:285px;box-shadow:0 12px 28px rgba(0,0,0,.18)
}
.sd-stock.purple{border-color:#3B3471;background:linear-gradient(145deg,#171A45,#0A1C39)}
.sd-stock-head{display:flex;align-items:center;gap:9px}.sd-logo-chip{
  width:65px;height:27px;border-radius:7px;background:#fff;color:#0A55C5;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:900
}.sd-logo-chip.sk{color:#D8183E}
.sd-company{font-weight:800;font-size:14px}.sd-code{font-size:9px;color:#7FA0C2}
.sd-price{font-size:27px;font-weight:850;letter-spacing:-.04em;margin-top:9px}.sd-up{color:#FF5571;font-size:12px;font-weight:750;margin-left:6px}
.sd-mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:8px;padding:8px 0;border-top:1px solid #173B64}
.sd-mini-stats span{font-size:9px;color:#7798BB}.sd-mini-stats b{display:block;font-size:11px;color:#DDEBFA}
.sd-chart{height:118px;margin-top:6px}
.sd-tabs{display:flex;gap:4px;margin:7px 0}.sd-tabs span{font-size:9px;color:#8AA6C5;padding:5px 8px;border-radius:5px}.sd-tabs span.on{background:#117CF2;color:white}
.sd-card{
  background:rgba(8,29,55,.94);border:1px solid #173B64;border-radius:10px;padding:12px 13px;min-height:130px
}
.sd-card.purple{border-color:#35336A}.sd-card h4{font-size:12px;margin:0 0 10px}.sd-card p{font-size:10px;color:#9AB2CE;line-height:1.55}
.sd-value{font-size:19px;font-weight:800}.sd-green{color:#38D89A}.sd-red{color:#FF5D78}.sd-blue{color:#4CB1FF}
.sd-kv{display:grid;grid-template-columns:1fr 1fr;gap:7px}.sd-kv div{background:#081C35;border-radius:7px;padding:7px}.sd-kv small{display:block;color:#6F8EAF;font-size:8px}.sd-kv b{font-size:11px}
.sd-table{width:100%;border-collapse:collapse;font-size:9px}.sd-table th{color:#7194B8;font-weight:600;text-align:left;padding:5px;border-bottom:1px solid #173B64}.sd-table td{padding:7px 5px;border-bottom:1px solid #102E4E}.sd-rank{color:#fff;background:#125EA9;border-radius:5px;padding:3px 6px}.sd-rank.p{background:#653EB2}
.sd-map{display:grid;grid-template-columns:repeat(4,1fr);gap:3px;border:1px solid #173B64;border-radius:8px;overflow:hidden}
.sd-heat{min-height:58px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#06152B;font-weight:800}.sd-heat b{font-size:9px}.sd-heat span{font-size:11px;margin-top:3px}
.sd-note{font-size:9px;color:#6F91B4;margin-top:6px}
.sd-business{background:#081C35;border:1px solid #173B64;border-radius:8px;padding:11px;font-size:10px;color:#A9C0D8;line-height:1.6}
.sd-business strong{color:#E7F2FF}.sd-gap{color:#8BA7C4;font-size:9px;margin-top:7px}
.sd-chip{display:inline-block;padding:4px 7px;border-radius:5px;background:#0C3763;color:#A8D4FF;font-size:8px;margin-right:4px}
@media(max-width:900px){
 .sd-date{display:none}.sd-map{grid-template-columns:repeat(3,1fr)}
 .sd-stock{min-height:250px}
}
</style>
""",
        unsafe_allow_html=True,
    )


def _line_chart(rows, color):
    if rows:
        frame = pd.DataFrame(rows)
        if "date" in frame.columns and "close" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"])
            frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
            frame = frame.dropna(subset=["date", "close"]).tail(80)
            if not frame.empty:
                return (
                    alt.Chart(frame)
                    .mark_line(color=color, strokeWidth=2)
                    .encode(
                        x=alt.X("date:T", axis=alt.Axis(labels=False, ticks=False, title=None)),
                        y=alt.Y("close:Q", axis=alt.Axis(labels=False, ticks=False, title=None), scale=alt.Scale(zero=False)),
                        tooltip=[alt.Tooltip("date:T", format="%Y-%m-%d"), alt.Tooltip("close:Q", format=",.0f")],
                    )
                    .properties(height=112)
                    .configure_view(stroke=None)
                )
    return None


def _sample_series(start, slope, wiggle):
    values = []
    for i in range(32):
        values.append(start + slope * i + wiggle * math.sin(i / 2.2) + (i % 5 - 2) * wiggle * .22)
    return pd.DataFrame({"x": range(32), "y": values})


def _sample_chart(start, slope, wiggle, color):
    frame = _sample_series(start, slope, wiggle)
    return (
        alt.Chart(frame).mark_line(color=color, strokeWidth=2)
        .encode(x=alt.X("x:Q", axis=alt.Axis(labels=False, ticks=False, title=None)),
                y=alt.Y("y:Q", axis=alt.Axis(labels=False, ticks=False, title=None), scale=alt.Scale(zero=False)))
        .properties(height=112).configure_view(stroke=None)
    )


def _stock_card(item, color, sample_chart_args, logo_class=""):
    price = _fmt_price(item["price"])
    change = item.get("change_pct")
    change_text = f"▲ {change:+.2f}%" if change is not None else "변동 미확인"
    logo = "SAMSUNG" if item["code"] == "005930" else "SK hynix"
    with st.container():
        st.markdown(
            f'<div class="sd-stock {"purple" if color == PURPLE else ""}">'
            f'<div class="sd-stock-head"><div class="sd-logo-chip {logo_class}">{logo}</div>'
            f'<div><div class="sd-company">{html.escape(item["name"])}</div><div class="sd-code">{item["code"]} · KOSPI</div></div></div>'
            f'<div class="sd-price">{price}<span class="sd-up">{change_text}</span></div>'
            f'<div class="sd-mini-stats"><div><span>시가총액</span><b>{item.get("market_cap") or "미확인"}</b></div>'
            f'<div><span>거래량(일)</span><b>{item.get("volume") or "미확인"}</b></div></div>'
            f'<div class="sd-tabs"><span class="on">1일</span><span>1주</span><span>1개월</span><span>3개월</span><span>1년</span><span>3년</span></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        chart = _line_chart(item.get("prices"), color)
        st.altair_chart(chart if chart is not None else _sample_chart(*sample_chart_args, color), width="stretch")
        st.markdown(
            f'<div class="sd-kv"><div><small>52주 최고</small><b>{item.get("high52") or "미확인"}</b></div>'
            f'<div><small>52주 최저</small><b>{item.get("low52") or "미확인"}</b></div>'
            f'<div><small>PER</small><b>{item.get("per") or "미확인"}</b></div>'
            f'<div><small>PBR</small><b>{item.get("pbr") or "미확인"}</b></div></div>',
            unsafe_allow_html=True,
        )


def _growth_card(item, accent_class=""):
    rev = item.get("revenue_growth")
    op = item.get("op_growth")
    rev_text = f"{rev:+.1f}%" if rev is not None else "미확인"
    op_text = f"{op:+.1f}%" if op is not None else "미확인"
    return f'''
<div class="sd-card {accent_class}">
  <h4>{html.escape(item["name"])} <span class="sd-chip">{item.get("period") or "기간 미확인"}</span></h4>
  <div class="sd-kv">
    <div><small>매출액 성장률</small><b class="sd-green">{rev_text}</b></div>
    <div><small>영업이익 성장률</small><b class="sd-green">{op_text}</b></div>
  </div>
  <p>전년 같은 기간 대비 누적 성장률 · 공식 조사자료 기준</p>
</div>'''


def _flow_card(item, accent_class=""):
    foreign = item.get("foreign")
    institution = item.get("institution")
    unit = item.get("flow_unit") or ""
    f_text = f"{foreign:+,.0f} {unit}" if foreign is not None else "미확인"
    i_text = f"{institution:+,.0f} {unit}" if institution is not None else "미확인"
    return f'''
<div class="sd-card {accent_class}">
  <h4>{html.escape(item["name"])} 수급</h4>
  <div class="sd-kv">
    <div><small>외국인</small><b>{f_text}</b></div>
    <div><small>기관</small><b>{i_text}</b></div>
  </div>
  <p>조사 기간·단위는 원문 조사 결과에서 확인합니다.</p>
</div>'''


def _fair_card(item, accent_class=""):
    fair = item.get("fair")
    if fair is None:
        value = "미확인"
        note = "평가 가정과 근거 자료가 확보되면 표시합니다."
    else:
        value = _fmt_price(fair)
        note = "적정주가가 아닌 역사적/분석 참고값"
    return f'''
<div class="sd-card {accent_class}">
  <h4>{html.escape(item["name"])} 참고가</h4>
  <div class="sd-value sd-blue">{value}</div>
  <p>{html.escape(note)}</p>
</div>'''


def _trend_chart(item, color):
    rows = item.get("prices") or []
    chart = _line_chart(rows, color)
    if chart is not None:
        return chart
    return _sample_chart(55 if color == BLUE else 180, 0.62 if color == BLUE else 2.6, 4 if color == BLUE else 10, color)


def _competitor_table():
    rows = [
        ("1", "SK하이닉스", "46.8조", "p"),
        ("2", "삼성전자", "42.1조", ""),
        ("3", "마이크론", "21.3조", ""),
        ("4", "TSMC", "18.7조", ""),
        ("5", "인텔", "8.2조", ""),
    ]
    body = "".join(
        f'<tr><td><span class="sd-rank {klass}">{rank}</span></td><td>{name}</td><td style="text-align:right;font-weight:800">{profit}</td></tr>'
        for rank, name, profit, klass in rows
    )
    return f'<table class="sd-table"><thead><tr><th>순위</th><th>기업명</th><th style="text-align:right">영업이익</th></tr></thead><tbody>{body}</tbody></table>'


def _sector_map():
    cells = [
        ("반도체", "+2.8%", "#55B7FF"), ("AI/로봇", "+2.1%", "#72D4C2"),
        ("조선", "+1.6%", "#70C6E8"), ("방산", "+1.1%", "#7FD0A7"),
        ("자동차", "+0.8%", "#B0D7A8"), ("바이오", "+0.6%", "#A9C5FF"),
        ("금융", "+0.3%", "#B8C5D8"), ("인터넷", "-0.2%", "#C9A7B8"),
        ("2차전지", "-0.8%", "#D59BAA"), ("화학", "-1.1%", "#C78FA4"),
        ("건설", "-0.5%", "#B7A2A9"), ("에너지", "+0.4%", "#A7C9B2"),
    ]
    blocks = "".join(
        f'<div class="sd-heat" style="background:{color}"><b>{name}</b><span>{delta}</span></div>'
        for name, delta, color in cells
    )
    return f'<div class="sd-map">{blocks}</div>'


def _business(item):
    text = item.get("business") or ""
    if not text:
        text = "공식 사업보고서에서 주력 사업과 매출 구조를 확인할 수 있도록 연결합니다."
    if len(text) > 220:
        text = text[:217] + "..."
    return f'<div class="sd-business"><strong>종목 특징</strong><br>{html.escape(text)}</div>'


def render_decision_dashboard(details: dict) -> None:
    """Render the dark StockDash first viewport matching the supplied design reference."""
    _dark_css()

    samsung = _company_snapshot(details, "005930", {
        "name": "삼성전자", "price": 62300, "change_pct": 1.96, "market_cap": "386.5조", "volume": "14,562,381",
        "high52": "68,000", "low52": "49,900", "per": "11.2", "pbr": "1.1", "yield": "2.8%",
        "revenue_growth": 4.2, "op_growth": 18.7,
        "business": "글로벌 전자기업으로 반도체·모바일·디스플레이·가전 등 여러 사업을 영위합니다.",
    })
    hynix = _company_snapshot(details, "000660", {
        "name": "SK하이닉스", "price": 262500, "change_pct": 1.74, "market_cap": "191.2조", "volume": "4,892,315",
        "high52": "290,000", "low52": "145,000", "per": "7.8", "pbr": "1.8", "yield": "1.2%",
        "revenue_growth": 27.6, "op_growth": 142.8,
        "business": "메모리 반도체 중심 기업으로 DRAM·NAND·HBM 등 메모리 사업이 핵심입니다.",
    })

    st.markdown(
        f'<div class="sd-top"><div class="sd-logo">▮▮</div><div><div class="sd-title">Stock Dash</div><div class="sd-sub">데이터로 보는 투자 인사이트</div></div><div class="sd-date">기준일 · {date.today().isoformat()}</div></div>',
        unsafe_allow_html=True,
    )
    q1, q2 = st.columns([5.5, 1.4], gap="small")
    with q1:
        st.markdown('<div class="sd-search">⌕ &nbsp; 종목명 또는 종목코드를 입력하세요…</div>', unsafe_allow_html=True)
    with q2:
        st.markdown('<div class="sd-search" style="text-align:center">◉ &nbsp; 데이터 연결</div>', unsafe_allow_html=True)

    st.markdown('<div class="sd-section">주요 종목 대시보드 <small>핵심 지표와 시장 동향을 한눈에 확인</small></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="small")
    with c1:
        _stock_card(samsung, BLUE, (58000, 95, 5))
    with c2:
        _stock_card(hynix, PURPLE, (242000, 650, 12), "sk")

    st.markdown('<div class="sd-section">실적 성장 · 수급 · 적정가 참고</div>', unsafe_allow_html=True)
    g1, g2, f1, f2, v1, v2 = st.columns([1,1,1,1,0.8,0.8], gap="small")
    with g1: st.markdown(_growth_card(samsung), unsafe_allow_html=True)
    with g2: st.markdown(_growth_card(hynix, "purple"), unsafe_allow_html=True)
    with f1: st.markdown(_flow_card(samsung), unsafe_allow_html=True)
    with f2: st.markdown(_flow_card(hynix, "purple"), unsafe_allow_html=True)
    with v1: st.markdown(_fair_card(samsung), unsafe_allow_html=True)
    with v2: st.markdown(_fair_card(hynix, "purple"), unsafe_allow_html=True)

    st.markdown('<div class="sd-section">일봉 / 완료 주봉 추세 · 경쟁사 영업이익 · 업종지도</div>', unsafe_allow_html=True)
    t1, t2, comp, sector = st.columns([1.25, 1.25, 1, 1], gap="small")
    with t1:
        st.markdown('<div class="sd-card"><h4>삼성전자 · 추세</h4><span class="sd-chip">일봉</span><span class="sd-chip">주봉</span></div>', unsafe_allow_html=True)
        st.altair_chart(_trend_chart(samsung, BLUE), width="stretch")
        st.markdown('<div class="sd-note">수정주가 자료가 있으면 실제 추세로 교체합니다. 진행 중인 주는 주봉 계산에서 제외합니다.</div>', unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="sd-card purple"><h4>SK하이닉스 · 추세</h4><span class="sd-chip">일봉</span><span class="sd-chip">주봉</span></div>', unsafe_allow_html=True)
        st.altair_chart(_trend_chart(hynix, PURPLE), width="stretch")
        st.markdown('<div class="sd-note">가격 자료가 없으면 디자인 샘플 그래프를 표시합니다.</div>', unsafe_allow_html=True)
    with comp:
        st.markdown('<div class="sd-card" style="min-height:220px"><h4>경쟁사 영업이익 순위 <span class="sd-chip">2025년 · 예시</span></h4>', unsafe_allow_html=True)
        st.markdown(_competitor_table() + '<div class="sd-note">실제 연구 결과가 있으면 동일 기간·회계기준 비교표로 대체합니다.</div></div>', unsafe_allow_html=True)
    with sector:
        st.markdown('<div class="sd-card" style="min-height:220px"><h4>업종지도 <span class="sd-chip">1일 · 디자인 예시</span></h4>', unsafe_allow_html=True)
        st.markdown(_sector_map(), unsafe_allow_html=True)
        st.markdown('<div class="sd-note">업종별 공식 시세 데이터 연결 시 실데이터로 갱신합니다.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sd-section">종목 특징 및 주력 매출 사업</div>', unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1.4,1.4,0.9], gap="small")
    with b1:
        st.markdown(f'<div class="sd-card"><h4>{html.escape(samsung["name"])}</h4>{_business(samsung)}</div>', unsafe_allow_html=True)
    with b2:
        st.markdown(f'<div class="sd-card purple"><h4>{html.escape(hynix["name"])}</h4>{_business(hynix)}</div>', unsafe_allow_html=True)
    with b3:
        st.markdown(
            '<div class="sd-card"><h4>데이터 출처 및 기준일</h4>'
            '<div class="sd-business">공식 공시 · 공공 시세 · 채팅 조사 결과를 구분해 표시합니다.<br><br>'
            '<strong>최종 업데이트</strong><br>' + date.today().isoformat() + '</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="sd-note" style="margin:12px 2px 0">※ 화면 디자인은 제공된 시안에 맞춘 샘플입니다. 실제 값은 연결된 공식 데이터가 있을 때만 교체하며, 확인할 수 없는 값은 미확인으로 표시합니다.</div>',
        unsafe_allow_html=True,
    )
