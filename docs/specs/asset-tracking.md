---
feature: asset-tracking
title: 자산 트래킹 서비스 MVP
author: planner-agent
created_at: 2026-04-23
status: Draft
priority: P0
stack_scope: [backend, frontend]
owners:
  backend: backend (FastAPI / Python)
  frontend: frontend (Next.js 16)
related_docs:
  - docs/specs/asset-tracking/backend.md
  - docs/specs/asset-tracking/frontend.md
  - docs/api/asset-tracking.yaml
---

# PRD — 자산 트래킹 서비스 (AssetLog MVP)

> 본 문서는 AssetLog 프로젝트의 **상위(Umbrella) PRD** 입니다. MVP 의 제품 범위를 정의하며, 이후 세부 기능(`자산 등록`, `가격 갱신`, `대시보드` 등)은 이 문서를 상위 컨텍스트로 하여 `/planner <sub>` 로 분할 작성됩니다.

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-23 |
| 작성 주체 | planner agent |
| 상태 | Draft |
| 우선순위 | P0 |
| 스택 범위 | backend (Python/FastAPI) · frontend (Next.js 16) |

---

## 1. 제품 개요 & 문제 정의

### 1.1 제품 한 줄 정의
> **AssetLog** — 국내 주식 · 해외 주식 · 암호화폐를 한 화면에서 추적하고 시간 단위로 평가액·수익률을 재계산해 주는 **개인용 포트폴리오 트래커**.

### 1.2 문제
개인 투자자는 자산 클래스별로 분산된 플랫폼(증권사 HTS, 거래소, 해외 브로커)에 로그인해야 전체 평가액을 확인할 수 있다. 이로 인해:

- 총 자산·자산 배분 현황을 **한 눈에 보기 어려움**
- 각 플랫폼의 수익률 계산 기준이 달라 **통합 손익 비교 곤란**
- 매수 기록을 수동으로 스프레드시트에 관리 → 시세 업데이트 수작업

### 1.3 기존 대안과의 차별점
| 대안 | 한계 |
|------|------|
| 증권사 앱 | 자사 계좌만, 해외·코인 미지원 |
| 스프레드시트 | 시세 자동 갱신 부재, 공식 수동 관리 |
| 유료 트래커 (e.g. Kubera) | 해외 중심, 한국 주식 커버리지 약함, 구독료 |

AssetLog 는 **3대 자산 클래스 통합 + 한국 주식 1급 지원 + 셀프호스팅 가능** 을 지향한다.

---

## 2. 핵심 페르소나

### Persona A — "멀티 자산 직장인 A" (주 타깃)
- 30대 초반, IT 직군, 월 수입 중 일정 비율을 분산 투자
- 보유: 미국 ETF(QQQ, VOO), 국내 대형주 2~3 종목, BTC/ETH 소액
- 니즈: **주 1~2회 퇴근 후 포트폴리오 평가액·비중 확인**
- 페인: 삼성증권 앱 + 업비트 + IBKR 를 번갈아 켜는 번거로움

### Persona B — "자산 클래스 혼합 운용자 B" (보조 타깃)
- 40대, 자영업, 현금흐름 관리 중요
- 보유: 국내 주식 다수, 해외 개별주, 주요 알트코인 5~10 종목
- 니즈: **자산 클래스별 비중이 목표 배분에서 얼마나 벗어났는지 파악**
- 페인: 종목 수가 많아 수기 집계 시간이 오래 걸림

---

## 3. 핵심 사용자 스토리

