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


## 4단계: 검증 통과 시 다음 작업 자동 실행 (테스트 전용)
`.github/workflows/cj-staged-check.yml`은 작업 브랜치 변경 시 순차적으로 실행됩니다.
1. 수급 파서와 KRX 비교 보호장치 단위테스트
2. **1단계 성공 시에만** 검증된 자료의 간결 브리핑 형식 테스트
3. **2단계 성공 시에만** 3계좌 위험관리 및 실패 차단 통합테스트

테스트의 공식 KRX 자료와 3계좌 데이터는 **모두 합성 데이터**입니다.
테스트가 통과해도 실제 공식 자료 대조, 현재 계좌 연결,
ChatGPT 예약 알림 연결, 실거래 가능성을 검증한 것은 아닙니다.

현실 데이터가 없는 경우 `cj_pipeline_gate.py`는 **BLOCKED**를 반환합니다.
로컬에서만 다음을 수행할 수 있습니다:
```bash
python cj_pipeline_gate.py --comparison-json /private/flow_checked.json \
  --private-accounts-json /private/cj_accounts.json --target 005930
```
- 공식 CSV의 실제 출처/내보내기와 자릿수·시장·거래일 정합성을 확인한 후
  비교 JSON을 생성해야 합니다. 경로 문자열만으로 공식 원천 인증을 보장하지 않습니다.
- 3계좌 계정 번호·API 키·거래내역·잔고 파일은 절대 공개 저장소/Actions에 업로드하지 않습니다.
- 현행 GitHub 자동 검증은 안전한 **코드 테스트**에만 적용됩니다. 알림 자동
  발송·메인 브랜치 병합·카카오 설정·매매 실행은 포함하지 않습니다.
- 최종 사용 전 실제 KRX 원천 및 3계좌 최신 잔고가 필요합니다.


## 5단계: 공개 시장가격 중기 추세 연구 (별도 검증·미연동)
`cj_market_trends.py`는 **FinanceDataReader** (한국) 및 **yfinance**
(미국)를 선택적으로 이용하여 일간 **미조정 종가**의
5·20·60거래관측치 수익률과 20·60개 관측치 이동평균을 산출합니다.
한국: KOSPI·KOSDAQ·삼성전자·SK하이닉스;
미국: S&P500·NASDAQ·NVDA·GOOGL·ANET.
코스피/코스닥 `KS11`/`KQ11`은 FinanceDataReader README에서 확인한 코드입니다.
미국 가격은 yfinance `auto_adjust=False` 설정을 명시해,
배당·분할 조정 가격과 단순 종가 비교가 섞이지 않게 했습니다.
종목의 분할·배당 발생 시 장기 수익률은 별도 검증해야 합니다.

```bash
python -m pip install -r requirements-brief.txt
python cj_market_trends.py --market KR --asof YYYY-MM-DD
python cj_market_trends.py --market US --asof YYYY-MM-DD
python -m unittest discover -s tests -p 'test_cj_market_trends.py' -v
```

모든 수치는 연구용이며 **공식 거래소 인증 완료 상태가 아닙니다**.
수익률은 거래 관측치 기준이며 통상적인 *달력 5·20·60일*과 다릅니다.
최종 관측 날짜와 한국시간 수집 날짜를 기록합니다. 휴장, 게시 지연,
자료 누락으로 정확한 거래일 캘린더와 불일치할 수 있으므로
정식 보고 전 거래소 거래일과 교차확인하십시오.
한국 **당일 오후 18시 전** 조회된 가격은 확정 종가로 채택하지 않으며,
미국 종가의 **한국 날짜와 동일한 거래일** 역시 독립 검증 없이
확정됐다고 간주하지 않습니다.
미국/한국 자료는 별개 장 종료시각을 기준으로 해석합니다.

현재 **정기 ChatGPT 브리핑과 미연동**이며, GitHub 코드나 패키지를
추가했다는 사실 자체를 최신 시세 수집 성공으로 표시하지 않습니다.
공개 라이브러리 연결실패·누락·오류 시 `UNKNOWN`을 반환합니다.


## 6단계: 공개 데이터 실제 연결 점검 (2026-11-11 시작)
- `cj_live_smoke.py`: 삼성전자 외국인/기관 수급(PyKrx), 삼성전자 가격
  (FinanceDataReader), S&P500 지수(yfinance)의 **연결 가능성만** 확인.
  공용 조회정보의 **상태·기준일·60개 관측치 확보 여부**를 기록하며
  가격/순매수 실측 숫자는 출력하지 않음.
- `.github/workflows/cj-live-smoke.yml`: **작업 브랜치에 한정**한
  별도 테스트. 실제 시장 데이터 연결 시험일 뿐 투자 브리핑 운영 배포가 아님.
- 인터넷 연결, 데이터 제공자 차단, 사용 제한, 휴장일에는 `UNKNOWN`
  또는 부분자료가 정상적으로 반환될 수 있음. 실패 시 가짜 확정값을 채우지 않음.
- 기준일은 한국시간 실행 전날을 우선 조회하는 실험값으로 실제 거래소 영업일이
  아닐 수 있음. 별도의 공식 거래일 확인 필수.
- `official_krx_crosscheck=NOT_RUN` /
  `chatgpt_briefing_connection=NOT_CONFIGURED` 상태를 유지.
- 패키지 설치 및 외부 접속의 성공 여부는 실제 워크플로 로그에서
  별도 확인해야 하며, **코드 단위테스트 통과만으로 실연결 성공이라고
  판단하지 않는다**.
- 이 저장소의 public 로그/아티팩트에 증권 계좌번호·API 키·잔고·입출금
  기록을 넣지 말 것.

권장 적용 순서:
1. 위 외부 데이터 연결 점검이 통과하고 국내/미국 각각 거래일·거래단위를 확인
2. KRX 공식 수급 일별 자료를 실제 확보하여 별도 로컬에서 60거래일 대조
3. 같은 기준일의 공식 지수/종가와 오픈소스 가격 비교
4. **검증된 공개 자료**에 한해 ChatGPT 예약 실행 환경의 실제 조회 가능성을 확인
5. 연결되지 않으면 예약은 공식 자료 직접 검증 방식 그대로 유지하고
   코드가 연동됐다고 표현하지 않음

기존 오전 09:50/오후 18:30 ChatGPT 알림, main, 개인 계좌 정보, 매매는
이번 브랜치 작업의 변경 대상이 아님.
