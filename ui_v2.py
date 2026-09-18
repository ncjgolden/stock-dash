from __future__ import annotations

import html
import streamlit as st


NAV_ITEMS = [
    ("홈", "⌂"),
    ("시장 현황", "▥"),
    ("종목 분석", "◫"),
    ("공시 분석", "▤"),
    ("테마 & 섹터", "◇"),
    ("포트폴리오", "▣"),
    ("관심 종목", "☆"),
    ("AI 인사이트", "✦"),
    ("데이터 연결 관리", "⚙"),
]


def apply_theme():
    st.markdown(
        """
<style>
:root {
  --bg: #F7F9FC;
  --surface: #FFFFFF;
  --surface-soft: #F9FBFF;
  --line: #E6EAF0;
  --line-strong: #D8DEE8;
  --text: #0F172A;
  --muted: #64748B;
  --blue: #2563EB;
  --blue-soft: #EFF6FF;
  --green: #059669;
  --red: #DC2626;
}
html, body, [class*="css"] {
  font-family: Pretendard, "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
}
.stApp {
  background: var(--bg);
  color: var(--text);
}
.block-container {
  max-width: 1480px;
  padding-top: 1.4rem;
  padding-bottom: 4rem;
}
header[data-testid="stHeader"] {
  background: rgba(247,249,252,.88);
  backdrop-filter: blur(12px);
}
section[data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div {
  padding-top: .9rem;
}
[data-testid="stSidebar"] .stRadio > label {
  display: none;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
  gap: .18rem;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
  border-radius: 12px;
  padding: .45rem .55rem;
  transition: all .15s ease;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
  background: #F3F6FB;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
  background: #EAF2FF;
  color: #1D4ED8;
  font-weight: 700;
}
h1, h2, h3, h4 {
  color: var(--text);
  letter-spacing: -.035em;
}
h1 { font-weight: 800; }
h2, h3 { font-weight: 760; }
p, li { line-height: 1.62; }
[data-testid="stCaptionContainer"] {
  color: var(--muted);
}
[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 8px 24px rgba(15,23,42,.035);
}
[data-testid="stMetricLabel"] {
  color: var(--muted);
}
[data-testid="stMetricValue"] {
  color: var(--text);
  font-weight: 750;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--line) !important;
  border-radius: 16px !important;
  background: var(--surface);
  box-shadow: 0 8px 24px rgba(15,23,42,.03);
}
.stButton > button, .stFormSubmitButton > button {
  border-radius: 11px;
  min-height: 2.7rem;
  font-weight: 700;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--blue);
  border-color: var(--blue);
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
  border-radius: 12px !important;
}
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px;
  padding: 8px 12px;
}
.stDataFrame {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}
.planx-brand {
  display:flex; align-items:center; gap:10px; margin: 2px 0 18px 0;
}
.planx-brand-mark {
  width:32px; height:32px; border-radius:10px;
  display:flex; align-items:center; justify-content:center;
  background:linear-gradient(145deg,#2563EB,#60A5FA);
  color:white; font-size:18px; font-weight:800;
}
.planx-brand-title {
  font-size:18px; line-height:1.15; font-weight:800; letter-spacing:-.03em;
}
.planx-brand-sub {
  font-size:10px; color:#94A3B8; margin-top:2px;
}
.planx-hero {
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FBFF 55%, #EFF6FF 100%);
  border: 1px solid #E2E8F0;
  border-radius: 22px;
  padding: 28px 30px;
  margin-bottom: 18px;
  box-shadow: 0 14px 38px rgba(15,23,42,.045);
}
.planx-eyebrow {
  color:#2563EB; font-size:12px; font-weight:800; letter-spacing:.08em;
  text-transform:uppercase; margin-bottom:8px;
}
.planx-hero h1 {
  margin:0; font-size:34px; line-height:1.18;
}
.planx-hero p {
  margin:9px 0 0; color:#64748B; font-size:14px;
}
.planx-card {
  background:#FFFFFF;
  border:1px solid #E6EAF0;
  border-radius:16px;
  padding:17px 18px;
  min-height:116px;
  box-shadow:0 8px 24px rgba(15,23,42,.03);
}
.planx-card-title {
  font-size:12px; color:#64748B; margin-bottom:8px; font-weight:700;
}
.planx-card-value {
  font-size:22px; color:#0F172A; font-weight:800; letter-spacing:-.03em;
}
.planx-card-note {
  margin-top:7px; font-size:11px; color:#94A3B8;
}
.planx-empty {
  background: #FFFFFF;
  border:1px dashed #CBD5E1;
  border-radius:16px;
  padding:22px;
  color:#64748B;
}
.planx-source {
  display:inline-flex; align-items:center; gap:5px;
  color:#64748B; background:#F8FAFC; border:1px solid #E2E8F0;
  padding:4px 8px; border-radius:999px; font-size:10px;
}
.planx-status-ok { color:#047857; background:#ECFDF5; border-color:#A7F3D0; }
.planx-status-wait { color:#92400E; background:#FFFBEB; border-color:#FDE68A; }
.planx-status-bad { color:#B91C1C; background:#FEF2F2; border-color:#FECACA; }
hr { border-color:#E6EAF0 !important; }
@media (max-width: 900px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .planx-hero { padding:22px 20px; }
  .planx-hero h1 { font-size:28px; }
}
/* Quiet, readable research workspace. */
.block-container { max-width:1240px; padding-top:2rem; }
.stApp { background:#f8f6f1; }
section[data-testid="stSidebar"] { background:#eee7da; border-right:0; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#493e2f; }
section[data-testid="stSidebar"] .planx-brand-title { color:#493e2f; font-size:22px; }
section[data-testid="stSidebar"] .planx-brand-sub { color:#806e50; font-size:13px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] { gap:10px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { padding:14px 12px; border-radius:8px; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover { background:#e7ddc9; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) { background:#dfcea8; box-shadow:inset 3px 0 #ad873f; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) p { color:#493e2f; }
[data-testid="stSidebar"] .stButton button p { color:#1b2c45; }
.planx-brand { margin:12px 0 36px; }
.planx-brand-mark { background:#a17c36; border-radius:9px; width:38px; height:38px; }
.planx-hero { background:transparent; border:0; border-radius:0; padding:0 0 18px; box-shadow:none; margin-bottom:6px; }
.planx-hero h1 { font-size:36px; font-weight:750; }
.planx-hero p { font-size:16px; color:#77674e; max-width:650px; }
.planx-eyebrow { font-size:12px; color:#98763a; letter-spacing:.12em; }
.planx-card { box-shadow:none; min-height:132px; border-radius:12px; padding:22px; border-top:3px solid #b1883c; }
.planx-card-title { font-size:14px; font-weight:500; }
.planx-card-value { font-size:28px; font-variant-numeric:tabular-nums; }
.planx-card-note { font-size:13px; color:#5d6d82; }
[data-testid="stMetric"] { box-shadow:none; border-radius:12px; }
[data-testid="stExpander"] { background:#fff; border-radius:10px; }
[data-testid="stExpander"] summary p { font-size:15px; }
[data-testid="stMarkdownContainer"] p { font-size:16px; line-height:1.75; }
[data-testid="stCaptionContainer"] p { font-size:14px; }
.stTabs [data-baseweb="tab-list"] { gap:4px; overflow-x:auto; }
.stTabs [data-baseweb="tab"] { font-size:15px; padding:12px 14px; white-space:nowrap; }
.stTextInput input { min-height:46px; font-size:16px; background:#fff; }
.stButton > button, .stFormSubmitButton > button { min-height:44px; border-radius:8px; }
@media (max-width:640px) {
  .block-container { padding-top:1.3rem; }
  .planx-hero h1 { font-size:28px; }
  .planx-card { min-height:100px; padding:14px; }
  .planx-card-value { font-size:23px; }
}
/* PlanX premium decision cockpit */
:root{--px-navy:#17324D;--px-gold:#B9944A;--px-ivory:#FBF7EE;--px-paper:#FFFDF8;--px-green:#16804B}
.stApp{background:linear-gradient(135deg,#fbf8f1 0%,#fffdf8 56%,#f8f4ea 100%)!important;color:var(--px-navy)}
.block-container{max-width:1680px!important;padding:1.05rem 1.35rem 4rem!important}
section[data-testid="stSidebar"]{background:#f8f2e7!important;border-right:1px solid #e9dfcf!important}
section[data-testid="stSidebar"] .planx-brand{padding:8px 10px 18px;border-bottom:1px solid #ded2bf;margin-bottom:18px}
section[data-testid="stSidebar"] .planx-brand-title{font-family:Georgia,"Times New Roman",serif;font-size:35px!important;color:#8a6428!important;font-weight:600}
section[data-testid="stSidebar"] .planx-brand-sub{font-size:10px!important;letter-spacing:.16em;color:#46576c!important}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label{padding:13px 14px!important;border-radius:8px!important}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked){background:#ede2cf!important;box-shadow:inset 3px 0 #b9944a!important}
.px-topline{display:flex;align-items:center;justify-content:space-between;padding:0 2px 12px;color:var(--px-navy)}
.px-topline>div:first-child{display:flex;align-items:baseline;gap:15px}.px-topline span{font:600 34px/1 Georgia,serif;color:#8a6428}.px-topline b{font-size:14px;letter-spacing:.2em}.px-topline small{font-size:11px;color:#778396}.px-date{font-size:12px;font-weight:650}.px-date i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#1c9a64;margin:0 5px}
.px-market{background:rgba(255,255,255,.75);border:1px solid #e7ded0;border-bottom:0;border-radius:12px 12px 0 0;padding:11px 13px 3px;display:grid;grid-template-columns:1fr auto;align-items:end}.px-market span{grid-column:1/-1;font-size:11px;font-weight:750}.px-market strong{font:700 22px/1.15 Georgia,serif;color:var(--px-navy)}.px-market em{font-size:11px;font-style:normal;font-weight:700}
.px-title-row{display:flex;align-items:center;gap:36px;margin:13px 0 9px}.px-title-row h2{font-size:20px!important;margin:0!important}.px-title-row>div{display:flex;align-items:center;gap:8px;flex:1}.px-title-row span,.px-title-row b{padding:8px 24px;background:#f4f1eb;border-radius:8px;font-size:12px;min-width:95px;text-align:center}.px-title-row b{background:linear-gradient(135deg,#c8a159,#aa7b2e);color:white}.px-title-row i{font-style:normal;color:#aaa}
.px-score,.px-signal{height:208px;box-sizing:border-box;background:rgba(255,255,255,.86);border:1px solid #e8dfd2;border-radius:10px;padding:14px;box-shadow:0 9px 22px rgba(67,52,31,.035)}
.px-score-title{font-size:13px;font-weight:750}.px-score-title b{font:700 23px Georgia,serif;color:#8d6423;margin-left:6px}.px-ring{width:92px;height:92px;margin:8px auto;border-radius:50%;background:conic-gradient(var(--px-green) 0 78%,#e5e8e4 78% 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative}.px-ring:before{content:"";position:absolute;inset:10px;background:white;border-radius:50%}.px-ring strong,.px-ring span{z-index:1}.px-ring strong{font:700 30px Georgia,serif}.px-ring span{font-size:10px;color:#78869a}.px-score-row{display:flex;justify-content:space-between;font-size:10px;margin-top:2px}.px-signal-head{display:flex;align-items:center;justify-content:space-between;font-size:13px}.px-signal-head span{font-size:9px;padding:3px 8px;border-radius:999px;background:#e7f3eb;color:#337753}.px-signal h4{font-size:14px!important;margin:16px 0 6px!important}.px-signal p{font-size:11px!important;line-height:1.5!important;color:#6b7889;min-height:50px}.px-bars{height:48px;display:flex;align-items:end;gap:6px}.px-bars i{display:block;flex:1;opacity:.95;border-radius:2px 2px 0 0}
.px-section-head{display:flex;align-items:end;justify-content:space-between;margin:12px 0 3px;padding:10px 14px 6px;background:#fff;border:1px solid #e8dfd2;border-bottom:0;border-radius:10px 10px 0 0}.px-section-head h3{font-size:18px!important;margin:0 0 5px!important}.px-section-head h3 small{font-size:10px;color:#718096}.px-section-head strong{font:700 22px Georgia,serif}.px-section-head em{font:700 12px Pretendard,sans-serif;color:#d74242}.px-section-head>span{font-size:10px;color:#8490a0}
.px-panel-title{height:38px;box-sizing:border-box;display:flex;justify-content:space-between;align-items:center;padding:9px 11px;background:#fff;border:1px solid #e7ded0;border-bottom:0;border-radius:10px 10px 0 0;font-size:12px;font-weight:800}.px-panel-title span{font-size:9px;color:#7d8998;font-weight:600}
.px-heatmap{height:295px;display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(3,1fr);gap:1px;border-radius:0 0 9px 9px;overflow:hidden}.px-heat{display:flex;flex-direction:column;align-items:center;justify-content:center;color:#17324d;font-size:10px;text-align:center}.px-heat b{font-size:10px}.px-heat span{font:700 12px Georgia,serif;margin-top:3px}.px-watch{height:295px;box-sizing:border-box;background:#fff;border:1px solid #e7ded0;border-radius:0 0 9px 9px;padding:6px 10px}.px-watch-row{display:grid;grid-template-columns:1fr auto 50px;gap:7px;align-items:center;padding:10px 2px;border-bottom:1px solid #eee8df;font-size:10px}.px-watch-row b{font:600 10px Georgia,serif}.px-watch-row em{font-style:normal;font-weight:750;text-align:right}.px-watch-row em.up{color:#d64242}.px-watch-row em.down{color:#2f6dc3}
.px-value{height:150px;background:#fff;padding:25px 16px 10px;border:1px solid #e7ded0;border-top:0;text-align:center}.px-value>b{font-size:12px}.px-value-line{height:8px;border-radius:8px;background:#e9e7e2;margin:30px 10px 10px;position:relative}.px-value-line i{display:block;position:absolute;left:28%;right:26%;height:100%;background:#4d9a6a;border-radius:8px}.px-value-line strong{position:absolute;width:12px;height:12px;border-radius:50%;background:#9d722c;border:2px solid white;top:-4px;left:51%;box-shadow:0 1px 3px #888}.px-value-label{display:flex;justify-content:space-between;font-size:9px;color:#7c8895}.px-value small{display:block;margin-top:16px;color:#8a95a2;font-size:9px}.px-brief{height:150px;box-sizing:border-box;background:#f5f2ec;border:1px solid #e7ded0;border-top:0;padding:15px;display:flex;gap:10px}.px-brief>b{width:28px;height:28px;border-radius:6px;background:#e2e5e7;display:flex;align-items:center;justify-content:center;font-size:11px}.px-brief ul{padding:0 0 0 15px;margin:0}.px-brief li{font-size:10px!important;line-height:1.7!important;color:#536277}
.px-education{margin-top:9px;background:#fff;border:1px solid #e7ded0;border-radius:10px;padding:10px 14px;display:flex;align-items:center;gap:20px;font-size:11px}.px-education b{margin-right:13px}.px-education span,.px-education small{color:#718096}.px-pens{display:flex;gap:8px;margin-left:auto}.px-pens i{width:17px;height:5px;border-radius:5px;transform:rotate(-42deg);background:#d83c3c}.px-pens i:nth-child(2){background:#3677d8}.px-pens i:nth-child(3){background:#16804b}.px-pens i:nth-child(4){background:#171717}.px-live-divider{display:flex;align-items:center;gap:12px;margin:28px 0 8px;color:#80612f;font-size:11px;font-weight:800;letter-spacing:.08em}.px-live-divider:before,.px-live-divider:after{content:"";height:1px;background:#d9cbb5;flex:1}
@media(max-width:1100px){.px-score,.px-signal{height:230px}.px-topline small{display:none}.px-title-row span,.px-title-row b{min-width:auto;padding:7px 12px}.px-watch-row{grid-template-columns:1fr auto}.px-watch-row em{display:none}}
@media(max-width:700px){.block-container{padding:.8rem!important}.px-topline{align-items:flex-start}.px-topline>div:first-child{display:block}.px-topline span{font-size:27px}.px-topline b{display:block;font-size:10px;margin-top:4px}.px-date{display:none}.px-title-row{display:block}.px-title-row>div{overflow-x:auto;margin-top:8px}.px-score,.px-signal{height:auto;min-height:190px}.px-section-head{display:block}.px-section-head>span{display:block;margin-top:7px}.px-education{flex-wrap:wrap}.px-pens{margin-left:0}}
</style>
""",
        unsafe_allow_html=True,
    )


