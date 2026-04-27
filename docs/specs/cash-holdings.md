---
feature: cash-holdings
title: 현금 보유 관리 (Cash Holdings)
author: planner-agent
created_at: 2026-04-27
status: Draft
priority: P1
stack_scope: [backend, frontend]
owners:
  backend: backend (FastAPI / Python)
  frontend: frontend (Next.js)
related_docs:
  - docs/specs/cash-holdings/backend.md
  - docs/specs/cash-holdings/frontend.md
  - docs/specs/asset-tracking.md
---

# PRD — 현금 보유 관리 (Cash Holdings)

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-27 |
| 상태 | Draft |
| 스택 범위 | backend (Python/FastAPI) · frontend (Next.js) |
| 우선순위 | P1 |
| 모드 | single-owner (users 테이블 없음) |

---

## 1. 배경

현재 AssetLog 는 주식·암호화폐 보유분만 트래킹한다 (`UserAsset` → `AssetSymbol`). 그러나 실제 포트폴리오의 **현금 잔액** (예: 증권계좌 예수금, 거래소 USDT 잔고, KRW 통장) 도 자산의 일부이며 자산 배분 의사결정에 영향을 준다. 사용자는 현재 대시보드 총 NAV 가 현금을 포함하지 않아 **실제 자산 규모 대비 과소 표시** 됨을 불편해한다.

이번 이터레이션에서는 **잔액 스냅샷** 만 도입한다. 입출금 트랜잭션 추적은 후속 이터레이션 (v2) 으로 미룬다.

## 2. 목표 (Goals)

- 사용자가 통화별로 현금 계좌 잔액을 등록·수정·삭제할 수 있다.
- 포트폴리오 요약 (`/api/portfolio/summary`) 의 통화별 총 평가액에 현금 잔액이 합산된다.
- 자산 분포 차트에 `cash` 카테고리가 추가되어 100% 합계가 유지된다.
- `/assets` 페이지 한 화면에서 보유 자산과 함께 현금이 보인다.
- 잔액 입력 → 대시보드 반영까지 **5초 이내** (서버 라운드트립 1회).

## 3. 비목표 (Non-goals)

- **입출금 거래 기록** (deposit/withdrawal Transaction) — 이번 스코프 X. v2.
- **이자/이자수익 계산** — X.
- **현금 → 종목 매수 시 자동 차감** — X. 사용자가 수동으로 잔액 갱신.
- **은행 API 연동 / 자동 동기화** — X.
- **다중 사용자 격리** — single-owner 모드 그대로 유지 (users 테이블 없음).
- **현금에 대한 가격 갱신 / FX 자동 변환 저장** — X. FX 변환은 기존 `FxRateService` 로 조회 시 on-the-fly.

## 4. 대상 사용자

**Persona A** (asset-tracking PRD 와 동일) — 멀티 자산 직장인. 증권계좌 예수금 + 거래소 USDT/USDC + 원화 통장 등 흩어진 현금을 한 화면에서 보고 싶다.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-1 | 사용자로서 라벨·통화·잔액으로 현금 계좌를 **등록** 할 수 있어야 한다 | 1) `POST /api/cash-accounts` → 201 / 2) currency 가 ISO 4217 3-letter 가 아니면 422 / 3) balance < 0 이면 422 / 4) 동일 (label, currency) 중복 허용 (서로 다른 계좌 가능) |
| US-2 | 사용자로서 등록한 현금 계좌의 **잔액·라벨을 수정** 할 수 있어야 한다 | 1) `PATCH /api/cash-accounts/{id}` 으로 balance 만, label 만, 또는 둘 다 수정 / 2) 미존재 id → 404 / 3) currency 는 수정 불가 (잘못 등록 시 삭제 후 재등록) |
| US-3 | 사용자로서 등록한 현금 계좌를 **삭제** 할 수 있어야 한다 | 1) `DELETE /api/cash-accounts/{id}` → 204 / 2) 미존재 id → 404 / 3) hard delete |
| US-4 | 사용자로서 **현금이 포함된 포트폴리오 요약** 을 확인할 수 있어야 한다 | 1) `total_value_by_currency` 의 통화별 합계에 현금 잔액 포함 / 2) `cash_total_by_currency` 별도 필드로 현금 단독 합계도 제공 / 3) `allocation` 에 `asset_type=cash` 항목이 추가되어 합계 100% 유지 |
| US-5 | 사용자로서 `/assets` 페이지 한 화면에서 **현금과 보유 자산을 함께** 볼 수 있어야 한다 | 1) `보유 자산` 섹션 위에 `현금` 섹션 카드 / 2) 각 카드에 라벨·통화·잔액·수정/삭제 버튼 / 3) 비어 있을 때 "현금 추가" CTA 표시 |
| US-6 | 사용자로서 흔한 통화는 **드롭다운**, 특수 통화는 **자유 입력** 으로 선택할 수 있어야 한다 | 1) 드롭다운: KRW, USD, JPY, EUR, GBP, CNY, HKD, SGD, AUD, CAD, CHF / 2) "기타" 선택 시 3-letter 텍스트 입력 / 3) 클라이언트·서버 양쪽에서 ISO 4217 3-letter 검증 |
| US-7 | 사용자로서 등록 직후 폼이 **다시 초기화되어 즉시 다음 계좌를 추가** 할 수 있어야 한다 | 1) 성공 토스트 / 2) 폼 reset / 3) 목록에 새 항목이 즉시 보임 (낙관적 업데이트 또는 invalidate) |

