---
feature: portfolio-performance
title: 포트폴리오 성과 측정 — TWR / MWR(IRR) 수익률 계산
author: planner-agent
created_at: 2026-05-07
status: draft
priority: P0
stack_scope: [backend]
parent_issue: "#61"
related_issues:
  - "#62 — 벤치마크 비교 (TWR 시계열 재사용)"
  - "#66 — Sharpe / MDD / 변동성 (일별 수익률 시계열 재사용)"
  - "#67 — 월별 수익률 히트맵 (구간별 TWR 재사용)"
related_docs:
  - docs/specs/portfolio-performance/backend.md
  - docs/specs/portfolio-dashboard.md
  - docs/specs/cash-holdings.md
---

# PRD — 포트폴리오 성과 측정 (TWR / MWR)

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-05-07 |
| 상태 | draft |
| 스택 범위 | backend (FastAPI/Python) — frontend 변경 없음 |
| 우선순위 | P0 |
| 브랜치 | `feature/portfolio-performance` (worktree: `.worktrees/feature-portfolio-performance/`) |

---

## 1. 배경

현재 대시보드(`/api/portfolio/summary`)는 **현재 평가액**, **누적 손익(미실현 + 실현)**, **클래스별 비중** 만 노출한다. 이 지표는 "지금 얼마인가"는 답하지만 **"내 투자 의사결정이 좋았는가"** 는 답하지 못한다.

문제 — 사용자가 1년 전 100만원을 한 번에 넣었을 때와 매월 분할 매수했을 때, 동일한 평가액·손익을 보여줘도 두 운용의 **수익률은 다르다**. 추가매수·부분매도가 있을 때 단순 손익률(`pnl/cost`)은 시점 효과를 왜곡한다.

표준 해법은 두 가지 — **TWR(Time-Weighted Return)** 과 **MWR(Money-Weighted Return = IRR)**. 본 슬라이스는 두 지표를 계산해 단일 엔드포인트로 제공하고, 후속 분석 이슈(#62 / #66 / #67)가 재사용할 수 있는 **공통 시계열 빌더** 를 함께 만든다.

## 2. 목표 (Goals)

- **G-1** `GET /api/portfolio/performance?period=&method=&currency=` 엔드포인트가 TWR · MWR 둘 다 계산해 반환한다.
- **G-2** 계산 로직(`services/performance.py`)은 **순수 함수 단위로 분리**되어 #62 벤치마크, #66 위험지표, #67 히트맵에서 import 만으로 재사용 가능해야 한다 (구체 함수 시그니처 — `7. 데이터 모델 / 모듈 구조` 참고).
- **G-3** 100 종목 / 5년치 거래 / 일 단위 가격 시계열 기준 **응답 p95 < 700ms** (단일 사용자, 캐시된 가격 데이터 가정).
- **G-4** TWR · MWR 모두 알려진 fixture(단일매수 / 추가매수 / 부분매도) 에 대해 **상대오차 < 0.01% (1bp)** 이내로 일치.
- **G-5** 신규 백엔드 코드 라인 커버리지 ≥ 90% (pre-push 게이트).

## 3. 비목표 (Non-goals)

- **벤치마크 비교** (S&P500, KOSPI 대비 초과수익) — #62 후속 이슈.
- **Sharpe / Sortino / MDD / 변동성** — #66 후속 이슈. 본 슬라이스는 **재사용 가능한 일별 수익률 시계열만** 제공.
- **월별 수익률 히트맵 UI** — #67 후속 이슈.
- **frontend 차트/UI** — 본 슬라이스는 backend-only. 프론트는 후속 이슈에서 통합.
- **자산별/태그별 분해 (per-symbol TWR)** — v2. 본 슬라이스는 **포트폴리오 전체** 단일 수익률만.
- **세후 수익률 / 배당 재투자 모델링** — DIVIDEND 트랜잭션 도입 이후.
- **새 ORM 모델 / Alembic migration** — 거래·가격·환율 데이터는 이미 충분.

## 4. 대상 사용자

상위 PRD Persona A (멀티 자산 직장인) · Persona B (자산 혼합 운용자). 인증된 사용자만 호출 가능.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-1 | 사용자로서 **TWR** 을 조회해 추가매수·매도 시점에 영향받지 않는 순수 운용 수익률을 알고 싶다 | 1) 1년 전 100만원 매수 → 현재 평가 120만원 일 때 TWR ≈ 0.20 (±1bp) <br> 2) 같은 자산을 6개월 전 추가매수 100만원 → TWR 은 첫 100만원 구간 + 두 번째 구간의 **기하평균** 으로 일치 <br> 3) 응답 시간 p95 < 700ms |
| US-2 | 사용자로서 **MWR(IRR)** 을 조회해 내가 넣은 돈의 시간가치를 반영한 실효 수익률을 알고 싶다 | 1) 단일 100만원 매수 → 1년 후 120만원 평가 일 때 MWR ≈ 0.20 (±1bp) <br> 2) 부분 매도 시 SELL 은 **음의 부호 현금흐름** 으로 처리 <br> 3) IRR 수렴 실패 시 (현금흐름 부호가 모두 같은 경우 등) 응답 필드는 `null`, HTTP 200 (에러 아님) |
| US-3 | 사용자로서 **기간** 을 선택해 (1W/1M/3M/6M/1Y/YTD/ALL) 단기·장기 성과를 비교하고 싶다 | 1) `period=1Y` → 정확히 365일 전부터의 구간만 집계 <br> 2) `period=YTD` → 해당 연도 1월 1일 00:00 UTC 부터 <br> 3) `period=ALL` → 가장 오래된 거래 시점부터 <br> 4) 시작일 이전 보유분(opening position)이 있으면 시작일의 평가액을 **첫 번째 시점 자본** 으로 잡는다 |
| US-4 | 사용자로서 **표시 통화** 를 선택해 다중 통화 포트폴리오의 통합 성과를 보고 싶다 | 1) `currency=KRW` → 모든 거래·평가액을 거래일 환율 기준으로 KRW 환산 후 계산 <br> 2) 환율 데이터 부족 시 응답 `twr`/`mwr` 은 `null`, `warnings` 배열에 사유 — HTTP 200 |
| US-5 | 사용자로서 보유 자산이 없거나 거래가 1건뿐일 때도 **명확한 응답** 을 받고 싶다 | 1) 거래 0건 → `twr=null, mwr=null, cashflows=[]`, HTTP 200 <br> 2) 거래 1건만 있고 보유중 → TWR / MWR 모두 (현재가 대비) 정상 계산 |

