"""Premium PlanX decision dashboard.

The first screen deliberately uses labelled sample market data when an official
market capability is not connected. Stored company research is used whenever
it is available; the UI never presents the sample values as live data.
"""
from __future__ import annotations

from datetime import date
import html

import altair as alt
import pandas as pd
import streamlit as st


NAVY = "#17324D"
GOLD = "#B9944A"
GREEN = "#16804B"
RED = "#D64B4B"
BLUE = "#3677D8"
PAPER = "#FFFDF8"


def _spark(values: list[float], color: str) -> alt.Chart:
    frame = pd.DataFrame({"순서": range(len(values)), "값": values})
    return (
        alt.Chart(frame)
        .mark_line(color=color, strokeWidth=2)
        .encode(x=alt.X("순서:Q", axis=None), y=alt.Y("값:Q", axis=None, scale=alt.Scale(zero=False)))
        .properties(height=34)
        .configure_view(stroke=None)
    )


def _market_strip() -> None:
    markets = [
        ("KOSPI", "2,482.36", "+0.75%", RED, [42, 44, 43, 47, 46, 50, 49, 53]),
        ("KOSDAQ", "723.61", "+0.89%", RED, [35, 37, 36, 39, 42, 41, 44, 43]),
        ("USD/KRW", "1,386.20", "-0.29%", BLUE, [52, 50, 53, 51, 54, 49, 48, 46]),
        ("WTI", "67.24", "+0.93%", RED, [32, 34, 33, 37, 36, 39, 40, 43]),
        ("GOLD", "2,577.30", "+0.48%", RED, [45, 46, 48, 47, 50, 51, 50, 53]),
    ]
    cols = st.columns(5, gap="small")
    for col, (name, value, delta, color, points) in zip(cols, markets):
        with col:
            st.markdown(
                f'<div class="px-market"><span>{name}</span><strong>{value}</strong>'
                f'<em style="color:{color}">{delta}</em></div>',
                unsafe_allow_html=True,
            )
            st.altair_chart(_spark(points, color), width="stretch")
    st.caption("화면 구성 예시 · 시장 API 연결 전 샘플 수치이며 실시간 데이터가 아닙니다.")


