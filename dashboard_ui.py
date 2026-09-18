"""Investment-analysis dashboard UI for the StockDash research landing page."""
from __future__ import annotations

from datetime import date
import html

import altair as alt
import pandas as pd
import streamlit as st


UP = "#D63B3B"
DOWN = "#2F6FC0"
NAVY = "#17324D"
GOLD = "#B9944A"
GREEN = "#16804B"
MUTED = "#718096"
BORDER = "#DCE3EB"
BG = "#F4F7FA"


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
        "change": item.get("change"),
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


def _trend(item):
    rows = item.get("prices") or []
    if not rows:
        st.info("현재 수정주가 시계열이 없습니다. 실제 데이터가 연결되면 일봉 차트가 표시됩니다.")
        return

    df = pd.DataFrame(rows)
    if "date" not in df or "close" not in df:
        st.info("주가 데이터 형식이 일봉 분석에 충분하지 않습니다.")
        return
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna().tail(120)
    if df.empty:
        st.info("표시할 주가 데이터가 없습니다.")
        return

    chart = (
        alt.Chart(df)
        .mark_line(color=NAVY, strokeWidth=2)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("close:Q", title="종가", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("date:T", title="일자"),
                alt.Tooltip("close:Q", title="종가", format=",.0f"),
            ],
        )
        .properties(height=300)
        .configure_view(stroke=None)
        .configure_axis(gridColor="#E9EEF3", labelColor="#66778A", titleColor="#66778A")
    )
    st.altair_chart(chart, use_container_width=True)