## 6. 핵심 플로우

### 6.1 현금 계좌 추가
```
1. /assets 진입 — 상단 "현금" 섹션 비어있음 → "현금 추가" 버튼 클릭
2. 다이얼로그: 라벨(예: "신한 KRW") · 통화 드롭다운(KRW 기본) · 잔액 입력
3. 제출 → POST /api/cash-accounts {label, currency, balance}
4. 201 응답 → useQueryClient.invalidateQueries(['cash-accounts'], ['portfolio-summary'])
5. 토스트 "현금 계좌가 추가되었습니다" → 다이얼로그 닫힘 → 목록에 새 카드
```

### 6.2 잔액 수정
```
1. 카드의 "수정" 버튼 → 인라인 폼 또는 다이얼로그
2. balance 또는 label 만 변경 가능. currency 는 readonly 표시
3. PATCH /api/cash-accounts/{id} {balance?: ..., label?: ...}
4. 200 응답 → invalidate 'cash-accounts' + 'portfolio-summary'
```

### 6.3 삭제
```
1. 카드의 "삭제" 버튼 → 확인 다이얼로그 ("이 현금 계좌를 삭제하시겠습니까?")
2. 확인 → DELETE /api/cash-accounts/{id}
3. 204 응답 → invalidate
```

### 6.4 포트폴리오 요약 통합
```
1. /dashboard 또는 /assets 진입 시 GET /api/portfolio/summary 호출
2. 서버에서:
   a. 기존 holdings 집계 → total_value_by_currency, allocation_value (asset_type 별)
   b. 신규: cash_total_by_currency = Σ balance per currency
   c. total_value_by_currency 에 cash 잔액 합산 (통화별)
   d. allocation: cash_total 을 grand_total 분모에 포함 + 별도 entry asset_type=cash
3. 응답에 cash_total_by_currency 추가 필드 포함 (현금만 따로 보고 싶을 때)
```

### 예외 경로
- ISO 4217 형식 위반 → 422 + 인라인 에러 "통화 코드는 3글자여야 합니다 (예: KRW)"
- balance 음수 → 422 + 인라인 에러
- 네트워크/서버 오류 → 토스트 + 재시도 옵션
- DELETE 404 (이미 삭제됨) → 토스트 "이미 삭제된 계좌입니다" + 목록 재조회

## 7. 데이터 모델

### 7.1 신규 엔티티 — `CashAccount`

| 필드 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 식별자 |
| `label` | VARCHAR(100) | NOT NULL | 사용자 정의 표시명 (예: "신한 KRW", "Robinhood USD") |
| `currency` | CHAR(3) | NOT NULL, ISO 4217 | 통화 코드 (대문자 3-letter) |
| `balance` | NUMERIC(20, 4) | NOT NULL, ≥ 0 | 현재 잔액. 소수점 4자리 (USDC/USDT 등 stablecoin 호환) |
| `created_at` | DATETIME(tz) | NOT NULL, default now | 생성 시각 (UTC 저장) |
| `updated_at` | DATETIME(tz) | NOT NULL, default now / onupdate now | 마지막 수정 시각 |

