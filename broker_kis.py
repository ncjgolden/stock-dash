"""Personal domestic-stock balance reader. No order endpoints."""
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


class BrokerError(RuntimeError):
    pass


def amount(value):
    try:
        result = float(str(value).replace(',', ''))
        if not (-float('inf') < result < float('inf')):
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise BrokerError('잔고 응답의 숫자를 확인할 수 없습니다. 이전 자료를 유지합니다.') from None


class KIS:
    def __init__(self, *, key, secret, cano, product, mode='demo'):
        self.key = key.strip()
        self.secret = secret.strip()
        self.cano = cano.strip()
        self.product = product.strip()
        self.mode = mode.strip()
        if not self.key or not self.secret or not re.fullmatch(r'[0-9]{8}', self.cano) or not re.fullmatch(r'[0-9]{2}', self.product):
            raise BrokerError('한국투자증권 App Key·App Secret·계좌 앞 8자리·뒤 2자리를 설정하세요.')
        if self.mode not in ('real', 'demo'):
            raise BrokerError('KIS_ENV는 real 또는 demo로 입력하세요.')
        self.base = 'https://openapi.koreainvestment.com:9443' if self.mode == 'real' else 'https://openapivts.koreainvestment.com:29443'
        self.token = None
        self.expires = 0

    def request(self, method, path, **kwargs):
        try:
            response = requests.request(method, self.base + path, timeout=(5, 20), **kwargs)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            return response, data
        except (requests.RequestException, ValueError):
            raise BrokerError('증권사 연결에 실패했습니다. 환경·키·서비스 상태를 확인한 뒤 다시 조회하세요.') from None

    def authorize(self):
        if self.token and time.time() < self.expires:
            return
        _, data = self.request('POST', '/oauth2/tokenP', json={'grant_type': 'client_credentials', 'appkey': self.key, 'appsecret': self.secret})
        if not data.get('access_token'):
            raise BrokerError('증권사 인증에 실패했습니다. 실전·모의 키가 선택 환경과 같은지 확인하세요.')
        self.token = data['access_token']
        self.expires = time.time() + max(0, amount(data.get('expires_in', 0)) - 120)

    def balance(self):
        self.authorize()
        rows, seen = [], set()
        fk = nk = continuation = ''
        summary = {}
        for _ in range(100):
            response, data = self.request('GET', '/uapi/domestic-stock/v1/trading/inquire-balance',
                headers={'authorization': 'Bearer ' + self.token, 'appkey': self.key, 'appsecret': self.secret,
                         'tr_id': 'TTTC8434R' if self.mode == 'real' else 'VTTC8434R', 'custtype': 'P', 'tr_cont': continuation},
                params={'CANO': self.cano, 'ACNT_PRDT_CD': self.product, 'AFHR_FLPR_YN': 'N', 'OFL_YN': '',
                        'INQR_DVSN': '02', 'UNPR_DVSN': '01', 'FUND_STTL_ICLD_YN': 'N',
                        'FNCG_AMT_AUTO_RDPT_YN': 'N', 'PRCS_DVSN': '00', 'CTX_AREA_FK100': fk, 'CTX_AREA_NK100': nk})
            if str(data.get('rt_cd')) != '0':
                raise BrokerError('잔고 조회가 승인되지 않았습니다. 계좌·상품코드와 API 신청 상태를 확인하세요.')
            if not isinstance(data.get('output1'), list) or not isinstance(data.get('output2'), list):
                raise BrokerError('잔고 응답 형식이 달라 조회를 중단했습니다.')
            rows.extend(data['output1'])
            if data['output2'] and not summary:
                summary = data['output2'][0]
            if response.headers.get('tr_cont') not in ('F', 'M'):
                break
            fk, nk = data.get('ctx_area_fk100', '').strip(), data.get('ctx_area_nk100', '').strip()
            if not nk or (fk, nk) in seen:
                raise BrokerError('잔고의 다음 페이지를 확인하지 못했습니다. 일부 잔고를 전체로 표시하지 않습니다.')
            seen.add((fk, nk))
            continuation = 'N'
            time.sleep(0.6)
        else:
            raise BrokerError('잔고 페이지 한도를 초과했습니다. 조회 범위를 확인하세요.')
        positions = []
        codes = set()
        for row in rows:
            quantity = amount(row.get('hldg_qty'))
            if quantity <= 0:
                continue
            code = str(row.get('pdno', ''))
            if code in codes:
                raise BrokerError('종목별 잔고에 중복 응답이 있어 확인이 필요합니다.')
            codes.add(code)
            positions.append({'code': code, 'name': row.get('prdt_name', code), 'quantity': quantity,
                              'average_cost': amount(row.get('pchs_avg_pric')), 'price': amount(row.get('prpr')),
                              'value': amount(row.get('evlu_amt')), 'pnl': amount(row.get('evlu_pfls_amt'))})
        total = sum(p['value'] for p in positions)
        for position in positions:
            position['weight'] = position['value'] / total * 100 if total > 0 else 0
        return {'positions': positions, 'value': total, 'pnl': sum(p['pnl'] for p in positions),
                'cash': amount(summary['dnca_tot_amt']) if summary.get('dnca_tot_amt') not in (None, '') else None,
                'mode': self.mode, 'fetched': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}

