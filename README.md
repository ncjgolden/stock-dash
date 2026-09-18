# stock-dash · 내 관심종목 퀀트 보드

**수강생은 [단계별 실습 안내 · 여기서 시작](START-HERE.md)만 순서대로 따라오세요.** 01–07 기본 실습. Supabase 저장과 ChatGPT 달력 연결은 선택 소개이며, 직접 캘린더 API와 예약 설정은 수강생 실습에서 제외합니다. 아래 문서는 강사와 개발자를 위한 상세 참고입니다.

종목명·키워드 검색 → 종목코드 자동 확인 → 최근 결산·시세 자동 조회 → 성장·수익성·가치 진단 → 기업·섹터 확인 → 분석 이력 자동 저장.

한눈에 분석 상단에는 사업보고서의 주요 사업 발췌, 사업 키워드, 최근 90일 중 조회한 공시 6건과 수집일, 다음 점검 질문을 표시합니다. 실시간 뉴스나 경쟁사 정량 비교를 수집한 것으로 표시하지 않습니다.

DART 직접 통신이 실패하면 `public-data/{종목코드}.json` 공개 수집본을 확인합니다. 최초 수집 대상은 삼성전자·SK하이닉스입니다. GitHub Actions의 **Public DART data**에서 `DART_CRTFC_KEY` Secret을 이용해 수동 갱신합니다. 개인 보유수량과 일지는 수집본에 포함되지 않습니다. 이 경로는 현재 시세를 별도 조회하지만 과거 시가총액 배수가 없어 가치 참고 범위를 보류합니다. 자세한 입력 순서는 START-HERE의 강사용 항목에 있습니다.

개인별로 복사해서 사용하는 수업용 실행 프로젝트입니다. 한 배포와 한 DB는 한 사람만 사용합니다. 여러 수강생이 같은 DB를 공유하지 않습니다.

## 1. 먼저 화면 열기

Python 3.11 이상을 설치하고 이 폴더에서 실행합니다. Windows는 `start.bat`을 더블클릭할 수 있습니다.

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

처음에는 가상 종목 화면이 열립니다. 실제 종목이나 실제 수익률이 아닙니다.

`.env.example`을 `.env`로 복사하고 `APP_PASSWORD`에 나만의 긴 비밀번호를 입력한 뒤 재실행하세요. 비밀번호를 입력하면 종목 보관함이 열립니다. 비밀번호가 없으면 개인 데이터는 열리지 않습니다.

## 2. 공식 API 키 준비

