"""Validated, source-bearing research produced in chat; no LLM API client."""
import json
import math
import re
import calendar
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


def validate(report):
    if not isinstance(report, dict) or not re.fullmatch(r'[0-9]{6}', str(report.get('code', ''))):
        raise ValueError('종목코드는 숫자 6자리여야 합니다.')
    if not isinstance(report.get('name'), str) or not report['name'].strip():
        raise ValueError('기업명이 필요합니다.')
    date.fromisoformat(report['as_of'])
    if date.fromisoformat(report['as_of']) > date.today():
        raise ValueError('조사일은 미래 날짜일 수 없습니다.')
    def inspect(value, key=''):
        if key == 'source' and (not isinstance(value, str) or urlparse(value).scheme != 'https' or not urlparse(value).netloc):
            raise ValueError('출처는 HTTPS 원문 주소여야 합니다.')
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('유한한 숫자만 입력할 수 있습니다.')
        if isinstance(value, dict):
            for k, v in value.items(): inspect(v, k)
        elif isinstance(value, list):
            for v in value: inspect(v)
    inspect(report)
    for key in ('financial', 'flow', 'valuation', 'prices', 'peers'):
        if report.get(key) is not None and not isinstance(report[key], dict):
            raise ValueError(key + ' 항목 형식을 확인하세요.')
    if not isinstance(report.get('data_gaps', []), list) or any(not isinstance(x, str) for x in report.get('data_gaps', [])):
        raise ValueError('미확인 항목은 설명 목록으로 입력하세요.')
    def number(obj, key):
        if isinstance(obj.get(key), bool) or not isinstance(obj.get(key), (int, float)):
            raise ValueError(key + ' 숫자가 필요합니다.')
    for key in ('business', 'summary'):
        if key in report:
            if not isinstance(report[key], dict) or not isinstance(report[key].get('text'), str) or not report[key].get('source'):
                raise ValueError(key + ' 설명과 출처가 필요합니다.')
    financial = report.get('financial')
    if financial:
        for k in ('revenue', 'prior_revenue', 'operating_profit', 'prior_operating_profit'): number(financial, k)
        for k in ('period', 'prior_period', 'basis', 'unit', 'currency', 'source'):
            if not financial.get(k): raise ValueError('누적 실적의 기간·기준·단위·출처가 필요합니다.')
        # Both observations must represent the same number of months.
        p, q = financial['period'], financial['prior_period']
        if not re.fullmatch(r'\d{4}-(03|06|09|12)', p) or not re.fullmatch(r'\d{4}-(03|06|09|12)', q) or int(p[:4])-int(q[:4]) != 1 or p[5:] != q[5:]:
            raise ValueError('전년 같은 누적 기간만 비교합니다. 예: 2026-06 / 2025-06')
        year, month = map(int, p.split('-'))
        if date(year, month, calendar.monthrange(year, month)[1]) > date.fromisoformat(report['as_of']):
            raise ValueError('완료하지 않은 기간을 확정 실적으로 입력할 수 없습니다.')
    flow = report.get('flow')
    if flow:
        for k in ('foreign', 'institution'): number(flow, k)
        if flow.get('unit') not in ('주', '원', '억원') or not flow.get('source'): raise ValueError('수급 단위와 출처가 필요합니다.')
        if date.fromisoformat(flow['start']) > date.fromisoformat(flow['end']): raise ValueError('수급 기간을 확인하세요.')
        if date.fromisoformat(flow['end']) > date.fromisoformat(report['as_of']): raise ValueError('미래 수급은 입력할 수 없습니다.')
    valuation = report.get('valuation')
    if valuation:
        # 미확인 평가값은 명세상 null을 허용한다. 모든 값이 확인된 경우에만
        # 가격 범위/현재가 검증을 수행하고, 방법·출처는 항상 남긴다.
        if not valuation.get('method') or not valuation.get('source'):
            raise ValueError('평가 방법과 근거 출처가 필요합니다.')
        numeric = [valuation.get(k) for k in ('low', 'base', 'high', 'current_price')]
        if all(v is not None for v in numeric):
            for k in ('low', 'base', 'high', 'current_price'): number(valuation, k)
            if not 0 < valuation['low'] <= valuation['base'] <= valuation['high'] or valuation['current_price'] <= 0:
                raise ValueError('가격 범위와 현재가를 확인하세요.')
            if not valuation.get('price_date'):
                raise ValueError('현재가 기준일이 필요합니다.')
            date.fromisoformat(valuation['price_date'])
            if date.fromisoformat(valuation['price_date']) > date.fromisoformat(report['as_of']):
                raise ValueError('미래 가격을 현재가로 사용할 수 없습니다.')
        elif any(v is not None for v in numeric):
            raise ValueError('적정주가 값은 확인값을 넣거나 모두 null로 유지하세요.')
    prices = report.get('prices')
    if prices:
        if prices.get('adjusted') is not True or not prices.get('source'): raise ValueError('추세 계산에는 수정주가와 출처가 필요합니다.')
        if not isinstance(prices.get('rows'), list) or len(prices['rows']) > 2000: raise ValueError('가격 행 수를 확인하세요.')
        dates = set()
        for row in prices['rows']:
            if not isinstance(row, dict): raise ValueError('가격 행 형식을 확인하세요.')
            d = date.fromisoformat(row['date']); number(row, 'close')
            if d > date.fromisoformat(report['as_of']) or row['close'] <= 0 or row['date'] in dates: raise ValueError('중복 날짜·미래 가격·종가를 확인하세요.')
            dates.add(row['date'])
    peers = report.get('peers')
    if peers:
        for k in ('period', 'basis', 'currency', 'unit', 'selection_reason', 'source'):
            if not peers.get(k): raise ValueError('경쟁사 비교 기준과 선정 이유가 필요합니다.')
        seen = set()
        if not isinstance(peers.get('rows'), list): raise ValueError('경쟁사 목록이 필요합니다.')
        for row in peers['rows']:
            if not isinstance(row, dict): raise ValueError('경쟁사 행 형식을 확인하세요.')
            number(row, 'operating_profit')
            for k in ('period', 'basis', 'currency', 'unit'):
                if row.get(k) != peers[k]: raise ValueError('경쟁사별 기간·회계기준·통화·단위를 통일하세요.')
            if not row.get('source') or not row.get('name') or row['name'] in seen: raise ValueError('경쟁사 이름·출처·중복을 확인하세요.')
            seen.add(row['name'])
    return report