- **owner 필드 없음** — single-owner 모드 (`backend/CLAUDE.md`, `c8a4f1e927b3_drop_users_table_and_user_id` 마이그레이션 컨벤션 따름)
- **인덱스**: `currency` 단일 인덱스 (통화별 합계 집계 최적화)
- **유니크 제약 없음** — 동일 (label, currency) 중복 허용 (여러 KRW 통장 등 현실적 시나리오)

### 7.2 ER 관계
```
CashAccount  (독립 엔티티 — UserAsset / AssetSymbol 와 FK 관계 없음)
UserAsset 1 ── 1 AssetSymbol  (기존 그대로)
```

### 7.3 왜 별도 테이블인가
| 대안 | 문제 |
|------|------|
| `UserAsset.quantity = balance, latest_price = 1` 로 우겨넣기 | quantity 의미 왜곡, 가격 갱신 잡이 cash 까지 fetch 시도, asset_type enum 에 `cash` 추가 필요, P&L 계산 의미 없음 |
| `AssetSymbol(asset_type=cash, symbol=KRW)` 마스터 + UserAsset | trade 도메인 모델 (avg_cost, transaction) 이 cash 에 적용 안됨, 거래소 의미 없음 |
| **CashAccount 분리 (채택)** | trade vs balance 도메인 분리 명확. Portfolio 서비스에서 두 소스 합산만 하면 됨 |

### 7.4 마이그레이션 정책
- 신규 Alembic revision 만 추가. **기존 revision 수정 금지** (`backend/CLAUDE.md` NEVER 규칙)
- revision id 자동 생성, message: `create_cash_accounts_table`
- downgrade 는 `DROP TABLE cash_accounts`

## 8. API 계약

> 버전 prefix 없음 (기존 라우터 컨벤션과 동일 — `/api/...` 평면 prefix). 기존 `/api/user-assets` 패턴을 그대로 따름.

| 메서드 | 경로 | 설명 | 상태 코드 |
|--------|------|------|----------|
| GET | `/api/cash-accounts` | 모든 현금 계좌 목록 | 200 |
| POST | `/api/cash-accounts` | 신규 현금 계좌 생성 | 201, 422 |
| PATCH | `/api/cash-accounts/{id}` | 잔액/라벨 수정 | 200, 404, 422 |
| DELETE | `/api/cash-accounts/{id}` | 현금 계좌 삭제 | 204, 404 |

### 8.1 스키마

#### `CashAccountResponse` (모든 응답에서 사용)
```json
{
  "id": 1,
  "label": "신한 KRW",
  "currency": "KRW",
  "balance": "1500000.0000",
  "created_at": "2026-04-27T01:00:00+00:00",
  "updated_at": "2026-04-27T01:00:00+00:00"
}
```
- `balance` 는 **string 으로 직렬화** (Decimal 정밀도 유지 — 기존 portfolio 스키마와 일관성)
- `created_at`, `updated_at` 은 ISO-8601 UTC

#### `CashAccountCreate` (POST 요청 본문)
```json
{
  "label": "신한 KRW",
  "currency": "KRW",
  "balance": "1500000.00"
}
```
- `label`: 1~100자
- `currency`: 정확히 3자, 대문자 ASCII (`^[A-Z]{3}$`) — 입력값은 자동 uppercase 변환
- `balance`: Decimal as string, ≥ 0, 소수점 최대 4자리

#### `CashAccountUpdate` (PATCH 요청 본문 — 모든 필드 선택)
```json
{ "label": "신한 KRW (저축)", "balance": "1600000.00" }
```
- 빈 객체 (`{}`) → 422 "no fields to update"
- `currency` 필드는 **허용하지 않음** (스키마에 정의 X)

### 8.2 에러 응답 형식 (기존 `ErrorResponse` 재사용)
```json
{ "detail": "human-readable message" }
```

