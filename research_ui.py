import hashlib
import json
from datetime import date

import pandas as pd
import streamlit as st

from ui_v2 import hero, card
from automatic import brief
from bi_view import theme, overview, detail, peers_chart
from chat_research import published, parse_bundle, trends, growth, request_text
from dashboard_ui import render_decision_dashboard


def _dashboard_research(state):
    """Merge published research with the existing saved official-analysis records."""
    research = published()
    for item in state.get('chat_research', []):
        if item.get('code') not in research or item.get('as_of', '') >= research[item['code']].get('as_of', ''):
            research[item['code']] = item

    # Keep the existing automatic/DART analysis visible in the final cockpit too.
    # No missing market/flow values are fabricated; unavailable fields stay absent.
    for stock in state.get('stocks', []):
        report = stock.get('report') or {}
        code = stock.get('code', '')
        if not report or not code or code.startswith('pending-'):
            continue
        years = report.get('years') or []
        if len(years) < 2:
            continue
        last, prev = years[-1], years[-2]
        try:
            result = brief(report)
        except (KeyError, TypeError, ValueError):
            continue
        research.setdefault(code, {
            'code': code,
            'name': report.get('name') or stock.get('name') or code,
            'as_of': report.get('fetched') or report.get('price_date') or date.today().isoformat(),
            'summary': {'text': result.get('summary', ''), 'source': report.get('source', '')},
            'business': {'text': report.get('business_excerpt', ''), 'source': report.get('source', '')},
            'financial': {
                'period': str(last.get('year', '')) + '-12',
                'prior_period': str(prev.get('year', '')) + '-12',
                'basis': report.get('basis', '미확인'),
                'currency': 'KRW',
                'unit': '억원',
                'revenue': last.get('revenue'),
                'prior_revenue': prev.get('revenue'),
                'operating_profit': last.get('profit'),
                'prior_operating_profit': prev.get('profit'),
                'net_income': last.get('net_income'),
                'prior_net_income': prev.get('net_income'),
                'source': report.get('source', ''),
            },
            'valuation': (
                {**result['fair'], 'current_price': report.get('price'), 'price_date': report.get('price_date')}
                if result.get('fair') and report.get('price') is not None else {}
            ),
            'data_gaps': report.get('data_gaps', []),
            'sector': ', '.join(x.get('sector', '') for x in result.get('sectors', []) if x.get('sector')),
        })
    return research