| # | 스토리 | 수락 기준 |
|---|--------|-----------|
| US-1 | **회원가입·로그인 사용자**로서 내 계정에 자산 목록이 **다른 사용자와 격리**되어 저장되어야 한다 | 1) 이메일·비밀번호로 가입·로그인 가능 / 2) JWT 인증 없이 `/api/**` 접근 시 401 / 3) 타 사용자의 자산이 내 대시보드에 노출되지 않음 |
| US-2 | **사용자**로서 **미국 주식**을 심볼로 검색해 보유 자산으로 등록할 수 있어야 한다 | 1) `AAPL` 입력 시 `Apple Inc.` 후보 반환 / 2) 수량·평균단가·매수일 입력 후 저장 / 3) 대시보드에 1분 이내 반영 |
| US-3 | **사용자**로서 **한국 주식**을 종목코드(6자리)로 검색해 등록할 수 있어야 한다 | 1) `005930` 입력 시 `삼성전자` 반환 / 2) KRW 통화로 저장 / 3) 가격 갱신 시 KRX 시세 조회 |
| US-4 | **사용자**로서 **암호화폐**를 심볼로 등록할 수 있어야 한다 | 1) `BTC/USDT` 등록 가능 / 2) 거래소(ex: binance) 선택 또는 기본값 사용 / 3) 소수점 8자리 수량 정상 저장 |
| US-5 | **사용자**로서 각 자산에 대해 **매수 기록(거래일·수량·단가)** 을 여러 건 추가할 수 있어야 한다 | 1) 같은 심볼에 대한 N 개 매수 저장 / 2) 평균단가가 자동 재계산 / 3) 거래 이력 조회 가능 |
| US-6 | **사용자**로서 **시간 단위로 자동 갱신된 현재가**로 평가액·수익률을 확인할 수 있어야 한다 | 1) 스케줄러가 1 시간마다 실행 / 2) 마지막 갱신 시각이 UI 에 표시 / 3) 갱신 실패 종목은 `stale` 플래그 |
| US-7 | **사용자**로서 대시보드에서 **총 평가액 · 총 손익 · 자산 클래스별 비중**을 한눈에 볼 수 있어야 한다 | 1) 총 평가액 = Σ(수량 × 현재가) / 2) 손익 = 평가액 - 총 매수금 (절대+%) / 3) 클래스별 비중 합이 100% |
| US-8 | **사용자**로서 보유 자산 목록에서 **종목별 평가액·손익·비중**을 정렬·조회할 수 있어야 한다 | 1) 열: 심볼·이름·수량·평균단가·현재가·평가액·손익·비중 / 2) 비중 내림차순 기본 정렬 |
| US-9 | **사용자**로서 등록한 자산을 **삭제**할 수 있어야 한다 | 1) 삭제 버튼 → 확인 다이얼로그 / 2) 삭제 시 관련 거래 기록도 함께 제거(또는 soft delete) |
| US-10 | **사용자**로서 가격이 **장시간 갱신되지 않으면 경고**를 받아야 한다 | 1) 마지막 갱신이 3 시간 초과 시 UI 에 "지연됨" 배지 / 2) 해당 종목은 손익 집계에서 제외하지 않되 시각적 구분 |

---

## 4. MVP 스코프

### 4.1 포함 / 제외 표

| 구분 | 항목 | 비고 |
|------|------|------|
| 포함 | 이메일+비밀번호 회원가입·로그인 (JWT access token) | 다중 사용자 격리 |
| 포함 | 심볼 검색 (해외/국내/코인) | yfinance / pykrx(FDR) / ccxt |
| 포함 | 자산 등록·삭제 (수동) | 수량·평균단가·매수일 |
| 포함 | 매수 거래 기록 (N 건) 및 평균단가 자동 재계산 | FIFO 아닌 가중평균 |
| 포함 | 1시간 주기 가격 자동 갱신 (apscheduler) | `Asia/Seoul` 기준 |
| 포함 | 대시보드 (총평가액 · 총손익 · 클래스별 비중) | 심플 위젯 |
| 포함 | 보유 자산 테이블 | 정렬, 종목별 평가액/손익 |
| 포함 | 한국어 UI | 기본 `ko-KR` |
| **제외** | 매도 기록 / 실현 손익 / 세금 계산 | v2 |
| **제외** | 가격 알림 · 임계치 알람 | v2 |
| **제외** | 자동 매매 / 리밸런싱 추천 | v3 |
| **제외** | 소셜·공유·포트폴리오 공개 | 후속 |
| **제외** | OAuth (Google/Apple) 로그인 | v2 |
| **제외** | 다중 통화 환산(KRW↔USD) 표시 통일 | 각 통화 **원본 표기** (대시보드는 통화별 합계) — v2 에서 통합 환산 |
| **제외** | 영어 UI (i18n) | v2 |