| 상황 | 코드 | detail 예시 |
|------|------|-------------|
| currency 형식 위반 | 422 | `"currency must be a 3-letter ISO 4217 code"` |
| balance 음수 | 422 | `"balance must be >= 0"` |
| label 길이 위반 | 422 | `"label must be 1..100 characters"` |
| PATCH 빈 객체 | 422 | `"at least one field must be provided"` |
| id 미존재 | 404 | `"CashAccount {id} not found"` |

### 8.3 포트폴리오 응답 변경

`GET /api/portfolio/summary` — `PortfolioSummaryResponse` 에 다음 필드를 **추가** (기존 필드는 변경 없음):

```jsonc
{
  // ... 기존 필드 ...
  "total_value_by_currency": { "KRW": "13000000.00", "USD": "8200.12" },
  // ↑ 변경 — 이제 holdings 평가액 + cash 잔액 합산 (통화별)

  "cash_total_by_currency": { "KRW": "1500000.00" },
  // ↑ 신규 — 현금만의 통화별 합계

  "allocation": [
    { "asset_type": "kr_stock", "pct": 38.0 },
    { "asset_type": "us_stock", "pct": 43.5 },
    { "asset_type": "crypto",   "pct":  8.6 },
    { "asset_type": "cash",     "pct":  9.9 }    // ← 신규 entry
  ]
}
```

- `pnl_by_currency`, `total_cost_by_currency`, `realized_pnl_by_currency` 는 **현금을 포함하지 않음** (현금에는 cost basis 개념 없음)
- `converted_total_value` (옵션 필드) — `convert_to` 파라미터 사용 시, 현금 잔액도 동일 FX 환산 후 합산
- `allocation` 분모 `grand_total` 은 `holdings 평가액 + cash 잔액` (단일 통화 기준이 아닌 자산 클래스 비중이므로, 환산 없이 합산하는 기존 로직 동작 검토 필요 — 자세한 것은 §12 오픈 이슈)

### 8.4 인증
- 기존 owner 인증 미들웨어 (`CurrentUser` Depends) 동일 적용. 모든 cash-accounts 엔드포인트는 인증 필수.

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | 모든 cash-accounts 엔드포인트 p95 < 100ms (단순 CRUD, 100 row 미만 가정) |
| 성능 | `/api/portfolio/summary` p95 변동 없음 — cash 합산은 단일 추가 쿼리 |
| 정밀도 | balance Decimal NUMERIC(20,4). 클라이언트 입력은 string → Pydantic Decimal 변환 |
| 타임존 | DB 저장 UTC, 응답 ISO-8601 |
| 보안 | 기존 owner 인증 통과 필수, FastAPI `Depends(CurrentUser)` |
| 검증 | currency 3-letter ISO + uppercase 강제, balance ≥ 0 (DB CHECK 또는 Pydantic field_validator) |
| 로깅 | CRUD 액션 INFO 레벨 (id 만, balance 값은 DEBUG) |
| 테스트 | backend ≥ 80%, frontend ≥ 90% 라인 커버리지 |
| i18n | UI 한국어 (`ko-KR`) |
| 접근성 | 통화 드롭다운 키보드 네비, 폼 라벨, 다이얼로그 focus trap |

## 10. 의존성 / 리스크

### 의존성
- **기존 `PortfolioService` / `PortfolioRepository`** — 통화별 합계 로직에 cash 추가 필요. 기존 메서드 시그니처 변경 없이 내부 합산만 보강.
- **기존 `FxRateService`** — `convert_to` 환산 시 cash 도 동일 경로로 변환 호출.
- **frontend `usePortfolioHoldings`, `usePortfolioSummary` (기존 훅)** — 응답 스키마 변경 (`cash_total_by_currency`, `allocation` 의 `cash` enum) 반영.
- **`AssetType` enum** — 기존: `kr_stock | us_stock | crypto`. 응답 `allocation.asset_type` 에 `cash` 가 추가됨. **백엔드 enum 자체는 확장하지 않고**, allocation 응답 스키마에서만 별도 처리 (또는 enum 확장 — §12 오픈 이슈).