def brand():
    st.markdown(
        """
<div class="planx-brand">
  <div>
    <div class="planx-brand-title">PlanX</div>
    <div class="planx-brand-sub">STOCK INTELLIGENCE</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, eyebrow: str = "PLANX INVESTMENT OS"):
    st.markdown(
        f"""
<div class="planx-hero">
  <div class="planx-eyebrow">{html.escape(eyebrow)}</div>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def card(title: str, value: str, note: str = "", status: str = ""):
    status_html = f'<div class="planx-card-note">{html.escape(status)}</div>' if status else ""
    st.markdown(
        f"""
<div class="planx-card">
  <div class="planx-card-title">{html.escape(title)}</div>
  <div class="planx-card-value">{html.escape(value)}</div>
  <div class="planx-card-note">{html.escape(note)}</div>
  {status_html}
</div>
""",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str):
    st.markdown(
        f"""
<div class="planx-empty">
  <strong style="color:#334155">{html.escape(title)}</strong><br>
  <span>{html.escape(message)}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def source_badge(label: str, state: str = "wait"):
    cls = {"ok": "planx-status-ok", "bad": "planx-status-bad"}.get(state, "planx-status-wait")
    st.markdown(
        f'<span class="planx-source {cls}">{html.escape(label)}</span>',
        unsafe_allow_html=True,
    )