### 4.2 범위 경계 원칙
- **DB = Single Source of Truth**. 외부 데이터 소스의 일시 장애가 사용자의 보유 정보에 영향을 주지 않음.
- 외부 시세 소스는 **비동기 읽기**. API 요청 경로에서 외부 호출 금지 (캐시된 PricePoint 읽기만).

---

## 5. 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| **온보딩 전환율** — 회원가입 → 첫 자산 등록 → 대시보드 진입 | ≥ 90% | 이벤트 로그 (`signup`, `asset_created`, `dashboard_viewed`) |
| **가격 갱신 성공률** | ≥ 99% / 1 시간 윈도우 | `price_refresh_job` 로그 — 대상 종목 중 실패 비율 |
| **대시보드 API p95 응답시간** | < 500ms | `GET /api/v1/portfolio/summary` + `/holdings` 응답 분포 |
| **자산 등록 플로우 완료 시간** | 검색 → 저장까지 **< 30초 (중앙값)** | 프론트 이벤트 측정 |
| **재방문율 (WAU/MAU)** | ≥ 40% | 주간·월간 고유 로그인 사용자 수 |

---

## 6. 핵심 플로우

### 6.1 신규 사용자 온보딩
```
1. 랜딩(/) → "시작하기" 클릭
2. /signup — 이메일·비밀번호 입력 → 가입
3. 자동 로그인 → /dashboard
4. 빈 상태 안내: "첫 자산을 등록해보세요" → /assets/new
5. 심볼 검색 → 수량·단가·매수일 입력 → 저장
6. /dashboard 로 리다이렉트 — 등록 자산 즉시 표시 (현재가 없으면 pending 배지, 다음 갱신 사이클에서 채워짐)
```

### 6.2 자산 추가
```
1. /assets → "추가" 버튼 또는 /assets/new
2. 자산 클래스 선택 (국내주식 / 해외주식 / 암호화폐)
3. 심볼 입력 — debounce 300ms 후 /symbols?q=... 호출
4. 자동완성에서 선택 → 수량·단가·매수일 입력
5. 제출 → POST /user-assets (+ 최초 트랜잭션 생성)
6. 성공 토스트 → /assets 목록으로 이동
```

#### 예외 경로
- 심볼 미매칭 → 인라인 에러 "조회된 심볼이 없습니다"
- 중복 등록 시도 (같은 심볼 이미 보유) → 기존 자산에 거래 추가 제안
- 외부 심볼 DB 장애 → 직접 입력 fallback (검증은 가격 갱신 시)

### 6.3 가격 자동 갱신
```
1. apscheduler (AsyncIOScheduler) — 매시 정각(0분) trigger
2. refresh_prices job 기동
3. DB 에서 distinct (asset_type, symbol) 목록 조회
4. 자산 클래스별 adapter 라우팅
   - kr_stock  → pykrx / finance-datareader
   - us_stock  → yfinance
   - crypto    → ccxt (기본 거래소: binance, fallback: upbit)
5. 각 adapter 는 bulk 조회 시도 후 실패 시 개별 조회 fallback
6. PricePoint 레코드 삽입 (symbol, price, currency, fetched_at)
7. last_price / last_fetched_at 를 user_asset 또는 symbol 마스터에 캐시 갱신
8. 실패 종목은 warning 로그 + `stale_since` 기록
```

### 6.4 대시보드 조회
```
1. /dashboard 진입 (인증 필요, 미인증 시 /login 리다이렉트)
2. 병렬 호출:
   - GET /api/v1/portfolio/summary  → 총평가액·총손익·클래스별 비중
   - GET /api/v1/portfolio/holdings → 보유 자산 테이블
3. TanStack Query 가 캐싱 (staleTime: 60s)
4. 마지막 가격 갱신 시각 표시 ("10분 전 업데이트")
```

---

## 7. 데이터 모델 (개념적)

> 세부 스키마·인덱스·제약은 `/plan db` 로 분할. 여기서는 엔티티 · 핵심 필드 · 관계만.

