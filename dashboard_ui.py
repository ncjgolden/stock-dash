"""Light investment decision cockpit for the research landing page."""
from __future__ import annotations
from datetime import date
import html
import pandas as pd
import streamlit as st
import altair as alt

UP = "#D63B3B"
DOWN = "#2F6FC0"
NAVY = "#17324D"
GOLD = "#B9944A"
GREEN = "#16804B"


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
        "change": None,
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
        "source": (f or {}).get("source") or (item.get("summary") or {}).get("source"),
        "as_of": item.get("as_of"),
    }


def _trend(item, color):
    rows = item.get("prices") or []
    if not rows:
        return
    df = pd.DataFrame(rows)
    if "date" not in df or "close" not in df:
        return
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna().tail(90)
    if df.empty:
        return
    chart = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X("date:T", axis=alt.Axis(labels=False, title=None)),
        y=alt.Y("close:Q", scale=alt.Scale(zero=False), axis=alt.Axis(title=None)),
        tooltip=["date:T", alt.Tooltip("close:Q", format=",.0f")],
    ).properties(height=145).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)


def _metric_card(title, value, note="", tone="normal"):
    color = {"up": UP, "down": DOWN, "good": GREEN}.get(tone, NAVY)
    st.markdown(
        f'<div class="px-metric"><div class="px-label">{html.escape(title)}</div>'
        f'<div class="px-value" style="color:{color}">{html.escape(str(value))}</div>'
        f'<div class="px-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def _pct_text(v):
    return f"{v:+.1f}%" if v is not None else "미확인"


def _flow_text(v, unit):
    return f"{v:+,.0f} {unit or ''}".strip() if v is not None else "미확인"


def _strategy(snapshot):
    checks = []
    if snapshot["rev"] is not None and snapshot["op"] is not None:
        if snapshot["rev"] > 0 and snapshot["op"] > 0:
            checks.append(("실적 모멘텀", "매출·영업이익 동반 증가가 이어지는지 다음 실적에서 확인", "good"))
        elif snapshot["rev"] > 0:
            checks.append(("이익률 점검", "매출 증가가 이익 증가로 연결되는지 원가·가격 확인", "watch"))
        else:
            checks.append(("실적 둔화", "매출과 이익의 회복 여부 및 원인 확인", "caution"))
    if snapshot["net"] is not None:
        checks.append(("순이익", "영업외손익·세금 등 일회성 효과 여부 확인", "good" if snapshot["net"] > 0 else "caution"))
    if snapshot["fair"] is not None:
        checks.append(("가치", "역사적 참고가와 현재가의 차이를 성장 지속성과 함께 검토", "watch"))
    else:
        checks.append(("가치", "검증 가능한 평가 가정이 부족해 참고가 보류", "caution"))
    if snapshot["foreign"] is not None or snapshot["institution"] is not None:
        checks.append(("수급", "외국인·기관 흐름을 실적과 같은 기간으로 비교", "watch"))
    else:
        checks.append(("수급", "수급 자료가 확보되기 전에는 방향성 판단을 보류", "caution"))
    return checks[:5]


def _css():
    st.markdown("""<style>
.stApp{background:#f6f8fb!important;color:#17324D}
.block-container{max-width:1560px!important;padding:1rem 1.2rem 3rem!important}
.px-head{display:flex;align-items:end;justify-content:space-between;border-bottom:1px solid #dfe5ec;padding:4px 2px 13px;margin-bottom:12px}
.px-brand{font-size:25px;font-weight:850;letter-spacing:-.04em}.px-brand small{font-size:10px;color:#7b899a;margin-left:8px}
.px-date{font-size:11px;color:#718096}
.px-search{background:white;border:1px solid #dbe2ea;border-radius:10px;padding:11px 14px;color:#718096;margin-bottom:10px}
.px-title{font-size:18px;font-weight:850;margin:13px 0 7px}
.px-card{background:white;border:1px solid #dce3eb;border-radius:13px;padding:14px;box-shadow:0 6px 18px rgba(31,51,73,.04)}
.px-name{font-size:22px;font-weight:900;color:#102f4d;letter-spacing:-.04em}.px-code{font-size:10px;color:#8190a1}
.px-price{font-size:27px;font-weight:900;margin:7px 0}.px-muted{color:#788697;font-size:10px}
.px-metric{background:white;border:1px solid #dce3eb;border-radius:11px;padding:13px;min-height:90px}
.px-label{font-size:10px;color:#738196;font-weight:750}.px-value{font-size:20px;font-weight:900;margin-top:6px}.px-note{font-size:9px;color:#8a96a4;margin-top:4px}
.px-chip{display:inline-block;background:#eef4fb;color:#315f8e;border-radius:99px;padding:4px 8px;font-size:9px;margin-right:4px}
.px-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}.px-cell{padding:14px 7px;text-align:center;border-radius:5px;font-weight:800;font-size:10px}
.px-cell b{display:block;font-size:12px;margin-top:4px}
.px-table{width:100%;border-collapse:collapse;font-size:10px}.px-table th,.px-table td{padding:8px;border-bottom:1px solid #edf0f3;text-align:left}.px-table th{color:#7b8795}
.px-strategy{border-left:4px solid #b9c5d2;background:white;border-top:1px solid #dce3eb;border-right:1px solid #dce3eb;border-bottom:1px solid #dce3eb;border-radius:0 9px 9px 0;padding:9px 12px;margin:5px 0}
.px-strategy b{font-size:11px}.px-strategy span{font-size:10px;color:#66778a;margin-left:8px}
.px-foot{font-size:10px;color:#7b8795;margin-top:10px}
@media(max-width:800px){.px-grid{grid-template-columns:repeat(2,1fr)}.px-name{font-size:19px}}
</style>""", unsafe_allow_html=True)


def render_decision_dashboard(research: dict) -> None:
    """Decision cockpit: input -> company -> financials -> valuation/flow -> sector -> monitoring plan."""
    _css()
    items = list(research.values())
    if items:
        snapshots = [_snapshot(x, x.get("name", "종목")) for x in items]
    else:
        snapshots = []

    st.markdown(f'<div class="px-head"><div><span class="px-brand">Stock Dash</span><small>INVESTMENT RESEARCH COCKPIT</small></div><div class="px-date">기준일 · {date.today().isoformat()}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="px-search">⌕ &nbsp; 분석할 종목을 입력하고, 검색 결과를 선택하면 기업·실적·수급·가치·업종 흐름을 한 화면에서 확인합니다.</div>', unsafe_allow_html=True)

    if not snapshots:
        st.info("아직 조사된 종목이 없습니다. 아래 '종목 추가'에서 기업명을 입력하면 분석 화면이 채워집니다.")
        return

    # Focus on the most recently researched company while retaining a compact comparison strip.
    focus = sorted(snapshots, key=lambda x: x.get("as_of") or "", reverse=True)[0]
    others = [x for x in snapshots if x["code"] != focus["code"]]

    st.markdown('<div class="px-title">① 분석 종목</div>', unsafe_allow_html=True)
    cols = st.columns(2 if others else 1, gap="small")
    for col, item in zip(cols, [focus] + others[:1]):
        with col:
            st.markdown(f'<div class="px-card"><div class="px-name">{html.escape(item["name"])}</div><div class="px-code">{html.escape(item["code"])} · 조사일 {html.escape(item.get("as_of") or "미확인")}</div><div class="px-price">{html.escape(_fmt(item["price"]))}</div><span class="px-chip">매출 {_pct_text(item["rev"])}</span><span class="px-chip">영업이익 {_pct_text(item["op"])}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="px-title">② 핵심 투자지표</div>', unsafe_allow_html=True)
    vals = [
        ("매출 성장률", _pct_text(focus["rev"]), "전년 같은 기간 누적"),
        ("영업이익 성장률", _pct_text(focus["op"]), "전년 같은 기간 누적"),
        ("순이익 성장률", _pct_text(focus["net"]), "순이익 자료가 있을 때"),
        ("영업이익률", _pct_text(_margin(focus)), "영업이익 ÷ 매출"),
        ("외국인", _flow_text(focus["foreign"], focus["flow_unit"]), "조사기간 순매수"),
        ("기관", _flow_text(focus["institution"], focus["flow_unit"]), "조사기간 순매수"),
        ("적정가 참고", _fmt(focus["fair"]), "평가모형 참고값"),
        ("자료 기준일", focus.get("as_of") or "미확인", "공개 조사 기준"),
    ]
    for row in [vals[:4], vals[4:]]:
        c = st.columns(4, gap="small")
        for col, (title, value, note) in zip(c, row):
            with col: _metric_card(title, value, note, "up" if isinstance(value,str) and value.startswith("+") else "normal")

    left, right = st.columns([1.15, .85], gap="small")
    with left:
        st.markdown('<div class="px-title">③ 주가 흐름</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown(f'<b>{html.escape(focus["name"])}</b> <span class="px-muted">수정주가 기준</span>', unsafe_allow_html=True)
            _trend(focus, NAVY)
            if not focus["prices"]:
                st.caption("수정주가 시계열이 없으면 임의 그래프를 표시하지 않습니다.")
    with right:
        st.markdown('<div class="px-title">④ 투자전략 체크리스트</div>', unsafe_allow_html=True)
        for title, text, kind in _strategy(focus):
            border = {"good":GREEN, "caution":UP, "watch":GOLD}.get(kind, "#b9c5d2")
            st.markdown(f'<div class="px-strategy" style="border-left-color:{border}"><b>{html.escape(title)}</b><span>{html.escape(text)}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="px-title">⑤ 전체 업종·시장 흐름</div>', unsafe_allow_html=True)
    with st.container():
        # Use researched sectors when available; never invent percentages.
        sector_rows = []
        for item in snapshots:
            sectors = item.get("business", "")
            label = item["name"]
            sector_rows.append((label, "기업별 섹터 분류는 사업보고서 확인 필요"))
        if sector_rows:
            st.dataframe(pd.DataFrame(sector_rows, columns=["분석 종목","업종 확인"]), hide_index=True, use_container_width=True)
        st.caption("KOSPI/KOSDAQ·업종별 등락·거래대금·시장 수급은 별도 시장 API 연결이 필요합니다. 데이터가 없으면 숫자를 임의 생성하지 않습니다.")

    st.markdown('<div class="px-title">⑥ 경쟁사·기업 특징</div>', unsafe_allow_html=True)
    a,b=st.columns(2,gap="small")
    with a:
        st.markdown('<div class="px-card"><b>경쟁사 영업이익 비교</b></div>', unsafe_allow_html=True)
        rows = []
        # Prefer the actual peer block of the focus report.
        # The research schema defines this as a within-sample absolute operating-profit comparison.
        for x in (research.get(focus["code"], {}).get("peers") or {}).get("rows", []):
            rows.append([x.get("name"), x.get("operating_profit"), x.get("period")])
        if rows:
            df=pd.DataFrame(rows,columns=["기업","영업이익","기간"])
            df["순위"]=df["영업이익"].rank(method="min",ascending=False).astype(int)
            st.dataframe(df.sort_values("순위")[["순위","기업","영업이익","기간"]],hide_index=True,use_container_width=True)
        else:
            st.info("동일 기간·회계기준의 경쟁사 자료가 없습니다.")
    with b:
        st.markdown(f'<div class="px-card"><b>{html.escape(focus["name"])} 기업 특징·주력사업</b><p class="px-muted">{html.escape(focus["business"] or "공식 사업보고서 설명 자료가 없습니다.")}</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="px-title">⑦ 데이터 신뢰도·추가 확인</div>', unsafe_allow_html=True)
    gaps = focus["gaps"]
    if gaps:
        for gap in gaps: st.write("• " + str(gap))
    else:
        st.success("현재 조사 결과에서 별도 미확인 항목이 없습니다.")
    st.markdown(f'<div class="px-foot">※ 이 화면의 전략 영역은 매수·매도 명령이 아니라, 확인된 지표를 바탕으로 다음에 확인할 조건을 정리합니다. 공식 자료·기준일·기간을 함께 확인하세요.</div>', unsafe_allow_html=True)


def _fmt(v):
    if v is None: return "미확인"
    try: return f"{float(v):,.0f}원"
    except (TypeError,ValueError): return str(v)


def _margin(s):
    op, rev = _num(s.get("op_value")), _num(s.get("revenue_value"))
    return op / rev * 100 if op is not None and rev not in (None, 0) else None
