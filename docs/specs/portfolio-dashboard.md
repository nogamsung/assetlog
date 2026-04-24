---
feature: portfolio-dashboard
title: Portfolio 집계 API + Dashboard UI
author: planner-agent
created_at: 2026-04-24
status: Draft
priority: P0
stack_scope: [backend, frontend]
parent_prd: docs/specs/asset-tracking.md
related_docs:
  - docs/specs/portfolio-dashboard/backend.md
  - docs/specs/portfolio-dashboard/frontend.md
  - docs/api/asset-tracking.yaml
---

# PRD — Portfolio 집계 API + Dashboard UI

> 상위 PRD (`docs/specs/asset-tracking.md`) 의 US-7 / US-8 / US-10 을 구현하는 **세부 슬라이스**.
> 가격 자동 갱신 스케줄러는 **별도 슬라이스**. 본 슬라이스는 **DB 에 이미 존재하는(혹은 이번에 추가하는) 캐시 필드를 읽어** 집계·표시만 수행한다.

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-24 |
| 상태 | draft |
| 스택 범위 | backend (FastAPI/Python) · frontend (Next.js) |
| 우선순위 | P0 |
| 브랜치 | `feature/portfolio-dashboard` (base: `origin/main`) |
| 작업 디렉토리 | `.worktrees/feature-portfolio-dashboard/` |

---

## 1. 배경

PR #1~#6 로 인증·AssetSymbol·UserAsset·Transaction(BUY) API 와 "자산 추가" UI 까지는 완료되었다. 그러나 **사용자가 자산을 등록한 뒤 얻을 수 있는 첫 가치** — "내 포트폴리오가 지금 얼마인가" — 가 전혀 노출되지 않는다. `/assets` 페이지는 단순 목록일 뿐, 평가액·손익·비중을 집계하지 않는다.

이 슬라이스는 상위 PRD 의 **US-7 (대시보드 요약)** · **US-8 (보유 자산 테이블)** · **US-10 (stale 경고 UI)** 을 구현해 **첫 번째 완결된 유저 가치 루프** (가입 → 자산 등록 → 평가액 확인) 를 닫는다. 가격 자동 갱신은 후속 슬라이스에서 다루되, 본 슬라이스의 UI 는 **`pending` / `stale` 상태를 표시할 준비** 를 갖춘다.

## 2. 목표 (Goals)

- **G-1** `GET /api/portfolio/summary`, `GET /api/portfolio/holdings` 두 엔드포인트가 **캐시된 가격 필드만** 읽어 집계 결과를 반환한다 (p95 < 500ms, 100 종목 기준).
- **G-2** `/dashboard` 페이지가 **요약 카드 3개** (총평가액 / 총손익 / 클래스별 도넛) + **보유 자산 테이블** 을 렌더한다.
- **G-3** 현재가가 없는 종목(`latest_price IS NULL`) 은 UI 에서 `pending` 배지로 구분되고 **집계 합계에서 제외** 된다.
- **G-4** `last_price_refreshed_at` 이 **3시간 이상 경과** 한 종목은 `stale` 배지로 구분되나 집계에는 **포함** 된다.
- **G-5** 신규 backend 코드는 pytest 라인 커버리지 ≥ 80%, frontend 는 Jest 라인 커버리지 ≥ 90% (pre-push 게이트).

## 3. 비목표 (Non-goals)

- **외부 시세 API 호출** — `/portfolio/*` 요청 경로에서 yfinance/pykrx/ccxt 호출 **금지** (상위 PRD 4.2). DB 캐시 읽기만.
- **가격 자동 갱신 스케줄러** — 별도 슬라이스 (`feature/price-refresh-scheduler`).
- **심볼 검색 어댑터 신규 구현** — 기존 `/api/symbols` 그대로 사용.
- **환율 통합 환산** — 통화별 분리 표기 유지 (v2 이전).
- **매도·실현 손익** — 상위 PRD v1.2 로 연기.
- **커스텀 자산 분류·태그** — 범위 외.

## 4. 대상 사용자