### 7.1 엔티티
| 엔티티 | 설명 | 핵심 필드 |
|--------|------|-----------|
| **User** | 사용자 계정 | `id`, `email` (unique), `password_hash`, `created_at` |
| **AssetSymbol** | 심볼 마스터 (조회 캐시) | `id`, `asset_type` (kr_stock/us_stock/crypto), `symbol`, `name`, `exchange`, `currency`, `last_synced_at` |
| **UserAsset** | 사용자별 보유 자산 (심볼 단위 집계) | `id`, `user_id`, `asset_symbol_id`, `quantity`, `avg_cost`, `first_purchased_at`, `created_at`, `updated_at` |
| **Transaction** | 매수 기록 (MVP 는 BUY 만) | `id`, `user_asset_id`, `type` (BUY), `quantity`, `unit_price`, `executed_at`, `memo`, `created_at` |
| **PricePoint** | 시세 스냅샷 (시간대별 이력) | `id`, `asset_symbol_id`, `price`, `currency`, `fetched_at` |

### 7.2 관계
```
User 1 ──< N UserAsset >── 1 AssetSymbol
                │
                └──< N Transaction

AssetSymbol 1 ──< N PricePoint
```

### 7.3 파생 계산 (DB 저장 X — 조회 시 계산)
- `current_value = quantity × latest_price`
- `cost_basis   = quantity × avg_cost`
- `pnl_abs      = current_value − cost_basis`
- `pnl_pct      = pnl_abs / cost_basis × 100`
- `avg_cost` 재계산: 신규 BUY 시 `(기존 qty × 기존 avg_cost + new qty × new unit_price) / (기존 qty + new qty)`

### 7.4 기존 모델과의 관계
현재 `backend/app/models/{holding,price}.py` 가 **사용자 분리 없이** 스캐폴드되어 있음. 이 PRD 구현 시 **User / UserAsset / Transaction / PricePoint / AssetSymbol** 로 재설계 필요. 기존 `Holding` 은 `UserAsset` 으로 대체, `PriceSnapshot` 은 `PricePoint` 로 재명명 + `asset_symbol_id` FK 추가.

---

## 8. API 계약 (요약)

> 상세 스키마는 `docs/api/asset-tracking.yaml` 참고. 버전 prefix: `/api/v1`.

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| POST | `/auth/signup` | 이메일·비밀번호 가입 | X |
| POST | `/auth/login` | 로그인 → JWT access token 반환 | X |
| GET | `/auth/me` | 현재 사용자 정보 | O |
| GET | `/symbols?q=&type=` | 심볼 검색 (외부 어댑터 사용) | O |
| POST | `/symbols` | 수동 심볼 등록 (fallback) | O |
| GET | `/user-assets` | 내 보유 자산 목록 | O |
| POST | `/user-assets` | 자산 신규 등록 (첫 매수 포함) | O |
| DELETE | `/user-assets/{id}` | 자산 삭제 | O |
| GET | `/user-assets/{id}/transactions` | 거래 이력 조회 | O |
| POST | `/user-assets/{id}/transactions` | 매수 기록 추가 | O |
| GET | `/portfolio/summary` | 총평가액·총손익·클래스별 비중 | O |
| GET | `/portfolio/holdings` | 보유 자산 + 현재가 + 손익 | O |

**응답 예시 (/portfolio/summary)**
```json
{
  "total_value_by_currency": {"KRW": 12500000, "USD": 8200.12},
  "total_cost_by_currency":  {"KRW": 11000000, "USD": 7500.00},
  "pnl_by_currency": {
    "KRW": {"abs": 1500000, "pct": 13.64},
    "USD": {"abs":  700.12, "pct":  9.34}
  },
  "allocation": [
    {"asset_type": "kr_stock", "pct": 42.1},
    {"asset_type": "us_stock", "pct": 48.3},
    {"asset_type": "crypto",   "pct":  9.6}
  ],
  "last_price_refreshed_at": "2026-04-23T10:00:00+09:00"
}
```

---

## 9. 외부 의존성