def parse_bundle(raw):
    if len(raw) > 3_000_000: raise ValueError('조사 파일은 3MB 이하로 나눠 주세요.')
    bundle = json.loads(raw)
    if not isinstance(bundle, dict) or bundle.get('schema_version') != 1 or not isinstance(bundle.get('reports'), list): raise ValueError('조사 파일 형식을 확인하세요.')
    reports = [validate(r) for r in bundle['reports']]
    if len({r['code'] for r in reports}) != len(reports): raise ValueError('중복 종목이 있습니다.')
    return reports


def published():
    reports = {}
    folder = Path(__file__).parent / 'research'
    for path in sorted(folder.glob('*.json')):
        try:
            for report in parse_bundle(path.read_bytes()):
                old = reports.get(report['code'])
                if old is None or report['as_of'] >= old['as_of']: reports[report['code']] = report
        except (ValueError, KeyError, TypeError):
            continue
    return reports


def growth(current, previous):
    if previous > 0: return f'{(current / previous - 1) * 100:+.1f}%'
    if previous <= 0 < current: return '흑자 전환'
    if previous < current <= 0: return '적자 축소'
    if current < 0: return '적자 지속·확대'
    return '비교 기준 부족'


def trends(prices, as_of):
    if not prices or prices.get('adjusted') is not True or not prices.get('rows'):
        return {'daily':'조사 필요', 'weekly':'조사 필요'}, None
    frame = pd.DataFrame(prices['rows']).sort_values('date')
    series = frame.set_index(pd.to_datetime(frame['date']))['close'].astype(float)
    def label(s, short, long):
        if len(s) < long + 1: return '기간 부족'
        fast, slow = s.rolling(short).mean(), s.rolling(long).mean()
        if s.iloc[-1] > fast.iloc[-1] > slow.iloc[-1] and slow.iloc[-1] > slow.iloc[-2]: return '상승 정렬'
        if s.iloc[-1] < fast.iloc[-1] < slow.iloc[-1] and slow.iloc[-1] < slow.iloc[-2]: return '하락 정렬'
        return '혼조·전환 확인'
    weekly = series.resample('W-FRI').last().dropna()
    weekly = weekly[weekly.index < pd.Timestamp(as_of)]
    return {'daily':label(series,20,60), 'weekly':label(weekly,10,20)}, frame


def request_text(stocks):
    names = '\n'.join(f"- {s['name']} ({s['code'] if not s['code'].startswith('pending-') else '코드 확인 필요'})" for s in stocks)
    return ('아래 종목들을 최신 공식 자료로 조사해서 stock-dash 통합 분석에 반영해줘.\n' + names +
            '\n실적 상승률, 전년 동기 누적 영업이익 성장률, 외국인·기관 수급(기간·단위), 적정주가(방법·가정), 수정주가 기준 일봉·완료 주봉 추세, 경쟁사 영업이익 순위, 종목 특징·주력 매출 사업을 작성해줘.\n'
            'research/의 공개 기업 조사 파일을 갱신하고 CHAT-RESEARCH.md 형식을 따라줘. 개인정보·계좌·수량은 넣지 말고 모든 항목에 기준일과 원문 출처를 남겨줘. 미확인 항목은 null로 두고 data_gaps에 이유를 적어줘. 경쟁사 비교는 같은 기간·통화·단위·회계기준으로 맞춰줘.')