### 리스크
| # | 리스크 | 완화 |
|---|--------|------|
| R-1 | `AssetType` enum 에 `cash` 추가 시 기존 `UserAsset.asset_type` 검증 실패 가능 | enum 확장 X. allocation 응답에서 `asset_type` 필드를 `str` 로 허용하거나 별도 union — backend 프롬프트에서 결정 |
| R-2 | 통화 자유 입력 → 오타 (예: `WON`, `KOR`) | 클라이언트 정규식 + 서버 정규식 이중 검증 |
| R-3 | 현금 합산이 holdings 평가액 통화와 다른 통화일 때 allocation pct 가 단순 합산되어 의미 왜곡 | `convert_to` 사용 시에만 의미있는 % — 미사용 시 통화별 그룹핑된 비중임을 UI 에 명시 |
| R-4 | 사용자가 같은 계좌를 두 번 등록 (중복) | 유니크 제약 없음 — UI 에서 등록 전 동일 (label, currency) 존재 시 경고 토스트 옵션 |

## 11. 범위 외 (Out of Scope)

- 입출금 거래 기록 / 잔액 변동 이력 (v2)
- 이자 / 배당금 / 캐시백 추적
- 다중 사용자 격리 (single-owner 모드 유지)
- 환율 자동 환산 후 단일 통화 NAV 표시 (별도 환율 PR 의 `convert_to` 그대로 활용)
- CSV 일괄 등록 (현금은 통상 5개 미만이므로 불필요 — 후속 검토)

## 12. 오픈 이슈

- [ ] **`AssetType` enum 에 `cash` 를 추가할지** 결정 — A안: enum 확장 (`AssetType.CASH`), 모든 곳 영향 / B안: allocation 스키마에서만 별도 union (`AssetType | Literal["cash"]`). **추천: B안** (영향 범위 최소화). backend.md 에서 B안으로 구현 지시.
- [ ] **현금이 0 인 통화** allocation 표기 — 표시 X (현재 grand_total 0 처리와 동일).
- [ ] **유니크 제약** — 동일 (label, currency) 허용 결정 유지하되, frontend 에서 중복 검출 시 경고 토스트 추가 여부.
- [ ] **stable coin (USDT, USDC) 처리** — 본 PRD 범위에서는 통화 코드 USDT/USDC 도 자유 입력으로 허용 (ISO 4217 엄격 검증과의 충돌). **결정: 검증 패턴 `^[A-Z]{3,4}$` 로 완화** (USDT 4자 허용). frontend 드롭다운에는 USDT, USDC 도 포함.
- [ ] **portfolio summary 의 `allocation` % 계산 분모** — `convert_to` 미사용 시 통화 혼합 합산이 의미 왜곡 가능 — UI 툴팁으로 "각 통화 원본 합산" 고지.
- [x] ~~**입력 통화 옵션**~~ — **해결**: 드롭다운 (KRW, USD, JPY, EUR, GBP, CNY, HKD, SGD, AUD, CAD, CHF, USDT, USDC) + "기타" 자유 입력.
- [x] ~~**`/cash` 별도 페이지 vs `/assets` 통합**~~ — **해결**: `/assets` 페이지에 "현금" 섹션 추가 (보유 자산 위). 한 화면 일관성 우선.

---

## 13. 역할별 책임

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | `cash_accounts` 테이블 Alembic · `CashAccount` 모델 · Schema · Repository · Service · Router · `PortfolioService` 통합 · pytest | [`./cash-holdings/backend.md`](./cash-holdings/backend.md) |
| frontend | `/assets` 페이지 현금 섹션 · `CashAccountList` · 추가/수정/삭제 폼 (RHF + Zod) · `useCashAccounts` 훅 · `lib/api/cash-account.ts` · 통화 드롭다운 · `usePortfolioSummary` 응답 타입 확장 · Jest + RTL | [`./cash-holdings/frontend.md`](./cash-holdings/frontend.md) |

### 역할 간 계약 (Source of Truth)
- 본 문서 §8 (API 계약) 이 단일 진실. 변경 시 PRD 먼저 → 양 역할 프롬프트 동기화.
- `cash_total_by_currency`, `allocation` 의 `cash` 항목은 **backend 가 추가** → frontend 가 타입·UI 반영.
- `CashAccountResponse.balance` 직렬화 형식 (string) 은 양쪽 동일.