## 6. 핵심 플로우

```
1. 클라이언트 → GET /api/portfolio/performance?period=1Y&method=both&currency=KRW
2. 라우터 → CurrentUser 인증 통과
3. PerformanceService.get_performance(period, method, currency)
   3.1 거래 로드 (currency 필터 없음 — 모든 통화 대상, 환산은 메모리에서)
   3.2 가격 시계열 로드 (PortfolioHistoryRepository 재사용)
   3.3 환율 시계열 로드 (FxRateRepository — 거래일 기준)
   3.4 TWR — 현금흐름 시점 기준 구간 분할 → 각 구간 수익률 → 기하평균
   3.5 MWR — 현금흐름 + 종가치 → IRR (Newton-Raphson + 이분법 폴백)
4. 응답 직렬화 (PerformanceResponse, Decimal → str)
```

### 예외 경로
- 기간 내 거래·보유 모두 없음 → `twr=null, mwr=null, cashflows=[]`, HTTP 200, `warnings=["no_activity_in_period"]`
- 환율 데이터 부족 (currency 환산 시) → `twr=null, mwr=null`, HTTP 200, `warnings=["fx_rate_missing"]`
- IRR 수렴 실패 (현금흐름 부호가 단일) → `mwr=null` (twr 은 정상), `warnings=["mwr_unsolvable"]`
- period 가 enum 외 값 → 422 Validation Error
- 인증 실패 → 401

## 7. 데이터 모델 / 모듈 구조

새 ORM 모델 / Alembic migration **없음**. 모든 입력은 기존 모델에서 조회.

```
[Transaction] 1 ── N [UserAsset] 1 ── 1 [AssetSymbol]
   ↓                                       ↓
[type, qty, price, traded_at]      [currency, last_price, last_price_refreshed_at]

[PricePoint]                       [FxRate]
[asset_symbol_id, fetched_at,      [base_currency, quote_currency, rate,
 price]                             fetched_at]
```

**모듈 구조 (재사용성 핵심):**