def _score_card(title: str, icon: str, state: str, headline: str, note: str, bars: list[int], tone: str = GREEN) -> None:
    columns = "".join(f'<i style="height:{max(10, value)}%;background:{tone}"></i>' for value in bars)
    st.markdown(
        f"""
        <div class="px-signal">
          <div class="px-signal-head"><b>{icon} {html.escape(title)}</b><span>{html.escape(state)}</span></div>
          <h4>{html.escape(headline)}</h4><p>{html.escape(note)}</p>
          <div class="px-bars">{columns}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _decision_cards() -> None:
    cols = st.columns([1.05, 1, 1, 1, 1, 1], gap="small")
    with cols[0]:
        st.markdown(
            """
            <div class="px-score">
              <div class="px-score-title">종합 투자점수 <b>78</b></div>
              <div class="px-ring"><strong>78</strong><span>/100</span></div>
              <div class="px-score-row"><span>매크로</span><b>76</b></div>
              <div class="px-score-row"><span>산업 경쟁력</span><b>82</b></div>
              <div class="px-score-row"><span>실적</span><b>80</b></div>
              <div class="px-score-row"><span>밸류에이션</span><b>70</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    cards = [
        ("매크로", "◎", "중립", "안정적인 흐름 지속", "금리와 유동성의 방향을 확인합니다.", [28, 34, 40, 48, 56], "#BCC3CA"),
        ("성장산업", "◒", "긍정", "AI 반도체 수요 확대", "산업 성장과 투자 계획을 함께 봅니다.", [24, 34, 47, 62, 78], GREEN),
        ("수출·수주", "▰", "긍정", "수출 개선세 지속", "수출·수주가 매출로 전환되는지 봅니다.", [26, 38, 49, 63, 82], GREEN),
        ("실적 성장", "▥", "긍정", "견조한 이익 성장", "매출보다 영업이익의 속도를 봅니다.", [32, 42, 50, 61, 79], GREEN),
        ("수급 강도", "↗", "긍정", "매수 우위 지속", "기관과 외국인의 방향을 확인합니다.", [30, 43, 58, 72, 55], BLUE),
    ]
    for col, args in zip(cols[1:], cards):
        with col:
            _score_card(*args)


def _price_chart() -> None:
    dates = pd.date_range("2024-01-01", periods=24, freq="MS")
    samsung = [100, 103, 106, 105, 110, 113, 111, 116, 120, 119, 124, 128, 132, 130, 137, 142, 140, 148, 151, 147, 158, 163, 160, 166]
    kospi = [100, 102, 104, 103, 106, 107, 106, 109, 111, 110, 112, 115, 117, 116, 119, 121, 120, 123, 124, 122, 126, 128, 127, 130]
    sector = [100, 104, 108, 107, 112, 116, 114, 121, 126, 124, 131, 136, 141, 138, 146, 153, 151, 160, 166, 161, 172, 179, 176, 185]
    frame = pd.DataFrame({"날짜": list(dates) * 3, "수익률": samsung + kospi + sector, "구분": ["삼성전자"] * 24 + ["KOSPI"] * 24 + ["반도체"] * 24})
    chart = (
        alt.Chart(frame)
        .mark_line(strokeWidth=2.2)
        .encode(
            x=alt.X("날짜:T", title=None, axis=alt.Axis(format="%y.%m", labelAngle=0, tickCount=6)),
            y=alt.Y("수익률:Q", title="지수화 (시작=100)", scale=alt.Scale(zero=False)),
            color=alt.Color("구분:N", scale=alt.Scale(domain=["삼성전자", "KOSPI", "반도체"], range=[GREEN, BLUE, GOLD]), legend=alt.Legend(orient="top")),
            tooltip=[alt.Tooltip("날짜:T", format="%Y-%m"), "구분:N", "수익률:Q"],
        )
        .properties(height=295)
        .configure(background=PAPER)
        .configure_view(stroke=None)
        .configure_axis(gridColor="#EEE8DC", labelColor="#617086", titleColor="#617086")
        .configure_legend(labelColor=NAVY, title=None)
    )
    st.altair_chart(chart, width="stretch")


def _heatmap() -> None:
    cells = [
        ("반도체", "+2.8%", "#137747", "wide"), ("IT하드웨어", "+1.5%", "#32945F", ""),
        ("자동차", "+1.2%", "#55A671", ""), ("2차전지", "-0.8%", "#EAA6A6", ""),
        ("바이오", "+0.6%", "#ADD7C0", ""), ("인터넷", "+1.9%", "#27875B", ""),
        ("금융", "+0.4%", "#C7E3D1", ""), ("에너지", "-0.3%", "#F2C9C9", ""),
        ("화학", "-1.1%", "#AFC9EE", ""), ("기계", "+0.7%", "#9FCFB5", ""),
        ("건설", "-0.6%", "#E9B2B2", ""), ("통신", "+0.2%", "#C5DFC9", ""),
    ]
    blocks = "".join(f'<div class="px-heat {klass}" style="background:{color}"><b>{name}</b><span>{delta}</span></div>' for name, delta, color, klass in cells)
    st.markdown(f'<div class="px-heatmap">{blocks}</div>', unsafe_allow_html=True)


def _watchlist() -> None:
    rows = [
        ("삼성전자", "72,400", "+2.69%", "up"), ("SK하이닉스", "198,500", "+1.53%", "up"),
        ("현대차", "273,000", "-0.36%", "down"), ("기아", "122,400", "+0.82%", "up"),
        ("NAVER", "215,000", "+1.42%", "up"), ("카카오", "39,850", "+0.76%", "up"),
    ]
    body = "".join(f'<div class="px-watch-row"><span>★ {name}</span><b>{price}</b><em class="{klass}">{change}</em></div>' for name, price, change, klass in rows)
    st.markdown(f'<div class="px-watch">{body}</div>', unsafe_allow_html=True)


def _bottom_cards() -> None:
    left, middle, right = st.columns([1.08, 1, 1.35], gap="small")
    with left:
        st.markdown('<div class="px-panel-title">실적 추이 <span>매출액 · 영업이익</span></div>', unsafe_allow_html=True)
        earnings = pd.DataFrame({"분기": ["3Q23", "4Q23", "1Q24", "2Q24", "3Q24", "4Q24(E)"], "매출": [67, 72, 72, 74, 79, 84], "영업이익": [42, 45, 48, 52, 60, 67]}).melt("분기", var_name="구분", value_name="값")
        chart = alt.Chart(earnings).mark_bar().encode(x=alt.X("분기:N", axis=alt.Axis(labelAngle=0), title=None), y=alt.Y("값:Q", title=None), xOffset="구분:N", color=alt.Color("구분:N", scale=alt.Scale(range=[BLUE, "#CBD1D7"]), legend=None)).properties(height=150).configure_view(stroke=None).configure_axis(grid=False)
        st.altair_chart(chart, width="stretch")
    with middle:
        st.markdown('<div class="px-panel-title">적정가치 <span>PER 기준</span></div>', unsafe_allow_html=True)
        st.markdown('''<div class="px-value"><b>현재 72,400원</b><div class="px-value-line"><i></i><strong></strong></div><div class="px-value-label"><span>52,000</span><span>68,000</span><span>86,000</span><span>102,000</span></div><small>역사적 범위 참고 · 목표주가 아님</small></div>''', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="px-panel-title">✦ AI 브리핑 <span>화면 예시</span></div>', unsafe_allow_html=True)
        st.markdown('''<div class="px-brief"><b>AI</b><ul><li>반도체 수요 확대와 영업이익 개선을 함께 확인합니다.</li><li>환율과 메모리 가격 변화가 다음 실적의 핵심 변수입니다.</li><li>현재 가격은 역사적 범위와 실제 전망치를 구분해 판단해야 합니다.</li></ul></div>''', unsafe_allow_html=True)


def render_decision_dashboard(details: dict) -> None:
    """Render the premium first viewport above the existing research workflow."""
    st.markdown(
        '<div class="px-topline"><div><span>PlanX</span><b>STOCK INTELLIGENCE</b><small>더 깊은 분석이, 더 나은 투자를</small></div><div class="px-date">'
        + date.today().strftime("%Y년 %m월 %d일") + ' · <i></i> 시장 데이터 샘플</div></div>',
        unsafe_allow_html=True,
    )
    _market_strip()
    st.markdown('<div class="px-title-row"><h2>오늘의 투자판단</h2><div><span>시장</span><i>›</i><span>산업</span><i>›</i><span>기업</span><i>›</i><b>투자판단</b></div></div>', unsafe_allow_html=True)
    _decision_cards()
    st.markdown('<div class="px-section-head"><div><h3>삼성전자 <small>005930</small></h3><strong>72,400원 <em>▲ +2.69%</em></strong></div><span>1년 · 샘플 데이터</span></div>', unsafe_allow_html=True)
    chart_col, heat_col, watch_col = st.columns([2.45, 1, 1.05], gap="small")
    with chart_col:
        _price_chart()
    with heat_col:
        st.markdown('<div class="px-panel-title">섹터별 등락률 <span>1일</span></div>', unsafe_allow_html=True)
        _heatmap()
    with watch_col:
        st.markdown('<div class="px-panel-title">관심종목 <span>더보기 ›</span></div>', unsafe_allow_html=True)
        _watchlist()
    _bottom_cards()
    st.markdown('''<div class="px-education"><div><b>교육자료</b><span>차트 기초 · 기술적 분석 · 투자 전략</span></div><div class="px-pens"><i></i><i></i><i></i><i></i></div><small>차트에 직접 그려보며 학습해보세요.</small></div>''', unsafe_allow_html=True)
    st.markdown('<div class="px-live-divider"><span>내 관심종목 실데이터 분석</span></div>', unsafe_allow_html=True)