| 라이브러리 | 역할 | 주의 |
|-----------|------|------|
| **yfinance** | 미국/해외 주식 시세 | Yahoo 비공식 — rate limit / HTML 구조 변경 리스크 |
| **pykrx** | 한국 주식 시세 · 종목 마스터 | KRX 스크래핑 기반 — 휴장일/장외시간 처리 필요 |
| **finance-datareader** | 한국 주식 백업 소스 · 지수 | pykrx 와 상호 보완 |
| **ccxt** | 암호화폐 시세 (다중 거래소) | 거래소별 symbol 표기 차이 — 정규화 필요 |
| **apscheduler** | 시간 단위 스케줄링 | `AsyncIOScheduler` + FastAPI lifespan 연동. 다중 프로세스 시 중복 실행 방지 필요 |
| **asyncmy** | MySQL async driver | SQLAlchemy 2.0 async 엔진에 연결 |
| **bcrypt / passlib** | 비밀번호 해싱 | MVP: bcrypt 12 rounds |
| **python-jose (or PyJWT)** | JWT 토큰 | HS256, exp 24h |

---

## 10. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | `/portfolio/summary`, `/portfolio/holdings` p95 < 500ms (100 종목 기준) |
| 성능 | `refresh_prices` job 1 사이클 < 5분 (500 심볼 기준) |
| 보안 | 비밀번호 bcrypt(cost=12), JWT HS256, access token 24h, secret `.env` 외 커밋 금지 |
| 보안 | 외부 시세 API 응답을 그대로 사용자에게 echo 금지 (whitelist 필드만) |
| 가용성 | 외부 소스 장애 시 기존 가격 유지 + `stale` 플래그 |
| 타임존 | DB 저장: **UTC**. 표시: `Asia/Seoul`. 프론트는 ISO-8601 수신 후 로컬 변환 |
| i18n | `ko-KR` 기본, 영어는 후속 |
| 접근성 | WCAG 2.1 AA, 키보드 내비게이션, 폼 라벨 |
| 로깅 | 외부 호출 실패 · 인증 실패 구조화 로그 (json). 패스워드·토큰 로깅 금지 |
| 테스트 커버리지 | backend ≥ 80%, frontend ≥ 90% (pre-push gate) |
| 배포 | `docker-compose` 로 local 기동 가능 (mysql + backend + frontend) |
| Node | frontend 빌드 시 Node ≥ 20.9.0 필요 (MEMORY 주의) |

---

## 11. 리스크 & 가정

### 리스크
| # | 리스크 | 영향 | 완화 |
|---|--------|------|------|
| R-1 | yfinance rate limit / 응답 구조 변경 | 해외 시세 중단 | adapter 추상화 + 실패 시 기존값 유지 + 모니터링 로그 |
| R-2 | pykrx KRX 사이트 변경 | 국내 시세 중단 | finance-datareader 를 secondary fallback |
| R-3 | ccxt 거래소별 symbol 불일치 (`BTC/USDT` vs `BTCUSDT` vs `KRW-BTC`) | 코인 시세 매칭 실패 | symbol 정규화 규칙 문서화 + AssetSymbol 마스터에 `exchange` 필드 |
| R-4 | 한국 휴장일 / 미국 휴장일 / 24h 코인 공존 | 갱신 실패·stale 오판 | asset_type 별 "거래 시간" 정책 테이블 |
| R-5 | 스케줄러 중복 실행 (다중 워커) | 중복 PricePoint | MVP: single-process 고정 (uvicorn --workers 1). v2: DB lock 기반 leader election |
| R-6 | 시세 지연 (free tier 15~20분) | 사용자 오해 | UI 에 "지연 시세" 고지 |
| R-7 | Node 18.20.8 환경에서 Next.js 16 빌드 실패 | 로컬 개발 블로킹 | README 에 nvm 업그레이드 안내 + `.nvmrc` 20.11+ 고정 |

### 가정
- 각 사용자 보유 종목 수 ≤ 100 (p95 기준)
- 총 사용자 수 MVP 기간 ≤ 500 (단일 MySQL 인스턴스로 충분)
- 장외 시간 시세는 마지막 거래일 종가로 대체 가능

---

## 12. 오픈 이슈

