"""Account holdings stay in this authenticated session; public reports use existing storage."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from automatic import brief
from broker_kis import BrokerError, KIS
from providers import Official


INPUT_KEYS = ('kis_input_mode', 'kis_input_key', 'kis_input_secret', 'kis_input_cano', 'kis_input_product')


def disconnect_account():
    for key in ('kis_client', 'kis_signature', 'kis_session_connection', 'account_snapshot',
                'account_results', 'account_notes', 'account_note'):
        st.session_state.pop(key, None)
    st.session_state.kis_clear_inputs = True


def render_portfolio(store, sample_mode):
    st.header('내 계좌 자동 분석')
    st.caption('한국투자증권 국내주식 · 잔고 조회와 분석 · 조회 시점 기준')
    st.markdown("""<style>
    .st-key-account_connection {background:#fffdf7;border:1px solid #d8c799;border-radius:12px;padding:24px;}
    .st-key-account_connection label p {font-size:18px!important;line-height:1.6;}
    .st-key-account_connection input {font-size:18px!important;min-height:48px;}
    .st-key-account_connection button {min-height:52px;font-size:18px!important;}
    </style>""", unsafe_allow_html=True)
    if sample_mode:
        st.info('앱 운영자가 APP_PASSWORD를 설정하면 개인 계좌 연결이 열립니다.')
        return
    # Remove credentials and holdings from legacy environment-based sessions.
    if st.session_state.get('kis_client') and not st.session_state.get('kis_session_connection'):
        disconnect_account()
    if st.session_state.pop('kis_clear_inputs', False):
        for key in INPUT_KEYS:
            st.session_state.pop(key, None)
    client = st.session_state.get('kis_client')
    if client:
        with st.container(border=True):
            st.success(('모의' if client.mode == 'demo' else '실전') + ' 계좌 연결됨 · 현재 접속에서만 사용')
            if st.button('계좌 연결 해제', use_container_width=True):
                disconnect_account()
                st.rerun()
    else:
        with st.container(key='account_connection'):
            st.subheader('내 계좌 연결')
            st.write('① 투자 환경 선택 → ② 발급받은 키 입력 → ③ 연결 확인')
            st.caption('입력한 키는 이 앱 서버의 현재 접속 세션에서만 처리합니다. 저장소·AI로 전송하지 않습니다.')
            st.link_button('한국투자증권 API 발급 안내', 'https://apiportal.koreainvestment.com/intro')
            with st.form('kis_connect'):
                mode = st.radio('투자 환경', ['모의투자', '실전투자'], horizontal=True, key='kis_input_mode')
                key = st.text_input('App Key', type='password', key='kis_input_key')
                secret = st.text_input('App Secret', type='password', key='kis_input_secret')
                cano = st.text_input('계좌번호 앞 8자리', type='password', max_chars=8, key='kis_input_cano')
                product = st.text_input('계좌번호 뒤 2자리', max_chars=2, key='kis_input_product')
                submitted = st.form_submit_button('연결 확인', type='primary', use_container_width=True)
            if submitted:
                try:
                    candidate = KIS(key=key, secret=secret, cano=cano, product=product,
                                    mode='demo' if mode == '모의투자' else 'real')
                    with st.spinner('계좌 연결과 잔고 조회 권한을 확인합니다…'):
                        snapshot = candidate.balance()
                    st.session_state.kis_client = candidate
                    st.session_state.kis_session_connection = True
                    st.session_state.account_snapshot = snapshot
                    st.session_state.account_results = {}
                    st.session_state.kis_clear_inputs = True
                    st.rerun()
                except BrokerError as error:
                    st.error(str(error))
        st.info('연결 해제·로그아웃 시 키와 계좌 조회 자료를 제거합니다. 재접속 시 다시 연결하세요. 매매 주문 기능은 없습니다.')
        return
    if st.button('잔고 새로고침·종목 분석', type='primary'):
        try:
            with st.spinner('보유종목과 잔고를 불러옵니다…'):
                snapshot = st.session_state.kis_client.balance()
            st.session_state.account_snapshot = snapshot
            st.session_state.account_results = {}
        except BrokerError as error:
            st.error(str(error))
            snapshot = None
        if snapshot is not None:
            positions = snapshot['positions']
            progress = st.progress(0, text='종목별 공식 자료를 확인합니다.')
            provider = Official()
            for index, position in enumerate(positions):
                code = position['code']
                item = {'code': code, 'name': position['name']}
                try:
                    if not re.fullmatch(r'[0-9]{6}', code):
                        raise ValueError()
                    report = provider.automatic(code)
                    result = brief(report)
                    item.update(report=report, automatic_brief=result, analyzed_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat())
                except Exception:
                    item['error'] = '기업 분석 미완료 · 공식 자료/상품 유형 확인 필요'
                st.session_state.account_results[code] = item
                progress.progress((index + 1) / len(positions), text=f"{index + 1}/{len(positions)} 종목 확인")
            progress.empty()
            st.caption('계좌 조회를 마쳤습니다. 분석 완료 여부는 종목별로 표시합니다.')
    snapshot = st.session_state.get('account_snapshot')
    if not snapshot:
        st.info('계좌를 연결하면 보유종목이 자동으로 들어옵니다. 종목코드·수량·매입가를 직접 입력하지 않아도 됩니다.')
        return
    st.caption(('실전' if snapshot['mode'] == 'real' else '모의') + ' 계좌 · 조회 ' + snapshot['fetched'])
    cols = st.columns(4)
    cols[0].metric('국내주식 평가액', f"{snapshot['value']:,.0f}원")
    cols[1].metric('평가손익', f"{snapshot['pnl']:+,.0f}원")
    cols[2].metric('예수금', f"{snapshot['cash']:,.0f}원" if snapshot['cash'] is not None else '미수집')
    cols[3].metric('보유종목', f"{len(snapshot['positions'])}개")
    st.caption('비중은 조회된 국내주식 평가액 기준입니다. 예수금은 출금 가능 금액과 다를 수 있습니다.')
    if not snapshot['positions']:
        st.info('조회된 계좌에 보유수량이 있는 국내주식이 없습니다.')
        return
    results = st.session_state.get('account_results', {})
    rows = []
    for p in snapshot['positions']:
        item = results.get(p['code'], {})
        b = item.get('automatic_brief', {})
        rows.append({'종목': p['name'], '코드': p['code'], '수량': p['quantity'], '평균매입가': p['average_cost'],
                     '평가액': p['value'], '평가손익': p['pnl'], '비중 %': round(p['weight'], 1),
                     '성장': b.get('growth', '분석 미완료'), '가치': b.get('value', '평가 보류')})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    largest = max(snapshot['positions'], key=lambda p: p['weight'])
    st.write(f"가장 큰 보유 비중은 {largest['name']} {largest['weight']:.1f}%입니다. 이 종목의 변화가 계좌에 미치는 영향을 먼저 확인하세요.")
    selected = st.selectbox('자세히 볼 보유종목', snapshot['positions'], format_func=lambda p: p['name'] + ' · ' + p['code'])
    item = results.get(selected['code'], {})
    if item.get('error'):
        st.warning(item['error'])
    if item.get('save_error'):
        st.warning('분석 결과를 저장하지 못했습니다. 현재 접속에서는 확인할 수 있습니다.')
    if item.get('report'):
        r, b = item['report'], item['automatic_brief']
        st.write(b['summary'])
        st.caption('기업 자료 수집일 ' + r.get('fetched', '') + ' · 계좌 조회일과 다를 수 있습니다.')
        st.subheader('실적 추이 · 억원')
        st.dataframe(pd.DataFrame(r['years'])[['year', 'revenue', 'profit']].rename(columns={'year':'연도','revenue':'매출','profit':'영업이익'}), hide_index=True)
        with st.expander('주요 사업 · 공식 보고서 발췌'):
            st.write(r.get('business_excerpt') or '사업 원문 미수집')
        st.subheader('최근 공시')
        for notice in sorted(r.get('disclosures', []), key=lambda n:n['date'], reverse=True)[:6]:
            st.link_button(notice['date'] + ' · ' + notice['title'], notice['url'])
    with st.form('account_note'):
        note = st.text_area('투자일지 · 보유 이유와 다음 확인 조건')
        if st.form_submit_button('일지 저장'):
            if note.strip():
                st.session_state.setdefault('account_notes', []).append({
                    'code': selected['code'], 'note': note.strip(),
                    'at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()})
                st.success('현재 접속 세션에 일지를 저장했습니다. 연결 해제 전 별도로 보관하세요.')