상위 PRD Persona A (멀티 자산 직장인) · Persona B (자산 혼합 운용자). 인증된 사용자만 대시보드 접근.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-D1 | 로그인한 사용자로서 `/dashboard` 진입 시 **총평가액 · 총손익 · 클래스별 비중** 을 3초 이내 확인할 수 있어야 한다 | 1) `GET /portfolio/summary` 응답에 `total_value_by_currency`, `total_cost_by_currency`, `pnl_by_currency`, `allocation`, `last_price_refreshed_at` 포함 / 2) 통화별 합계가 분리 표기 (KRW / USD) / 3) p95 < 500ms |
| US-D2 | 사용자로서 **보유 자산 테이블** 에서 종목별 평가액·손익·비중을 확인할 수 있어야 한다 | 1) 열: 심볼·이름·수량·평균단가·현재가·평가액·손익(절대+%)·비중 / 2) 기본 정렬: 평가액 내림차순 / 3) 사용자는 비중·손익 열을 클릭해 재정렬 가능 |
| US-D3 | 사용자로서 **현재가가 아직 채워지지 않은 종목** 이 있어도 대시보드가 정상 렌더되어야 한다 | 1) `latest_price IS NULL` → 테이블에 `pending` 배지 / 2) 해당 종목은 합계에서 **제외** 되고 주석 "현재가 대기 중 N 건" 표시 / 3) 비중 합은 나머지 종목 기준 100% |
| US-D4 | 사용자로서 **가격이 3시간 이상 갱신되지 않은 종목** 을 시각적으로 식별할 수 있어야 한다 | 1) `now - last_price_refreshed_at > 3h` → `stale` 배지 / 2) 집계에는 **포함** / 3) summary 응답의 전역 `last_price_refreshed_at` 은 **갱신된 종목 중 최신값** |
| US-D5 | 사용자로서 보유 자산이 0건이면 **빈 상태 안내** 와 "자산 추가" CTA 를 받아야 한다 | 1) `holdings=[]` → `/assets/new` 로 유도하는 EmptyState / 2) 요약 카드는 0 대신 대시(`—`) 표기 |
| US-D6 | 인증되지 않은 요청은 대시보드에 접근할 수 없어야 한다 | 1) `/api/portfolio/*` 에 쿠키/Bearer 없으면 401 / 2) 다른 사용자의 자산이 내 합계에 섞이지 않음 (user_id 스코프) / 3) 프론트는 미인증 시 `/login` 리다이렉트 |

## 6. 핵심 플로우

### 6.1 대시보드 조회 (happy path)
```
1. 로그인 상태에서 /dashboard 진입
2. Next.js (app) 레이아웃의 AuthGuard 통과
3. TanStack Query 로 병렬 호출:
   - GET /api/portfolio/summary
   - GET /api/portfolio/holdings
4. Backend:
   a. CurrentUser 의존성으로 user_id 추출
   b. PortfolioRepository 가 user_asset + asset_symbol + transaction(BUY) 을
      단일 쿼리(selectinload + subquery aggregate) 로 조회
   c. 캐시된 last_price / last_price_refreshed_at 를 asset_symbol 에서 읽음
   d. PortfolioService 가 통화별 그룹핑 + pending/stale 분류 + 비중 계산
5. 응답을 TanStack Query 가 staleTime 60s 로 캐시
6. 프론트는 카드 3개 + 테이블 렌더. 마지막 갱신 시각을 상대 표기 (예: "12분 전 업데이트")
```

### 6.2 예외 경로
- **현재가 null 종목 존재** → `summary.pending_count` 증가, 해당 종목은 `latest_value = null`. 프론트는 합계 주석 + 배지.
- **전 종목 `latest_price IS NULL`** → `total_value_by_currency = {}`. 프론트는 "현재가 데이터를 대기 중입니다" 안내 + 다음 갱신 예정 힌트.
- **401 (토큰 만료)** → 기존 axios 인터셉터가 `/login` 리다이렉트.
- **500 (DB 오류)** → 프론트 error.tsx + "다시 시도" 버튼.
- **빈 포트폴리오** → EmptyState → `/assets/new` CTA.

## 7. 데이터 모델 (요약 — 이 슬라이스 관점)

본 슬라이스는 **새 엔티티를 만들지 않는다.** 기존 테이블만 읽는다:

| 엔티티 | 이번 슬라이스에서의 쓰임 |
|--------|--------------------------|
| `users` | `current_user.id` 스코핑 |
| `asset_symbols` | `asset_type`, `symbol`, `name`, `exchange`, `currency`, **`last_price`** (Numeric(20,6), nullable), **`last_price_refreshed_at`** (DateTime(tz=True), nullable) 을 조회 |
| `user_assets` | `user_id` 로 필터, `asset_symbol_id` 로 조인 |
| `transactions` | `type=BUY` 집계 → `total_quantity`, `total_cost`, `avg_cost` 도출 |

### 7.1 이 슬라이스에서 추가하는 컬럼 (Alembic migration 1개)

`asset_symbols` 테이블에 두 컬럼을 **추가**한다. 값 채움은 별도 슬라이스(스케줄러) 책임. 본 슬라이스에서는 nullable 로 두고 읽기 로직만 구현.