```
app/services/performance.py
├── extract_cashflows(txs, currency, fx_rates) → list[Cashflow]
│       # SELL/BUY → 부호 있는 currency-환산 현금흐름
├── build_value_series(txs, prices, fx_rates, start, end, bucket) → list[ValuePoint]
│       # 기간 내 일별/시간별 평가액 시계열 — #66, #67 재사용
├── compute_twr(value_series, cashflows) → Decimal | None
│       # 현금흐름 시점에서 시계열을 절단 → 구간 수익률 → 기하평균
├── compute_mwr(cashflows, terminal_value, terminal_date) → Decimal | None
│       # IRR — Newton-Raphson + 이분법 폴백
└── PerformanceService.get_performance(...) → PerformanceResponse
```

`compute_twr` / `compute_mwr` / `extract_cashflows` 는 **순수 함수**로 외부 의존성 없음. 후속 이슈에서 `from app.services.performance import build_value_series` 로 직접 import.

## 8. API 계약 (요약)

```
GET /api/portfolio/performance
  ?period=1W|1M|3M|6M|1Y|YTD|ALL    (default: 1Y)
  &method=twr|mwr|both                 (default: both)
  &currency=KRW|USD|EUR                (default: KRW)
```

**응답 (200):**
```json
{
  "period": "1Y",
  "method": "both",
  "currency": "KRW",
  "start_date": "2025-05-07T00:00:00Z",
  "end_date":   "2026-05-07T00:00:00Z",
  "twr": "0.1873",
  "mwr": "0.1925",
  "annualized_twr": "0.1873",
  "annualized_mwr": "0.1925",
  "start_value": "10000000.00",
  "end_value":   "11500000.00",
  "cashflows": [
    {"date": "2025-05-07T00:00:00Z", "amount": "-10000000.00", "kind": "buy"},
    {"date": "2025-08-15T00:00:00Z", "amount":   "-5000000.00", "kind": "buy"},
    {"date": "2026-02-01T00:00:00Z", "amount":    "1200000.00", "kind": "sell"}
  ],
  "warnings": []
}
```

**응답 필드 정의:**
- `twr` / `mwr` — 기간 누적 수익률 (소수, e.g. 0.1873 = 18.73%). 계산 불가 시 `null`.
- `annualized_twr` / `annualized_mwr` — 연환산 수익률. period 가 1Y 이상이면 **CAGR**, 미만이면 단순 외삽 `(1+r)^(365/days) - 1`.
- `cashflows[].amount` — `currency` 기준 부호 있는 금액. **BUY = 음수**(자본 유입 = 현금 유출), **SELL = 양수**.
- `start_value` / `end_value` — 기간 시작·종료 시점의 포트폴리오 평가액 (currency 환산 후).
- `warnings` — 부분 실패 사유 코드 배열. 빈 배열이면 정상.

**계약 변경 시 — 본 PRD 8절 먼저 갱신 → backend.md 업데이트.**

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | p95 < 700ms (100 종목 / 5년치 / 일별 가격 / 단일 사용자) |
| 정확도 | TWR · MWR 모두 fixture 대비 상대오차 < 1bp |
| 결정성 | 동일 입력 → 동일 출력. IRR 수렴 시드는 고정. |
| 보안 | 인증된 사용자만. 사용자별 거래 격리 (multi-user 도입 시 user_id 스코프). |
| 로깅 | IRR 수렴 실패 / 환율 부족 / 거래 없음 → `logger.info` (warn 아님 — 정상 흐름) |
| 의존성 | **`numpy_financial` 또는 `numpy` 추가 금지** — 자체 IRR 구현 (Newton-Raphson + 이분법). 결정 근거: `10. 의존성 결정` 참고 |
| i18n | 응답 본문 i18n 없음 (코드만). UI 측 후속 이슈에서 처리. |

## 10. 의존성 / 리스크

### 의존성 결정 — IRR 구현 방식

| 옵션 | 장점 | 단점 | 결정 |
|------|------|------|------|
| `numpy_financial.irr` | 검증된 구현, 한 줄 | 신규 의존성 (+ transitive numpy), 패키지가 1.x 멈춤 (deprecated 경고) | **불채택** |
| `scipy.optimize.brentq` | 강건 (이분법 보장 수렴) | scipy 200MB+ — 가벼운 백엔드 원칙 위배 | **불채택** |
| **자체 Newton-Raphson + 이분법 폴백** | 신규 의존성 0, ~80줄, Decimal 친화 | 직접 검증 부담 → fixture 테스트로 보강 | **채택** |