def render_research(store, state, sample_mode):
    theme()
    research = _dashboard_research(state)
    render_decision_dashboard(research)
    hero('내 투자의 현재를 한눈에', '관심 있는 기업을 담고, 판단에 필요한 변화만 확인하세요.', 'PLANX · STOCK RESEARCH')
    if sample_mode:
        st.info('둘러보기 중입니다. 개인 목록을 저장하려면 먼저 대시보드 비밀번호를 설정하세요.')
    else:
        with st.expander('＋ 종목 추가', expanded=not state.get('stocks')):
            with st.form('research_manual'):
                name = st.text_input('종목명', placeholder='예: 삼성전자')
                with st.expander('종목코드를 알고 있다면 · 선택'):
                    code = st.text_input('종목코드', max_chars=6)
                if st.form_submit_button('내 목록에 추가'):
                    import re
                    if not name.strip() or (code and not re.fullmatch(r'[0-9]{6}', code)):
                        st.error('종목명과 숫자 6자리 코드를 확인하세요. 코드는 생략할 수 있습니다.')
                    else:
                        known = next((s for s in state.get('stocks', []) if s['name'].strip().casefold() == name.strip().casefold()), {})
                        identity = known.get('code') or code or 'pending-' + hashlib.sha256(name.strip().casefold().encode()).hexdigest()[:16]
                        try:
                            store.save_stock({'code':identity, 'name':name.strip(), 'kind':known.get('kind','관심')})
                            st.rerun()
                        except Exception: st.error('목록 저장에 실패했습니다. 저장 공간 설정을 확인하세요.')
    for r in state.get('chat_research', []):
        if r['code'] not in research or r['as_of'] >= research[r['code']]['as_of']: research[r['code']] = r
    stocks = {s['code']:s for s in state.get('stocks', [])}
    for p in st.session_state.get('account_snapshot', {}).get('positions', []):
        stocks[p['code']] = {**stocks.get(p['code'], {}), 'code':p['code'], 'name':p['name']}
    with st.expander('조사 요청 · 최신 내용으로 업데이트'):
        st.write('① 종목을 추가하거나 포트폴리오에서 계좌를 불러옵니다. ② 아래 요청문을 복사해 지금 대화창에 보냅니다. ③ 조사 결과가 반영되면 이 화면을 새로고침합니다.')
        st.code(request_text(list(stocks.values())), language=None)
        st.caption('요청문에는 종목명만 포함됩니다. 이 채팅에 요청문을 보내야 조사가 시작됩니다.')
        if st.button('반영된 조사 결과 다시 읽기'): st.rerun()
        if not sample_mode:
            with st.expander('조사 파일 가져오기 · 고급'):
                upload = st.file_uploader('별도로 받은 조사 JSON 가져오기 · 선택', type=['json'])
                if upload and st.button('조사 파일 검증·저장'):
                    try:
                        reports = parse_bundle(upload.getvalue())
                        def save(data):
                            merged = {r['code']:r for r in data.get('chat_research', [])}
                            for r in reports:
                                if r['code'] not in merged or r['as_of'] >= merged[r['code']]['as_of']: merged[r['code']] = r
                            data['chat_research'] = list(merged.values())
                        store.change(save)
                        st.rerun()
                    except (ValueError, KeyError, TypeError): st.error('조사 파일의 형식·출처·기간을 확인하세요. 기존 결과는 유지했습니다.')
                    except Exception: st.error('저장에 실패했습니다. 기존 결과는 유지했습니다.')
    if not stocks:
        with st.container(border=True):
            st.subheader('첫 관심종목을 담아보세요')
            st.write('위의 종목 추가를 열고 기업 이름 하나만 입력하면 시작할 수 있습니다.')
            st.caption('계좌가 있다면 왼쪽 계좌 연결에서 보유종목을 가져올 수도 있습니다.')
        return
    rows, details = [], {}
    for key, stock in stocks.items():
        r = research.get(key)
        if not r and key.startswith('pending-'):
            matches = [v for v in research.values() if v['name'].strip().casefold() == stock['name'].strip().casefold()]
            if len(matches) == 1: r = matches[0]
        r = r or {}
        f, v, flow = r.get('financial') or {}, r.get('valuation') or {}, r.get('flow') or {}
        trend, frame = trends(r.get('prices'), r.get('as_of', date.today().isoformat()))
        row = {'종목':stock['name'], '코드':r.get('code', key if not key.startswith('pending-') else '확인 필요'),
               '누적 매출 성장':growth(f['revenue'], f['prior_revenue']) if f else '조사 필요',
               '누적 영업이익 성장':growth(f['operating_profit'], f['prior_operating_profit']) if f else '조사 필요',
               '누적 순이익 성장':growth(f.get('net_income'), f.get('prior_net_income')) if f.get('net_income') is not None and f.get('prior_net_income') is not None else '미확인',
               '외국인 / 기관':f"{flow['foreign']:+,.0f} / {flow['institution']:+,.0f} {flow['unit']}" if flow else '조사 필요',
               '적정주가 참고':f"{v['base']:,.0f}원" if v else '조사 필요',
               '일봉':trend['daily'], '주봉':trend['weekly'], '조사일':r.get('as_of','미조사')}
        rows.append(row);details[key]=(stock, r, trend, frame)
    overview(details, st.session_state.get('account_snapshot'))
    with st.expander('전체 지표 비교'):
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown('### 기업 하나를 깊게 보기')
    selected = st.selectbox('자세히 볼 종목', list(details), format_func=lambda k:stocks[k]['name'], key='research_selected')
    stock, r, trend, frame = details[selected]
    if not r:
        st.info('이 종목의 채팅 조사 결과가 아직 없습니다. 위 요청문을 대화창에 보내면 조사 결과를 채울 수 있습니다.')
        if stock.get('report'):
            st.write('기존 공식 결산 분석: ' + brief(stock['report'])['summary'])
        return
    st.subheader(stock['name'])
    st.caption('조사일 ' + r['as_of'] + ' · 각 표의 자료 기간은 아래에 별도 표시합니다. 실시간 분석이 아닙니다.')
    detail(r)
    summary = r.get('summary')
    if summary:
        with st.container(border=True):
            st.markdown('**핵심 요약**')
            st.write(summary['text'])
    tabs = st.tabs(['어떤 기업인가요?', '실적은 어떤가요?', '주가 흐름', '가격과 확인 사항'])
    with tabs[0]:
        for label, key in [('주력사업과 기업 특징','business')]:
            st.subheader(label)
            entry = r.get(key)
            if entry:
                st.write(entry['text']); st.link_button('설명의 원문 근거', entry['source'], key='research_'+key)
            else: st.info('조사 필요')
    with tabs[1]:
        f = r.get('financial')
        if f:
            st.caption(f"누적 {f['period']} / 전년 {f['prior_period']} · {f['basis']} · {f['currency']} {f['unit']}")
            st.dataframe([{'항목':'매출','이번 누적':f['revenue'],'전년 누적':f['prior_revenue'],'변화':growth(f['revenue'],f['prior_revenue'])},
                          {'항목':'영업이익','이번 누적':f['operating_profit'],'전년 누적':f['prior_operating_profit'],'변화':growth(f['operating_profit'],f['prior_operating_profit'])},
                          {'항목':'순이익','이번 누적':f.get('net_income'),'전년 누적':f.get('prior_net_income'),'변화':growth(f.get('net_income'),f.get('prior_net_income')) if f.get('net_income') is not None and f.get('prior_net_income') is not None else None}], hide_index=True)
            st.link_button('실적 근거', f['source'])
        else: st.info('전년 같은 기간 누적 실적 조사 필요')
        st.subheader('투자전략 체크')
        # growth()는 화면 표시용 문자열을 반환하므로, 전략 조건에서는 원수치로 판단합니다.
        rg = ((f['revenue'] / f['prior_revenue']) - 1) * 100 if f and f.get('prior_revenue') not in (None, 0) else None
        pg = ((f['operating_profit'] / f['prior_operating_profit']) - 1) * 100 if f and f.get('prior_operating_profit') not in (None, 0) else None
        ng = ((f['net_income'] / f['prior_net_income']) - 1) * 100 if f and f.get('net_income') is not None and f.get('prior_net_income') not in (None, 0) else None
        if rg is not None and pg is not None:
            if rg > 0 and pg > 0: st.success('실적 모멘텀: 매출과 영업이익의 동반 증가가 다음 기간에도 이어지는지 확인')
            elif rg > 0: st.warning('이익률 점검: 매출 증가가 영업이익으로 이어지는지 원가·가격을 확인')
            else: st.warning('실적 둔화: 회복 여부와 둔화 원인을 다음 실적에서 확인')
        if ng is not None: st.info(f'순이익 변화 {ng:+.1f}% · 영업외손익과 일회성 효과를 함께 확인')
        peers = r.get('peers')
        st.subheader('경쟁사 영업이익 순위')
        if peers and peers['rows']:
            st.write(peers['selection_reason'])
            st.caption(f"비교 표본 내 순위 · {peers['period']} · {peers['basis']} · {peers['currency']} {peers['unit']}")
            peers_chart(peers)
            df = pd.DataFrame(peers['rows']);df['순위'] = df['operating_profit'].rank(method='min', ascending=False).astype(int)
            st.dataframe(df.sort_values('순위')[['순위','name','operating_profit','source']].rename(columns={'name':'기업','operating_profit':'영업이익','source':'출처'}), hide_index=True)
        else: st.info('같은 기간·회계기준의 경쟁사 실적 조사 필요')
    with tabs[2]:
        flow = r.get('flow')
        if flow:
            st.caption(flow['start'] + ' ~ ' + flow['end'] + ' · 순매수 ' + flow['unit'])
            a,b=st.columns(2);a.metric('외국인 순매수', f"{flow['foreign']:+,.0f}");b.metric('기관 순매수', f"{flow['institution']:+,.0f}")
            st.link_button('수급 근거', flow['source'])
        else: st.info('외국인·기관 수급 조사 필요')
        a,b=st.columns(2);a.metric('일봉 추세',trend['daily']);b.metric('완료 주봉 추세',trend['weekly'])
        st.caption('수정종가 기준: 일봉 20·60일, 주봉 10·20주 평균과 장기 평균 기울기를 함께 확인합니다. 진행 중인 주는 제외합니다.')
        if frame is not None:
            st.caption('가격 자료 마지막 거래일 ' + str(frame['date'].iloc[-1]))
            st.line_chart(frame.set_index('date')['close'])
            st.link_button('가격 자료 근거', r['prices']['source'])
    with tabs[3]:
        v = r.get('valuation')
        if v:
            a,b,c=st.columns(3)
            for col,key,label in [(a,'low','낮은 참고가'),(b,'base','기본 참고가'),(c,'high','높은 참고가')]: col.metric(label,f"{v[key]:,.0f}원")
            st.write(v['method']);st.caption(f"비교 가격 {v['current_price']:,.0f}원 · {v['price_date']} · 기본 참고가 대비 차이 {(v['base']/v['current_price']-1)*100:+.1f}%")
            st.link_button('평가 근거', v['source'])
        else: st.info('평가 가정과 가격 근거 조사 필요')
        for gap in r.get('data_gaps', []): st.write('확인 필요 · ' + str(gap))
    if not sample_mode:
        with st.expander('투자일지 남기기'):
            with st.form('research_note'):
                note=st.text_area('투자일지 · 다음 확인할 조건')
                if st.form_submit_button('기록 저장') and note.strip():
                    try:
                        from datetime import datetime, timezone
                        store.log('journal', {'code':selected,'at':datetime.now(timezone.utc).isoformat(),'kind':'note','note':note.strip()})
                        st.success('일지를 저장했습니다.')
                    except Exception: st.error('저장 실패. 입력 내용을 보관하세요.')