- [ ] **심볼 정규화 규칙** — 거래소별 심볼 표기 차이를 `AssetSymbol(asset_type, symbol, exchange)` 유니크 키로 해결할지 / 별도 `normalized_symbol` 컬럼을 둘지 결정
- [ ] **통화 처리** — MVP 에서 KRW/USD 혼합 시 대시보드에 "통화별 합계" 로 표기 (합계 환산 없음). v2 의 환율 소스 · 캐시 TTL 확정 필요
- [ ] **스케줄러 격리 방식** — MVP 는 FastAPI 프로세스 내 in-process. 사용자 증가 시 별도 worker(Celery/arq) 분리 시점 기준 정의 필요
- [x] ~~**JWT 저장 위치**~~ — **해결 (2026-04-23)**: `httpOnly` + `Secure` + `SameSite=Strict` **쿠키** 로 결정. backend 가 `/auth/login`·`/auth/signup` 응답에서 `Set-Cookie`, frontend 는 axios `withCredentials: true`. `localStorage` 금지 (XSS 방어). 세부 구현은 `memory/MEMORY.md` 2026-04-23 JWT 항목 참고.
- [ ] **DELETE /user-assets 시 Transaction 처리** — hard delete vs soft delete (`deleted_at`). 향후 실현 손익 조회를 위해 soft delete 권장 여부
- [ ] **휴장일 처리** — 한국 공휴일(법정) 캘린더 소스 필요. `holidays` 패키지 도입 검토
- [ ] **암호화폐 기본 거래소** — 한국 사용자 BTC 시세는 `upbit` (KRW) 이 자연스러움 vs global `binance` (USDT) 기본값. 사용자별 설정화 필요
- [ ] **초기 현재가 채우기** — 자산 최초 등록 직후 대기 없이 즉시 1회 가격 조회를 on-demand 로 수행할 것인지 (backend service 내부 trigger)

---

## 13. 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | MySQL 스키마 · Alembic · 인증 · REST API · 가격 어댑터 · 스케줄러 · 포트폴리오 집계 쿼리 · pytest | [`./asset-tracking/backend.md`](./asset-tracking/backend.md) |
| frontend | 인증 페이지 · 심볼 검색 UI · 자산 추가 플로우 · 대시보드 위젯 · 자산 목록 · API 클라이언트 · RTL 테스트 | [`./asset-tracking/frontend.md`](./asset-tracking/frontend.md) |

### 역할 간 계약 (Source of Truth)
역할 간 통신은 `docs/api/asset-tracking.yaml` (OpenAPI) 를 유일한 진실로 삼는다.
- backend 가 엔드포인트 스펙·응답 스키마를 변경하려면 **YAML 먼저 수정** → frontend 프롬프트에 반영 → 구현.
- frontend 가 필드 추가를 요청하려면 본 PRD 의 "API 계약" 섹션에 제안 → backend 합의 → YAML 수정.

---

## 14. 향후 이터레이션 로드맵

| 버전 | 기능 | 비고 |
|------|------|------|
| **v1.0 (MVP — 본 PRD)** | 인증 + 3 클래스 자산 등록 + 시간 단위 갱신 + 대시보드 | 본 문서 |
| v1.1 | 자산 삭제 soft delete · stale 시세 UI 개선 · 기본 휴장일 처리 | 버그 픽스 중심 |
| v1.2 | 매도 기록 · 실현 손익 집계 | 세금 계산은 아직 X |
| v1.3 | 가격 알림 (임계치 도달 이메일/웹 push) | 알림 인프라 도입 |
| v2.0 | 환율 통합 환산(KRW↔USD), i18n 영어 | 글로벌화 |
| v2.1 | OAuth (Google / Apple) | 신규 가입 편의 |
| v2.2 | 세금 계산 (양도소득세 · 금투세 대응) | 회계 파트너 검토 |
| v3.0 | 리밸런싱 추천, 시나리오 시뮬레이션 | ML 기반 |
| v3.x | 모바일(Flutter) 앱 | 현재 범위 외 |

---

## 참고 문서
- `CLAUDE.md` (루트) — 모노레포 규칙
- `backend/CLAUDE.md` — FastAPI 구현 규칙
- `frontend/CLAUDE.md` — Next.js 구현 규칙
- `memory/MEMORY.md` — 프로젝트 기록 (hourly price refresh, Node 버전 제약 등)
