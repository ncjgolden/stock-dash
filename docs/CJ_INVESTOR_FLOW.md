# CJ 시장 브리핑 개선안: 5·20·60거래일 수급 자료

> **별도 기능 초안 — 기존 ChatGPT 오전·오후 예약 및 stock-dash 메인 작동 방식 변경 없음.**

## 목적
외국인·기관·개인별 순매수 **금액(KRW)** 을 5/20/60 **거래일** 기준으로 집계합니다.
캘린더 5/20/60일이나 과거 고정 기간을 잘못 합산하지 않습니다. 기본 대상은
KOSPI, KOSDAQ, 삼성전자(005930), SK하이닉스(000660)입니다.

## 데이터와 안전성
- 출처: [PyKrx](https://github.com/sharebook-kr/pykrx), 공개 거래소 사이트 조회 도구.
  **KRX 공식 OpenAPI가 아닙니다.** 공식 자료와 교차검증하기 전 최종 확정치로 단정하지 않습니다.
- 사용 함수: `stock.get_market_trading_value_by_date(start, end, ticker, on="순매수")`.
  원본 README상 최종 투자자별 데이터는 오후 6시 이후 제공될 수 있습니다.
- 당일 오후 6시 KST 이전은 의도적으로 차단합니다. **16:30 마감 브리핑에
  이 자료를 당일 확정치로 넣지 않습니다.** 이전 확정 거래일 자료만 사용하거나
  장중 별도 공식 잠정 자료를 조회하고 반드시 '잠정'으로 표시해야 합니다.
- 날짜 누락·숫자 오류·60거래일 미달 시 해당 합계는 `null = UNKNOWN`입니다.
- 실제 계좌·주문·환율·기존 예약 알림을 읽거나 변경하지 않습니다.
- 사용자 계좌 거래내역과 잔고는 GitHub 공개 저장소에 올리지 마세요.

## 수동 실행
```bash
python -m pip install -r requirements-brief.txt
python cj_investor_flow.py --asof 2026-11-10
python -m unittest discover -s tests -p 'test_cj_investor_flow.py' -v
```
- 예시 날짜는 보고서를 만드는 **당일 날짜가 아니라**, 그 시점에 실제 확인된
  거래일로 교체해야 합니다. 소급 예시는 7일 경과 후 실행할 수 없습니다.
- pykrx 미설치, 외부 접속 실패, 장중 미완성 데이터는 브리핑에 숫자를
  채워 넣을 이유가 되지 않습니다. `UNKNOWN`을 유지합니다.

## 실제 브리핑 연결 (아직 미적용)
1. GitHub Actions/별도 호스트에서 공식 자료를 대조하고 날짜·출처를 기록
2. 검증된 JSON만 비공개 또는 접근 통제된 데이터 경로로 내보내기
3. ChatGPT 정기 알림이 그 자료에 접근할 수 있는지 별도 검증
4. 검증 후에만 알림 프롬프트/연동을 명시적으로 변경

이번 PR은 **데이터 엔진과 테스트만 추가**하며 실제 정기 알림의
데이터 소스가 변경되었다고 주장하지 않습니다. 기존 v4.2 기업 140점
점수·등급과 이 수급 합계를 합산하지 않습니다.


## 2단계: 공식 거래소 원자료 대조 (별도 검증)
`cj_official_reconcile.py`는 사용자 또는 담당자가 **KRX에서 직접 내보낸 CSV**와
PyKrx 자료를 날짜별, 투자자별, **원 단위**로 일치 확인합니다.
허용 출처 URL은 `https://data.krx.co.kr/`, `https://openapi.krx.co.kr/` 등입니다.

CSV 열 (UTF-8, 한 행 = 한 거래일·대상):
```csv
date,target,foreign_krw,institution_krw,individual_krw
```
이 열 이름은 검증 도구의 입력 형식이므로 **KRX 원본 CSV가 같은 열로
내려온다고 가정하면 안 됩니다**. 원본 파일의 컬럼명, 단위(원/천원/백만원),
투자자 분류, KRX 시장 포함 기준을 검증한 후 로컬에서 변환해야 합니다.
원본 URL은 입력자가 제공하는 메타데이터일 뿐, URL만으로 원본 진위를
암호학적으로 증명하지는 않습니다. 실제 화면의 데이터 출처와 비교하세요.

수동 실행 예시:
```bash
python cj_official_reconcile.py --asof YYYY-MM-DD --target 005930 \
  --official-csv /private/official_export_normalized.csv \
  --official-url https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd > /private/flow_checked.json
python cj_brief_packet.py --verified-json /private/flow_checked.json --target 005930
```
단, **60거래일의 동일한 일별 데이터**를 모두 대조해야
`MATCHED_60_SESSIONS`를 반환합니다. 누락되거나 일치하지 않는
구간은 `UNKNOWN` 또는 `MISMATCH`로 표기하며 브리핑 수치를 만들지 않습니다.
공식 데이터 대조는 작업 코드로 구현됐으나, 본 작업에서 실제 KRX 데이터 수집,
CSV 변환, 원본 검증, 현행 이용조건 확인을 완료했다는 뜻이 아닙니다.

## 3단계: 3계좌 포트폴리오 위험 계산 (로컬 전용)
`cj_portfolio_risk.py`는 세 계좌의 종목·현금·환율을 **동일한 기준시각**으로
직접 제공받아 종목 중복 합산 비중을 계산합니다. 특정 증권사를 임의
연결하지 않으며, 계좌 데이터가 없다면 결과도 계산하지 않습니다.

로컬 JSON 입력 형식 (아래는 임의의 예시이지 실제 보유내역이 아닙니다):
```json
{
  "observed_at": "2026-11-11T16:30:00+09:00",
  "fx": {"KRW": 1, "USD": 1400},
  "cash": [
    {"account": "ISA", "amount": 10, "currency": "KRW"},
    {"account": "GENERAL", "amount": 10, "currency": "KRW"},
    {"account": "OVERSEAS", "amount": 1, "currency": "USD"}
  ],
  "positions": [
    {"account": "ISA", "symbol": "005930", "quantity": 1, "price": 100, "currency": "KRW", "sector": "semiconductor"},
    {"account": "GENERAL", "symbol": "005930", "quantity": 2, "price": 100, "currency": "KRW", "sector": "semiconductor"},
    {"account": "OVERSEAS", "symbol": "NVDA", "quantity": 1, "price": 5, "currency": "USD", "sector": "semiconductor"}
  ],
  "valuation_history": [
    {"date": "2026-11-09", "nav_krw": 100, "external_flow_krw": 0},
    {"date": "2026-11-10", "nav_krw": 200, "external_flow_krw": 100}
  ]
}
```
예시의 숫자는 실 계좌와 관계없습니다. 데이터는 GitHub에 커밋하거나
공개 Actions 로그에 출력하지 말고 로컬에만 두십시오.
```bash
python cj_portfolio_risk.py --private-input /private/cj_accounts.json
```
- 원화 기준 비중에는 **현금·환율 포함**. GOOGL 등 동일 종목의 두 계좌
  수량은 티커 코드가 동일할 때 합산됩니다.
- 반도체 ETF의 기초자산 편입비중이 별도 검증되지 않으면 세부 반도체
  집중도는 완전한 look-through 분석이 아닙니다.
- 고점 대비 하락폭은 `(당일 NAV-기간 입출금)/전일 NAV` 방식의
  **입출금 조정 잠정 지수**에 근거합니다. 입출금 발생 시각이 반영된
  정밀 TWR 계산은 아닙니다. 최초 가치, 매일의 잔고, 외부 입출금 기록이
  빠졌다면 -10%/-20% 도달 여부를 확정하지 않습니다.
- -10%/-20%는 재검토 기준일 뿐 자동 매도 신호가 아닙니다.

## 실제 오전·오후 ChatGPT 예약과 연결 여부
**현재 미연동**: 본 PR의 파이썬 프로그램과 ChatGPT 예약 브리핑 사이에
자동 데이터 전송 경로가 없습니다. 정기 예약의 실행 환경이 GitHub Actions
로컬 파일이나 비공개 JSON을 읽을 수 있다는 근거도 없습니다.
사용자가 별도로 승인한 비공개 연동 경로 및 신뢰성 검증 전에는
예약 프롬프트·예약 시간·발송 설정을 바꾸지 않습니다.