```
asset_symbols
+ last_price                 NUMERIC(20, 6) NULL
+ last_price_refreshed_at    DATETIME(6) NULL   (timezone-aware)
+ INDEX ix_asset_symbols_last_refreshed (last_price_refreshed_at)
```

> **중요 — 범위 경계:** 컬럼만 추가하고 **값을 채우는 루틴은 구현하지 않는다.** 스케줄러 슬라이스 병합 전까지는 모든 행에서 값이 NULL 이며, UI 는 전체 `pending` 을 정상 렌더해야 한다.

### 7.2 파생 계산 (응답 시점, DB 저장 X)

```
for each user_asset ua:
    total_qty, total_cost = Σ(tx.quantity), Σ(tx.quantity * tx.price)   where tx.type=BUY
    avg_cost              = total_cost / total_qty                      (total_qty > 0)
    latest_price          = ua.asset_symbol.last_price                   (nullable)
    latest_value          = total_qty * latest_price                     (if latest_price not null)
    cost_basis            = total_cost
    pnl_abs               = latest_value - cost_basis                    (if latest_value not null)
    pnl_pct               = pnl_abs / cost_basis * 100                   (if cost_basis > 0)
    is_stale              = (now - last_price_refreshed_at) > 3h         (if last_price_refreshed_at not null)

summary:
    total_value_by_currency[currency]  += latest_value              (skip if null)
    total_cost_by_currency[currency]   += cost_basis
    allocation[asset_type]             = sum(latest_value for that type) / sum(all latest_value) * 100
    last_price_refreshed_at            = max(asset_symbol.last_price_refreshed_at)  across user's symbols
    pending_count                      = count(user_assets where latest_price IS NULL)
```

## 8. API 계약 (요약)

상세 스키마는 `docs/api/asset-tracking.yaml` (이미 초안 존재 — 본 슬라이스에서 `pending_count` 필드 및 holdings 스키마 확정).

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | `/api/portfolio/summary` | 통화별 총평가액·총손익·클래스별 비중 + pending_count | O |
| GET | `/api/portfolio/holdings` | 보유 자산별 현재가·손익·비중 행 배열 | O |

### 8.1 응답 예 — `GET /api/portfolio/summary`

```json
{
  "total_value_by_currency": {"KRW": 12500000.00, "USD": 8200.12},
  "total_cost_by_currency":  {"KRW": 11000000.00, "USD": 7500.00},
  "pnl_by_currency": {
    "KRW": {"abs": 1500000.00, "pct": 13.64},
    "USD": {"abs":     700.12, "pct":  9.34}
  },
  "allocation": [
    {"asset_type": "kr_stock", "pct": 42.1},
    {"asset_type": "us_stock", "pct": 48.3},
    {"asset_type": "crypto",   "pct":  9.6}
  ],
  "last_price_refreshed_at": "2026-04-24T09:00:00+09:00",
  "pending_count": 1,
  "stale_count": 0
}
```

### 8.2 응답 예 — `GET /api/portfolio/holdings`

```json
[
  {
    "user_asset_id": 12,
    "asset_symbol": {
      "id": 7, "asset_type": "us_stock", "symbol": "AAPL",
      "exchange": "NASDAQ", "name": "Apple Inc.", "currency": "USD"
    },
    "quantity": "10.0000000000",
    "avg_cost": "170.500000",
    "cost_basis": "1705.00",
    "latest_price": "175.200000",
    "latest_value": "1752.00",
    "pnl_abs": "47.00",
    "pnl_pct": 2.76,
    "weight_pct": 21.4,
    "last_price_refreshed_at": "2026-04-24T09:00:00+09:00",
    "is_stale": false,
    "is_pending": false
  }
]
```

**숫자 직렬화 규칙**: `Decimal` 필드는 **문자열** 로 직렬화 (`str(Decimal)`) — 부동소수점 오차 방지. `weight_pct`, `pnl_pct` 는 `float` (소수점 2자리). 프론트는 필요한 시점에 `Number(…)` 로 변환 후 `Intl.NumberFormat` 로 포맷.

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | `/portfolio/summary` · `/portfolio/holdings` p95 < 500ms @ 100 종목, 단일 MySQL + 단일 프로세스 |
| 쿼리 | **1 round trip** 원칙 — N+1 금지. `selectinload(asset_symbol)` + 서브쿼리 집계 |
| 보안 | 쿠키 JWT (httpOnly, Secure, SameSite=Strict) — 기존 미들웨어 재사용. `user_id` 스코핑 누락 시 계약 위반 |
| 정확성 | 금액 계산은 `Decimal` — float 혼용 금지. 응답 문자열 직렬화 |
| 타임존 | DB UTC 저장, 응답은 ISO-8601 (tz 포함), 프론트에서 `Asia/Seoul` 로 로컬 변환 |
| 접근성 | 테이블: `<table>` 시맨틱 + `<caption>` + `scope="col"`; 도넛: 텍스트 대안 제공 |
| 로깅 | 집계 실패 시 WARNING 로그 (user_id, 원인). PII·토큰 로그 금지 |
| 커버리지 | backend ≥ 80% (PortfolioService 분기 전부), frontend ≥ 90% |