근거 — 본 프로젝트는 의존성 최소화 원칙(backend `CLAUDE.md` 의 NEVER 와 정합). IRR 은 1차원 다항방정식 근찾기라 표준 알고리즘으로 충분. fixture 기반 테스트가 검증 책임을 진다.

### 의존성

- **기존 모델·리포지토리 그대로 사용**: `Transaction`, `PricePoint`, `AssetSymbol`, `FxRate`. 새 컬럼·인덱스 없음.
- **재사용**:
  - `app/repositories/portfolio_history.py::PortfolioHistoryRepository` — 거래 + 가격 시계열 로더 (이미 BUY/SELL 지원, 포인터 스캔 O(N)).
  - `app/services/fx_rate.py::FxRateService` — 통화 환산. 본 슬라이스는 **거래일 환율 (historical)** 이 필요 — 현재 `FxRateRepository.get_latest()` 만 있으면 부족하므로 **`get_at(base, quote, at: datetime)`** 추가 필요. (구현 위치 — backend.md 의 변경 파일 목록 참고)

### 리스크

- **R-1 — 거래일 환율 부재**: `FxRate` 는 시간별 스냅샷 — 5년 전 환율 데이터가 없을 수 있다. **완화**: `get_at` 은 `at` 시점 이전의 가장 최근 환율을 반환 (현재 환율로 백필 금지 — TWR 왜곡). 데이터 부족 시 `warnings=["fx_rate_missing"]` + null 응답.
- **R-2 — IRR 다중해**: 현금흐름 부호가 여러 번 바뀌면 IRR 해가 둘 이상일 수 있다. **완화**: Newton 시드는 항상 **0.10** 으로 고정 → 결정성 확보. 수렴 실패 시 이분법 `[-0.99, 10]` 으로 폴백. 둘 다 실패 시 `mwr=null`.
- **R-3 — TWR 구간 분할 시 동시점 거래**: 같은 timestamp 의 BUY + SELL 은 단일 현금흐름으로 합산 처리 (분할 후 0-구간 발생 방지).
- **R-4 — 후속 이슈 인터페이스 잠금**: `build_value_series` / `extract_cashflows` 의 시그니처가 #62/#66/#67 에서 import 되므로 **변경에 신중**. 변경 시 후속 이슈 대응 필요.

## 11. 범위 외 (Out of Scope)

- 자산별 / 태그별 / 통화별 분해 수익률
- 배당 / 이자 현금흐름 (DIVIDEND, INTEREST 트랜잭션 도입 이후)
- 세후 수익률
- 외부 벤치마크 (S&P500, KOSPI 등) 비교 — #62
- Risk-adjusted return (Sharpe, Sortino) — #66
- 월별 수익률 히트맵 — #67
- frontend UI / 차트 컴포넌트

## 12. 오픈 이슈

- [ ] **환율 환산 정책 — 거래일 vs 시점 가치평가일** : 본 PRD 는 **거래는 거래일 환율, 평가액(start/end value) 은 해당 시점 환율** 로 통일했다. 이는 표준 GIPS 와 일치하지만, 사용자가 "현재 환율로 모든 과거를 다시 그려줘" 같은 toggle 을 원할 수 있다. v2 결정 사항.
- [ ] **현금 (CashAccount) 잔고 포함 여부** : 현재 `cash-holdings` 슬라이스의 현금 잔고는 자산이지만 "수익을 발생시키지 않음". TWR / MWR 분모에 포함시킬지 — 본 슬라이스는 **자산 거래만 (Transaction 테이블)** 기준으로 계산. 후속 논의.
- [ ] **`bucket` 파라미터 노출 여부** : `period=1W` 일 때 시간별 시계열, `1Y` 일 때 일별 — 라우터가 자동 결정 (HistoryPeriod 와 동일 정책 재사용). 사용자 override 는 후속 이슈에서.

---

## 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | services/performance.py, schemas, router, FxRateRepository.get_at, tests | [`./portfolio-performance/backend.md`](./portfolio-performance/backend.md) |
| frontend | (본 슬라이스 변경 없음 — 후속 이슈 #62/#66/#67 와 함께 통합) | — |