def _mini_metric(title, value, note="", tone="normal"):
    color = {"up": UP, "down": DOWN, "good": GREEN}.get(tone, NAVY)
    st.markdown(
        f'<div class="sd-metric"><div class="sd-label">{html.escape(title)}</div>'
        f'<div class="sd-value" style="color:{color}">{html.escape(str(value))}</div>'
        f'<div class="sd-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def _strategy(snapshot):
    checks = []
    rev, op, net = snapshot["rev"], snapshot["op"], snapshot["net"]

    if rev is not None and op is not None:
        if rev > 0 and op > 0:
            checks.append(("실적 모멘텀", "매출과 영업이익의 동반 증가가 다음 실적에서도 이어지는지 확인", "good"))
        elif rev > 0:
            checks.append(("이익 전환 확인", "매출 증가가 영업이익 증가로 연결되는지 원가·가격 요인을 확인", "watch"))
        else:
            checks.append(("실적 둔화", "매출·이익 둔화의 원인과 회복 조건을 다음 공시에서 확인", "caution"))
    else:
        checks.append(("실적 자료", "동일 기준의 전년 대비 실적 자료가 확보되면 변화 방향을 확인", "caution"))

    if net is not None:
        checks.append(("순이익", "영업외손익·세금 등 일회성 요인이 포함됐는지 확인", "good" if net > 0 else "caution"))

    if snapshot["fair"] is not None:
        checks.append(("가치", "참고가와 현재가의 차이를 성장 지속성과 평가 가정과 함께 검토", "watch"))
    else:
        checks.append(("가치", "검증 가능한 평가 가정이 부족하므로 참고가 판단을 보류", "caution"))

    if snapshot["foreign"] is not None or snapshot["institution"] is not None:
        checks.append(("수급", "외국인·기관 흐름이 실적 및 주가 변화와 함께 움직이는지 비교", "watch"))
    else:
        checks.append(("수급", "수급 자료가 연결되기 전에는 방향성 판단을 보류", "caution"))
    return checks[:5]


def _market_cards():
    return [
        ("KOSPI", "지수 / 등락률", "market.index"),
        ("KOSDAQ", "지수 / 등락률", "market.index"),
        ("주도 업종", "업종별 등락 / 거래대금", "sector.performance"),
        ("시장 수급", "외국인 / 기관 / 개인", "market.investor_flow"),
        ("거래대금", "시장 / 업종 / 종목", "market.turnover"),
        ("원/달러", "환율 / 변동", "macro.fx"),
    ]


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


def _industry_map(focus):
    # Do not fabricate market performance. The tiles are intentionally data-ready:
    # real sector values should come from a future sector.performance provider.
    sectors = [
        ("반도체", "Semiconductor"),
        ("자동차", "Auto"),
        ("바이오", "Bio"),
        ("방산", "Defense"),
        ("금융", "Finance"),
        ("2차전지", "Battery"),
        ("조선", "Shipbuilding"),
        ("유틸리티", "Utility"),
        ("인터넷", "Internet"),
        ("미분류", "Other"),
    ]
    focus_sector = _sector_from_focus(focus)
    cells = []
    for name, en in sectors:
        active = name == focus_sector
        cells.append(
            f'<div class="sd-sector {"active" if active else ""}">'
            f'<div class="sd-sector-name">{html.escape(name)}</div>'
            f'<div class="sd-sector-en">{html.escape(en)}</div>'
            f'<div class="sd-sector-value">{"현재 종목" if active else "데이터 연결 필요"}</div>'
            f'<div class="sd-sector-note">sector.performance</div>'
            f'</div>'
        )
    return "".join(cells)


def _css():
    st.markdown(
        """<style>
.stApp{background:#F4F7FA!important;color:#17324D}
.block-container{max-width:1580px!important;padding:1.1rem 1.35rem 3.5rem!important}
.sd-head{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #DCE3EB;padding:4px 2px 13px;margin-bottom:12px}
.sd-brand{font-size:27px;font-weight:900;letter-spacing:-.05em;color:#102F4D}
.sd-brand small{font-size:10px;color:#8190A1;letter-spacing:.08em;margin-left:9px}
.sd-date{font-size:10px;color:#7A8795}
.sd-search{background:#fff;border:1px solid #DCE3EB;border-radius:12px;padding:11px 14px;color:#718096;margin-bottom:13px}
.sd-title{font-size:17px;font-weight:900;letter-spacing:-.035em;color:#17324D;margin:15px 0 8px}
.sd-sub{font-size:10px;color:#7B8999;margin:-3px 0 8px}
.sd-card{background:#fff;border:1px solid #DCE3EB;border-radius:14px;padding:16px;box-shadow:0 6px 18px rgba(31,51,73,.045)}
.sd-hero{background:#fff;border:1px solid #D5DEE8;border-radius:16px;padding:18px 20px;box-shadow:0 8px 22px rgba(31,51,73,.055)}
.sd-name{font-size:25px;font-weight:950;letter-spacing:-.05em;color:#102F4D}
.sd-code{font-size:10px;color:#8794A3;margin-top:2px}
.sd-price{font-size:31px;font-weight:950;color:#102F4D;margin:9px 0 2px}
.sd-change{font-size:12px;font-weight:800;color:#16804B}
.sd-state{display:inline-block;background:#EEF4FB;color:#315F8E;border-radius:999px;padding:5px 9px;font-size:9px;margin-top:8px}
.sd-meta{text-align:right;font-size:10px;color:#758396;line-height:1.9}
.sd-metric{background:#fff;border:1px solid #DCE3EB;border-radius:11px;padding:13px;min-height:92px}
.sd-label{font-size:10px;color:#738196;font-weight:800}
.sd-value{font-size:20px;font-weight:950;margin-top:6px;letter-spacing:-.03em}
.sd-note{font-size:9px;color:#8A96A4;margin-top:4px;line-height:1.4}
.sd-section{background:#fff;border:1px solid #DCE3EB;border-radius:14px;padding:15px}
.sd-section h4{font-size:13px;margin:0 0 10px;color:#17324D}
.sd-chip{display:inline-block;background:#EEF4FB;color:#315F8E;border-radius:999px;padding:5px 8px;font-size:9px;margin:2px 3px 2px 0}
.sd-strategy{border-left:4px solid #B9C5D2;background:#fff;border-top:1px solid #DCE3EB;border-right:1px solid #DCE3EB;border-bottom:1px solid #DCE3EB;border-radius:0 9px 9px 0;padding:10px 12px;margin:6px 0}
.sd-strategy b{font-size:11px}.sd-strategy span{font-size:10px;color:#66778A;margin-left:8px;line-height:1.45}
.sd-scenario{border:1px solid #DCE3EB;border-radius:11px;padding:12px;min-height:112px;background:#fff}
.sd-scenario b{font-size:11px;color:#17324D}.sd-scenario strong{display:block;font-size:15px;margin:7px 0}.sd-scenario p{font-size:9px;color:#718096;line-height:1.5;margin:0}
.sd-radar{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
.sd-radar-cell{border:1px solid #E1E7ED;border-radius:9px;padding:11px;background:#FBFCFD}
.sd-radar-cell b{font-size:10px;display:block;color:#17324D}.sd-radar-cell span{font-size:9px;color:#8A96A4}
.sd-map{background:#122C43;border-radius:16px;padding:17px;color:#fff}
.sd-map-head{display:flex;justify-content:space-between;align-items:end;margin-bottom:11px}
.sd-map-title{font-size:16px;font-weight:900}.sd-map-note{font-size:9px;color:#AAB8C5}
.sd-map-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px}
.sd-sector{min-height:88px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.055);border-radius:9px;padding:10px}
.sd-sector.active{border-color:#D8B66A;background:rgba(185,148,74,.16)}
.sd-sector-name{font-size:11px;font-weight:900}.sd-sector-en{font-size:8px;color:#91A2B2;margin-top:1px}
.sd-sector-value{font-size:10px;font-weight:800;margin-top:11px;color:#E7EEF3}
.sd-sector-note{font-size:7px;color:#8195A7;margin-top:3px}
.sd-foot{font-size:9px;color:#7B8795;margin-top:10px;line-height:1.5}
@media(max-width:900px){.sd-map-grid{grid-template-columns:repeat(2,1fr)}.sd-radar{grid-template-columns:repeat(2,1fr)}}
</style>""",
        unsafe_allow_html=True,
    )


def render_decision_dashboard(research: dict) -> None:
    """Investment cockpit: stock -> indicators -> charts -> strategy -> market -> industry map."""
    _css()
    items = list(research.values())
    snapshots = [_snapshot(x, x.get("name", "종목")) for x in items] if items else []

    st.markdown(
        f'<div class="sd-head"><div><span class="sd-brand">STOCK-DASH</span>'
        f'<small>투자분석 · 투자전략 대시보드</small></div>'
        f'<div class="sd-date">기준일 · {date.today().isoformat()}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sd-search">⌕ &nbsp; <b>분석할 종목</b>을 선택하면 주가 · 실적 · 수급 · 가치 · 경쟁사 · 시장 · 업종 흐름을 한 화면에서 연결합니다.</div>',
        unsafe_allow_html=True,
    )

    if not snapshots:
        st.info("아직 조사된 종목이 없습니다. 아래 '종목 추가'에서 기업명을 입력하면 투자분석 화면이 채워집니다.")
        return

    selected_code = st.session_state.get("selected_code")
    by_code = {x["code"]: x for x in snapshots}
    focus = by_code.get(selected_code) or sorted(
        snapshots, key=lambda x: x.get("as_of") or "", reverse=True
    )[0]
    others = [x for x in snapshots if x["code"] != focus["code"]]

    # 1. Hero / stock context
    st.markdown('<div class="sd-title">① 분석 종목 · 현재 위치</div>', unsafe_allow_html=True)
    hero_cols = st.columns([2.15, 1], gap="small")
    with hero_cols[0]:
        change = focus.get("change")
        change_text = f"{change:+.2f}%" if change is not None else "일간 등락 데이터 미수집"
        st.markdown(
            f'<div class="sd-hero"><div class="sd-name">{html.escape(focus["name"])}</div>'
            f'<div class="sd-code">{html.escape(focus["code"])} · 조사 기준일 {html.escape(focus.get("as_of") or "미확인")}</div>'
            f'<div class="sd-price">{html.escape(_fmt(focus["price"]))}</div>'
            f'<div class="sd-change">{html.escape(change_text)}</div>'
            f'<span class="sd-state">투자분석 대상 · 데이터 기반 확인</span></div>',
            unsafe_allow_html=True,
        )
    with hero_cols[1]:
        st.markdown('<div class="sd-card"><b>최근 분석 범위</b><div class="sd-meta">'
                    f'결산 · {html.escape(focus.get("period") or "미확인")}<br>'
                    f'기준 · {html.escape(str((research.get(focus["code"], {}).get("financial") or {}).get("basis") or "미확인"))}<br>'
                    f'자료 · {html.escape(focus.get("source") or "미확인")[:55]}'
                    f'</div></div>', unsafe_allow_html=True)

    # 2. Core investment indicators
    st.markdown('<div class="sd-title">② 핵심 투자지표</div>', unsafe_allow_html=True)
    vals = [
        ("매출 성장률", _pct_text(focus["rev"]), "전년 동일 기간"),
        ("영업이익 성장률", _pct_text(focus["op"]), "전년 동일 기간"),
        ("영업이익률", _pct_text(_margin(focus)), "영업이익 ÷ 매출"),
        ("순이익 성장률", _pct_text(focus["net"]), "자료 확보 시"),
        ("외국인", _flow_text(focus["foreign"], focus["flow_unit"]), "조사기간 순매수"),
        ("기관", _flow_text(focus["institution"], focus["flow_unit"]), "조사기간 순매수"),
        ("적정가 참고", _fmt(focus["fair"]), "평가모형 참고값"),
        ("자료 기준일", focus.get("as_of") or "미확인", "공개 조사 기준"),
    ]
    for row in (vals[:4], vals[4:]):
        cols = st.columns(4, gap="small")
        for col, (title, value, note) in zip(cols, row):
            with col:
                tone = "up" if isinstance(value, str) and value.startswith("+") else "normal"
                _mini_metric(title, value, note, tone)

    # 3. Technical analysis + investment judgement
    st.markdown('<div class="sd-title">③ 가격·기술적 분석 + ④ 투자판단</div>', unsafe_allow_html=True)
    left, right = st.columns([1.45, .85], gap="small")
    with left:
        st.markdown(
            '<div class="sd-section"><h4>주가 흐름 · 일봉 / 완료 주봉 분석 영역</h4>'
            '<span class="sd-chip">일봉</span><span class="sd-chip">완료 주봉</span>'
            '<span class="sd-chip">추세</span><span class="sd-chip">RSI</span></div>',
            unsafe_allow_html=True,
        )
        _trend(focus)
        if focus["prices"]:
            st.caption("실제 확보된 시계열만 표시합니다. 일봉·완료 주봉 지표를 단계적으로 확장할 수 있습니다.")
        else:
            st.caption("현재 데이터에는 주가 시계열이 없어 임의의 차트를 생성하지 않습니다.")

    with right:
        st.markdown('<div class="sd-section"><h4>투자판단 핵심 체크</h4></div>', unsafe_allow_html=True)
        for title, text_value, kind in _strategy(focus):
            border = {"good": GREEN, "caution": UP, "watch": GOLD}.get(kind, "#B9C5D2")
            st.markdown(
                f'<div class="sd-strategy" style="border-left-color:{border}">'
                f'<b>{html.escape(title)}</b><span>{html.escape(text_value)}</span></div>',
                unsafe_allow_html=True,
            )

    # 5. Strategy scenarios
    st.markdown('<div class="sd-title">⑤ 투자전략 시나리오</div>', unsafe_allow_html=True)
    st.markdown('<div class="sd-sub">예측값을 단정하지 않고, 조건이 충족될 때 무엇을 다시 확인할지 구조화합니다.</div>', unsafe_allow_html=True)
    scenarios = [
        ("상승 시나리오", "실적 개선 지속", "매출·영업이익 증가 + 수급 개선이 확인되는 경우", "다음 실적과 업종 상대강도를 재확인"),
        ("중립 시나리오", "현재 수준 유지", "실적은 유지되지만 가치·수급 신호가 엇갈리는 경우", "핵심 가격대와 다음 공시를 관찰"),
        ("하락 시나리오", "실적 둔화", "이익 감소 또는 핵심 가정이 훼손되는 경우", "하락 원인과 회복 조건을 먼저 확인"),
    ]
    scols = st.columns(3, gap="small")
    for col, (title, label, condition, action) in zip(scols, scenarios):
        with col:
            st.markdown(
                f'<div class="sd-scenario"><b>{html.escape(title)}</b>'
                f'<strong>{html.escape(label)}</strong>'
                f'<p>조건 · {html.escape(condition)}<br>확인 · {html.escape(action)}</p></div>',
                unsafe_allow_html=True,
            )

    # 6. Fundamentals / peers
    st.markdown('<div class="sd-title">⑥ 실적·기업분석</div>', unsafe_allow_html=True)
    a, b = st.columns([1.05, .95], gap="small")
    with a:
        st.markdown('<div class="sd-card"><b>경쟁사 영업이익 비교</b></div>', unsafe_allow_html=True)
        rows = []
        for x in (research.get(focus["code"], {}).get("peers") or {}).get("rows", []):
            rows.append([x.get("name"), x.get("operating_profit"), x.get("period")])
        if rows:
            df = pd.DataFrame(rows, columns=["기업", "영업이익", "기간"])
            df["순위"] = df["영업이익"].rank(method="min", ascending=False).astype(int)
            st.dataframe(
                df.sort_values("순위")[["순위", "기업", "영업이익", "기간"]],
                hide_index=True,
                use_container_width=True,
            )
            st.caption("동일 기간·회계기준 표본의 전사 영업이익 비교입니다. 사업부 경쟁력 순위와 동일하지 않습니다.")
        else:
            st.info("동일 기간·회계기준의 경쟁사 자료가 없습니다.")
    with b:
        st.markdown(
            f'<div class="sd-card"><b>{html.escape(focus["name"])} · 기업 특징 / 주력사업</b>'
            f'<p style="font-size:11px;line-height:1.65;color:#66778A">'
            f'{html.escape(focus["business"] or "공식 사업보고서 설명 자료가 없습니다.")}</p></div>',
            unsafe_allow_html=True,
        )

    # 7. Market radar
    st.markdown('<div class="sd-title">⑦ 시장·수급 레이더</div>', unsafe_allow_html=True)
    radar = st.container()
    with radar:
        cells = []
        for name, desc, cap in _market_cards():
            cells.append(
                f'<div class="sd-radar-cell"><b>{html.escape(name)}</b>'
                f'<span>{html.escape(desc)} · {html.escape(cap)}</span><br>'
                f'<span>데이터 연결 필요</span></div>'
            )
        st.markdown('<div class="sd-radar">' + "".join(cells) + '</div>', unsafe_allow_html=True)
        st.caption("시장·업종 API가 연결되면 실제 지수, 등락률, 거래대금, 투자자별 수급을 이 영역에 채웁니다. 숫자는 임의 생성하지 않습니다.")

    # 8. Investment decision checklist
    st.markdown('<div class="sd-title">⑧ 종합 확인 항목</div>', unsafe_allow_html=True)
    checks = [
        ("실적", "매출 → 영업이익 → 순이익 방향"),
        ("수익성", "영업이익률 개선·유지·하락"),
        ("가치", "참고가와 현재가의 거리"),
        ("수급", "외국인·기관과 주가의 동행"),
        ("시장", "지수와 해당 업종의 상대 흐름"),
        ("리스크", "공시·원가·환율·고객·정책"),
    ]
    cols = st.columns(3, gap="small")
    for col, (title, desc) in zip(cols * 2, checks):
        with col:
            _mini_metric(title, "확인", desc, "good")

    # 9. Industry investment map MUST remain at the bottom.
    st.markdown('<div class="sd-title">⑨ 업종별 투자지도</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sd-map"><div class="sd-map-head"><div class="sd-map-title">INDUSTRY INVESTMENT MAP</div>'
        f'<div class="sd-map-note">현재 종목 업종 · {_sector_from_focus(focus)} · 실제 업종 수급/등락 데이터 연결 예정</div></div>'
        f'<div class="sd-map-grid">{_industry_map(focus)}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sd-foot">※ 업종별 색·등락률·거래대금은 sector.performance API 연결 후 실제 데이터로 표시하도록 설계했습니다. '
        '현재는 화면 구조와 현재 종목의 업종 위치만 보여주며, 투자 판단을 위한 가상 수치를 만들지 않습니다.</div>',
        unsafe_allow_html=True,
    )

    gaps = focus["gaps"]
    if gaps:
        with st.expander("데이터 신뢰도 · 추가 확인 항목"):
            for gap in gaps:
                st.write("• " + str(gap))
    else:
        with st.expander("데이터 신뢰도 · 추가 확인 항목"):
            st.success("현재 조사 결과에서 별도 미확인 항목이 없습니다.")

    st.caption("전략 영역은 매수·매도 명령이 아니라, 확인된 지표와 조건을 바탕으로 다음 점검 항목을 구조화합니다. 공식 자료·기준일·기간을 함께 확인하세요.")