## 10. 의존성 / 리스크

- **의존성** — 기존 `users`, `asset_symbols`, `user_assets`, `transactions` 테이블 (PR #1~#6). `CurrentUser` 의존성, httpOnly 쿠키 미들웨어.
- **의존성 (신규)** — `asset_symbols.last_price` + `last_price_refreshed_at` 컬럼 (본 슬라이스에서 마이그레이션 추가).
- **리스크** — R-A: 스케줄러 슬라이스 병합 전까지 **모든 행이 pending** 이라 시연 시 공허함. 완화: `pending` 배지를 명확히 UX 로 표현 + 샘플 시드 스크립트 제공 옵션 (개발용, 오픈 이슈).
- **리스크** — R-B: `Decimal → str` 직렬화 변경이 기존 `UserAssetResponse` 소비처(`/assets` 페이지) 에 영향. 완화: `/portfolio/holdings` 는 **신규 스키마**(`HoldingResponse`)로 분리 — 기존 `UserAssetResponse` 미변경.
- **리스크** — R-C: 비중 계산 분모에 `latest_value = null` 종목이 섞이면 비중 총합이 100% 미만이 됨. 완화: 분모는 `sum(not null only)` — PRD 7.2 참조.

## 11. 범위 외 (Out of Scope)

- 외부 시세 API 어댑터 (별도 슬라이스)
- apscheduler 기반 가격 갱신 job (별도 슬라이스)
- 환율 통합 환산 및 단일 통화 표기
- 매도 / 실현 손익 / 세금
- 자산 상세 페이지 (`/assets/{id}`) — 본 슬라이스에서는 대시보드 테이블의 "행 클릭" 만 `/assets` 로 유지
- Server Actions / RSC fetching — 기존 TanStack Query 패턴 유지

## 12. 오픈 이슈

- [ ] **개발용 시드 스크립트** — 스케줄러 병합 전 시연을 위해 `last_price` 에 임의 값을 넣는 관리용 스크립트(`scripts/seed_prices.py`)를 본 슬라이스에 포함할지 / 별도 PR 로 뺄지. 권장: **별도** (본 슬라이스 배포 리스크 최소화).
- [ ] **`stale_count` 응답 포함 여부** — UI 요구는 아니지만 관측성 목적으로 포함 권장. 본 PRD 는 포함으로 확정.
- [ ] **대시보드 정렬 상태 보존** — 페이지 재방문 시 사용자가 선택한 정렬을 URL 쿼리(`?sort=value&dir=desc`)로 보존할지 / 컴포넌트 로컬 state 로만 할지. MVP 는 **로컬 state**.
- [ ] **도넛 차트 라이브러리** — `recharts` 도입 vs shadcn/ui 기반 순수 SVG 구현. 기존 package.json 에 차트 라이브러리 없음. 권장: `recharts` 도입 (번들 영향 평가 필요).

---

## 13. 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | Alembic migration (asset_symbols 컬럼 2개 추가) · PortfolioRepository · PortfolioService · `/api/portfolio/{summary,holdings}` 라우터 · Pydantic 스키마 · pytest (repository/service/router) | [`./portfolio-dashboard/backend.md`](./portfolio-dashboard/backend.md) |
| frontend | `/dashboard` 페이지 · 요약 카드 3종 · 도넛 차트 · 보유 자산 테이블(정렬) · API 클라이언트 (`lib/api/portfolio.ts`) · 훅 (`usePortfolioSummary`, `usePortfolioHoldings`) · 타입 (`types/portfolio.ts`) · Jest 테스트 | [`./portfolio-dashboard/frontend.md`](./portfolio-dashboard/frontend.md) |

### 역할 간 계약 (Source of Truth)
`docs/api/asset-tracking.yaml` 의 `PortfolioSummaryResponse`, `HoldingResponse` (신규 추가), `AllocationEntry`, `PnlByCurrencyEntry`, `CurrencyAmountMap`. backend 가 응답 스키마를 바꾸려면 **YAML 먼저 수정** → frontend 반영.