| 어디서 | 순서 | 저장할 이름 |
|---|---|---|
| [공공데이터포털](https://www.data.go.kr/data/15094808/openapi.do) | 로그인 → 금융위원회 주식시세정보 → 활용신청 → 승인 확인 → 일반 인증키 복사 | `DATA_GO_KR_SERVICE_KEY` |
| [OpenDART](https://opendart.fss.or.kr/) | 로그인 → 인증키 신청 → 사용 목적 입력 → 인증키 확인 | `DART_CRTFC_KEY` |

키를 `.env`의 같은 이름 오른쪽에 붙여 넣습니다. 인증키를 AI 채팅·코드·커밋·스크린샷에 넣지 마세요. 공공데이터 키는 일반 인증키의 디코딩 값을 권장합니다.

시세는 `apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo`, 인증은 `serviceKey`입니다. 장중 실시간 시세가 아니라 기준일이 있는 일별 시세입니다. 최근 10일에서 조회 가능한 날짜를 찾습니다.

재무는 `opendart.fss.or.kr/api/fnlttSinglAcntAll.json`, 인증은 `crtfc_key`입니다. `corpCode.xml`로 종목코드를 고유번호로 바꾸고, 사업보고서 `reprt_code=11011`의 3개년 매출·영업이익을 읽습니다. 기존 수업의 `fnlttSinglAcnt.json`·`fnlttMultiAcnt.json`은 주요 계정 조회용이고, 이 구현은 전체 계정 API를 사용합니다. 세 해 모두 연결이 있으면 연결, 없으면 세 해 모두 별도로 맞춥니다. 해당 연도 보고서가 없다면 기준연도를 낮추세요.

[KRX OpenAPI](https://openapi.krx.co.kr/)는 이 버전에서 호출하지 않습니다. 연구·백테스트 확장은 별도 이용 승인과 최신 이용조건 확인 후 진행합니다.

## 3. 종목명만 넣고 자동 분석하기

1. 위 검색창에 삼성전자처럼 종목명을 넣거나 삼성처럼 이름 일부를 입력합니다. 대소문자·공백은 정리하고 종목코드 검색도 지원합니다.
2. 정확히 일치하는 기업 하나면 바로 분석합니다. 여러 기업이면 이름과 종목코드가 있는 목록에서 선택합니다. 오타 유사도나 산업 테마 검색은 아직 지원하지 않습니다.
3. 결산연도·주식수·과거 배수를 직접 입력할 필요가 없습니다. 최근 발표된 결산과 동일 연결/별도 3개년을 찾습니다.
4. 한눈에 분석에서 성장·수익성·가치 점수, 실적 추이, 적정주가 참고 범위를 확인합니다.
5. 기업·섹터에서 사업보고서 발췌와 사업 키워드별 확인 지표를 봅니다. 키워드 분류는 공식 업종 확정이나 실시간 섹터 강도 분석이 아닙니다.
6. 분석 결과는 자동 저장됩니다. 분석 기록·투자일지에서 나의 판단만 추가합니다. 저장 실패 시 화면 결과를 JSON으로 다운로드할 수 있습니다.

시세·DART 키만 있으면 규칙 기반 핵심 해설과 숫자 분석이 동작합니다. AI가 공시를 읽고 문장으로 해설하는 기능은 운영자가 Streamlit Secrets에 OPENAI_API_KEY와 사용 가능한 OPENAI_MODEL을 추가하면 자동 분석 시 함께 호출합니다. API 사용 요금·접근 권한은 별도 확인해야 합니다. ChatGPT 구독이나 Google Calendar 연결이 이 키를 대신하지 않습니다. 모델 설정이 없거나 호출에 실패해도 공식 데이터 분석은 유지됩니다. 개인 메모·비밀번호·DB 키는 모델에 보내지 않습니다.

```toml
OPENAI_API_KEY = "운영자의 OpenAI API 키"
OPENAI_MODEL = "해당 API 계정에서 사용 가능한 Responses 모델 ID"
```

분기·최신 잠정실적·컨센서스·실시간 업종 수급은 이 버전에 포함되지 않습니다. 기업의 설명과 미래 예상은 확인된 실적과 구분합니다.

## 4. 전산실과 집에서 이어 쓰기

GitHub는 코드 보관함이고 Secrets는 서버 실행용 비밀 보관함입니다. 종목과 일지는 Supabase DB에 저장합니다. GitHub Secrets를 앱 브라우저가 읽는 구조가 아닙니다.

1. 내 GitHub에 이 프로젝트를 `stock-dash`로 업로드합니다. 수강생은 원본이 공개된 뒤 **Fork**로 자기 계정에 복사할 수 있습니다. Fork에는 원본의 Secrets가 복사되지 않습니다.
2. [Supabase](https://supabase.com/)에서 개인 프로젝트를 만듭니다. SQL Editor를 열고 `schema.sql` 전체를 붙여 넣어 실행합니다.
3. 프로젝트 URL과 서버용 `service_role` 키를 확인합니다. `.env`의 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`에 넣습니다.
4. [Streamlit Community Cloud](https://share.streamlit.io/)에서 GitHub 저장소와 `app.py`를 선택합니다. 호스팅 서비스의 Secrets에는 아래 TOML을 설정합니다.

```toml
APP_PASSWORD = "나만의 긴 비밀번호"
SUPABASE_URL = "https://내프로젝트.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "서버용 키"
DATA_GO_KR_SERVICE_KEY = "일반 인증키"
DART_CRTFC_KEY = "DART 인증키"
```

이제 집에서는 같은 앱 주소와 비밀번호로 들어갑니다. 가능하면 호스팅 서비스의 비공개 접근 제어도 함께 사용하세요. 공용 PC에서는 로그아웃하고 내려받은 `.env`를 남기지 마세요. 로컬 저장만 쓰면 `data/state.json`에 저장되며 다른 PC와 동기화되지 않습니다.

## 5. Google Calendar 연결

1. Google Calendar 설정에서 **새 캘린더 만들기** → 이름을 `나의 투자 점검`으로 정합니다.
2. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **API 및 서비스 → 라이브러리 → Google Calendar API → 사용**을 누릅니다.
3. **IAM 및 관리자 → 서비스 계정**에서 계정을 만듭니다. 프로젝트 전체 관리자 역할은 주지 않습니다.
4. 서비스 계정의 **키 → 키 추가 → 새 키 만들기 → JSON**을 선택합니다. 이 파일은 비밀키입니다.
5. JSON의 `client_email` 주소를 복사합니다. Calendar에서 `나의 투자 점검`의 공유 설정에 이 주소를 추가하고 **일정 변경** 권한을 줍니다. 조직에서 서비스 계정 공유를 막으면 관리자 정책 확인이 필요합니다.
6. 같은 Calendar 설정의 **캘린더 통합 → 캘린더 ID**를 복사합니다. 계정 이메일이나 표시 이름과 다를 수 있습니다.
7. GitHub 저장소 **Settings → Secrets and variables → Actions → New repository secret**에 아래 6개를 저장합니다.

| Secret 이름 | 값 |
|---|---|
| `SUPABASE_URL` | 앱과 같은 DB URL |
| `SUPABASE_SERVICE_ROLE_KEY` | 앱과 같은 서버 DB 키 |
| `DATA_GO_KR_SERVICE_KEY` | 시세 API 키 |
| `DART_CRTFC_KEY` | DART 키 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON 파일 내용 전체, 중괄호 포함 |
| `GOOGLE_CALENDAR_ID` | 전용 캘린더 ID |

JSON 파일은 저장소에 업로드하지 않습니다. 알림은 캘린더 앱의 알림 권한이 켜져 있어야 보입니다. 초대 이메일이나 다른 사람에게 보내는 메시지는 만들지 않습니다.

## 6. 예약 실행은 미리보기부터

1. 앱에서 한 종목을 실제 데이터로 분석한 뒤 **자동 점검 → 이 종목을 주간 점검에 포함 → 저장**.
2. GitHub **Actions → Weekly investment review → Run workflow**에서 `write_calendar`를 끈 채 실행합니다. 최초 미리보기는 데이터 조회만 하며 DB·캘린더에 쓰지 않습니다. 로그의 `processed`가 1 이상이고 `failed`가 0인지 확인합니다.
3. 같은 화면에서 `write_calendar`를 켜고 다시 실행합니다. DB의 분석·일지와 달력 일정을 확인합니다.
4. 자동화를 켜려면 **Settings → Secrets and variables → Actions → Variables**에 `ENABLE_SCHEDULE=true`, `CALENDAR_WRITE=true`를 추가합니다. 기본값은 꺼짐입니다.

예약은 UTC 일요일 23:17, 한국 월요일 08:17입니다. 일정은 해당 주 월요일 20:00에 15분 동안 만들고 10분 전 알림을 설정합니다. 같은 종목·같은 주에 재실행하면 같은 일정을 갱신합니다. 주중 수동 실행도 해당 주 월요일 일정이므로 이미 지난 시간일 수 있습니다. GitHub 예약은 지연될 수 있고 공개 저장소는 장기 비활동 시 예약이 중지될 수 있습니다.

종목 조회 실패 시 이전 분석은 덮어쓰지 않습니다. 캘린더 기록까지 성공한 종목을 갱신합니다. 실적 변화와 이전/현재 가격은 DB 일지에 기록하고 캘린더에는 점검 안내만 남깁니다.

## 자동 점수와 참고 가격

현재 기본 화면은 자동 계산이 가능한 성장 30점·수익성 30점·가치 40점입니다. 성장 점수는 기존 매출/영업이익 성장 규칙 합계에 1.5를 곱하고, 수익성은 영업이익률/25×30을 0~30에 제한합니다. 가치는 20+(참고가/현재가−1)×100/2를 0~40에 제한합니다. 자료 부족 항목과 종합 점수는 보류합니다. 업종별 최적화나 수익 예측 성능이 검증된 점수가 아닙니다.

적정주가 참고값은 이전 두 결산 공시일 7일 뒤까지 조회되는 시가총액/해당 결산 영업이익 배수를 최근 결산 이익에 적용하고 현재 상장주식수로 나눕니다. 두 결과의 최소·중간·최대를 표시합니다. 미래 실적을 예측하거나 내재가치를 확정하는 방식이 아닙니다. 두 개의 흑자 기준점과 상장주식수가 있어야 하며 금융업은 보류합니다. 과거 낮은 이익, 차입금 변화, 우선주·비지배지분, 구조 변화와 사이클로 왜곡될 수 있습니다.

종목 검색과 재무는 DART, 종가·시가총액·주식수는 공공데이터포털에서 가져옵니다. 사업보고서는 document.xml 원문 발췌이며 전체 보고서 분석을 보장하지 않습니다. 수동 5축 평가 모듈 analysis.py는 기존 예약 코드 호환을 위해 남아 있으며 기본 화면의 자동 점수와 별개입니다.

## 파일과 확인 방법

`app.py` 화면 · `providers.py` 공식 데이터 · `analysis.py` 계산 · `storage.py` 저장 · `calendar_sync.py` 일정 · `weekly_review.py` 예약 실행 · `.github/workflows` 자동화.

```bash
python -m unittest discover -s tests -v
```

실제 키를 발급받은 뒤 실제 데이터 조회와 Calendar 권한을 최종 확인해야 합니다. 샘플 모드와 테스트는 실계정 연결 성공을 보장하지 않습니다.

공식 도움말: [DART 개발가이드](https://opendart.fss.or.kr/guide/main.do) · [Supabase REST API](https://supabase.com/docs/guides/api/rest) · [Google Calendar 일정 생성](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert) · [GitHub 예약 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## 7. 최종 투자분석 대시보드

메인 **오늘의 투자판단** 화면은 다음 순서로 구성됩니다.

**종목 현재 위치 → 핵심 투자지표 → 가격·기술적 분석 → 투자판단 체크 → 조건별 투자전략 → 실적·기업분석 → 시장·수급 레이더 → 종합 확인 항목 → 업종별 투자지도**

기존의 DART·공공데이터 기반 종목 분석과 채팅 조사 결과를 같은 화면의 대시보드 데이터로 통합합니다. 저장된 공식 결산 분석도 대시보드에서 이어서 확인할 수 있으며, 데이터가 없는 항목은 **데이터 연결 필요/미확인**으로 표시하고 임의의 주가·수급·시장·업종 수치를 만들지 않습니다.

현재 업종 투자지도는 화면 구조와 종목의 업종 포커스 표시까지 반영되어 있습니다. 실제 업종별 등락률·거래대금·수급은 `sector.performance` 등 기관 Capability가 연결된 뒤 표시하도록 분리되어 있습니다.

기존 종목 분석·공시·투자일지·계좌 연결·교육자료·데이터 연결 관리 기능은 유지합니다. 대시보드는 기존 기능을 대체하지 않고 그 위에 투자판단용 요약 화면을 추가하는 구조입니다.

최종 디자인 반영 커밋:
- `9b0e69415d56eb856681c7b662f1f3c6beecfdf6` · 대시보드 UI
- `c6eea65648f2148da0c3871bff8f0735a3139870` · 기존 저장 분석과 대시보드 통합

