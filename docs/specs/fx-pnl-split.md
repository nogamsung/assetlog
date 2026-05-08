# PRD — 환차손익 분리 표시 (fx-pnl-split)

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-05-07 |
| 상태 | draft (decision-locked) |
| 스택 범위 | backend (python) + frontend (nextjs) |
| 우선순위 | P0 |
| 관련 이슈 | GitHub #63 (범위 확장 — historical FX 인프라 포함) |
| 의존성 PR | #97 (`FxRateService.convert_at`) — **미머지 상태에서 본 PR 진행**. snapshot 조회는 본 PR 의 `FxRateRepository.get_rate_at` 직접 호출. #97 머지 후 별도 chore PR 에서 `FxRateService.convert_at` → `get_rate_at` 위임으로 통합. |

---

## 1. 배경

현재 USD 자산을 KRW 로 환산해 표시할 때, 평가손익(`pnl_abs`)은 다음 두 효과가 합쳐진 값이다:

1. **가격 변동 손익** — 현지통화 기준 (현재가 - 평균매수가) × 보유수량
2. **환차손익** — 매수 시점 환율과 현재 환율의 차이가 원금에 미친 영향

두 효과는 의사결정 관점에서 완전히 다르다. 예: AAPL 이 +5% 올랐지만 USD/KRW 가 -3% 하락했다면 KRW 환산 손익은 +2% 에 그친다 — 사용자는 "AAPL 이 +5% 올랐다" 와 "환율이 손익을 깎아먹었다" 를 분리해 인지해야 한다.

**핵심 인프라 부재**: 현 `fx_rates` 테이블은 `(base, quote)` 유니크의 single-row-per-pair 구조 — 가장 최신 환율 1건만 보관하고 **historical 시계열이 없다**. 즉 거래일 시점 환율을 재구성할 수단이 없으므로, 본 PR 은 환차/가격 분리 알고리즘만 추가하면 모든 외화 자산에서 `fx_warning` 을 반환할 수밖에 없다. 따라서 **본 PR 범위에 `fx_rate_snapshots` 시계열 테이블 신설을 포함**한다 (사용자 결정, §10.1).

다중 통화 (KRW / USD / EUR) 자산 비중이 늘면서 환차손익 분리 요구가 P0 으로 격상.

## 2. 목표 (Goals)

- `GET /api/portfolio/holdings` 와 `GET /api/portfolio/summary` 응답에 `price_pnl` 과 `fx_pnl` 필드 추가 (환산 모드 — `convert_to` 파라미터 사용 시).
- 수학적 항등 보장: `pnl_abs (converted) == price_pnl + fx_pnl ± 1원` (Decimal rounding 허용 오차).
- `fx_rate_snapshots` 시계열 테이블 신설 — `fx_refresh_job` 매 tick 마다 snapshot 누적.
- 본 PR 머지 직후부터 신규 거래에 대해서는 즉시 분리값 활성. 기존 보유 자산 (snapshot 누적 이전 거래) 은 `fx_warning="missing_historical_rate"` + 합산만 표시.
- 프론트엔드 holdings 테이블·summary 카드에서 두 값을 별도 라벨로 표시.
- 환율 데이터 부족 시 graceful fallback (기능은 살아있고, 분리 표시만 비활성).
- 회귀 테스트로 항등식 검증.

## 3. 범위

### 포함 (in scope)

- **DB**: `fx_rate_snapshots` 신규 테이블 + Alembic migration. 기존 `fx_rates` 스키마 변경 없음.
- **Scheduler**: `app/scheduler/fx_refresh_job.py` (또는 `services/fx_rate.py::refresh_all`) — fx_rates upsert 직후 동일 trans 안에서 snapshot row insert.
- **Repository**: `FxRateRepository.insert_snapshot(...)` 와 `get_rate_at(base, quote, at)` 신규 메서드.
- **Service**: `services/portfolio.py` 에 `_compute_price_fx_split(...)` helper + `get_holdings`/`get_summary` 통합. `_compute_price_fx_split` 은 KRW-only 등 동일 통화 분기를 직접 처리 (return `fx_pnl=0`, `price_pnl=total_pnl`).
- **Schema**: `HoldingResponse.price_pnl | fx_pnl | fx_warning`, `PortfolioSummaryResponse.converted_price_pnl | converted_fx_pnl | fx_warning` 필드 추가.
- **Frontend**: 타입·API 매핑·holdings 테이블/리스트·summary 카드 분해 표시 + `FxWarningBadge`.
- **테스트**: 단위 (helper 항등식 / 동일 통화 / missing snapshot / 부분매도 잔여), 통합 (snapshot seed → repository → service 응답 항등식), RTL (3 분기).

### 제외 (out of scope)

- **TWR/IRR 의 historical FX 호환성** — `services/portfolio_history.py::convert_at` 통합은 #97 머지 후 별도 chore PR. 본 PR 은 portfolio holdings/summary 만 건드림. (충돌 회피 인라인 처리는 backend.md 참고.)
- 거래일 시점 환율을 거래 등록 폼에서 사용자가 직접 입력하는 UI.
- `realized_pnl` 의 가격/환차 분리 — 본 PR 은 미실현(unrealized) 만 분리. 실현손익은 후속 작업.
- `fx_rate_snapshots` 의 백필 — 본 PR 머지 시점 이전 fetched 환율은 snapshot 으로 옮기지 않음. 머지 직후부터 누적 시작.
- 시계열 환차손익 (Portfolio history 차트의 fx_pnl 분리) — #66 위험지표 이슈로 이관.
- 평균매수가 회계 방식 변경 — 기존 이동평균 그대로.
- 기존 `pnl_abs` / `converted_pnl_abs` 필드 제거 — 합산 값 유지하여 하위 호환성 보장.

## 4. 대상 사용자

- **단일 owner** — assetlog 의 단일 사용자 모델 그대로.
- **다중 통화 보유자** — KRW 외화 (USD/EUR) 자산 1건 이상 보유한 사용자가 직접 수혜.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-1 | 사용자로서 USD 자산의 손익이 가격변동 vs 환변동 중 어디서 왔는지 알고 싶다 | 1) holdings 테이블 손익 셀에 `+10만원 (가격 +8만 · 환차 +2만)` 패턴 표시 2) summary 카드 "미실현 손익" 영역에 동일 분해 노출 3) KRW only 자산은 환차 라벨 숨김 |
| US-2 | 사용자로서 환율 데이터가 부족한 경우에도 화면이 깨지지 않고 이해 가능한 메시지가 보여야 한다 | 1) snapshot 부재 시 holdings 행에 "환율 데이터 누적 중" 인포 아이콘 + tooltip 2) `price_pnl`/`fx_pnl` 은 null 이지만 기존 `pnl_abs (converted)` 는 그대로 표시 3) summary 카드는 분리 라벨 없이 합산만 표시 |
| US-3 | 개발자로서 응답 항등식이 자동 회귀로 검증되어야 한다 | 1) `total_pnl == price_pnl + fx_pnl ± 1원` 단위·통합 테스트 2) 환율 +10% / 가격 +20% 합성 시나리오에서 정확한 분배 3) 100% 매도된 자산의 분리값 모두 0 |
| US-4 | 운영자로서 매시간 fx 갱신 잡이 snapshot 을 누적하여 미래 거래의 분리값이 즉시 동작해야 한다 | 1) `fx_refresh_job` 1회 tick 후 `fx_rate_snapshots` 에 페어당 1행 insert 2) 동일 `(base, quote, recorded_at)` 중복 insert 차단 (UNIQUE) 3) 매수 직후 snapshot row 가 존재하면 `get_rate_at(base, quote, traded_at)` 가 가장 가까운 과거 행 반환 |

## 6. 핵심 플로우

### 6.1 환산 모드 진입 (행복 경로)

```
1. 사용자가 통화 토글을 "KRW" 로 설정
2. 프론트가 GET /api/portfolio/holdings?convert_to=KRW 호출
3. 백엔드:
   a. 현재 환율 (cached, fx_rates) 로 latest_value, cost_basis 환산
   b. 각 BUY 거래의 traded_at 시점 snapshot 조회 (FxRateRepository.get_rate_at)
   c. 가중평균 fx_buy_avg = Σ(cost_i × fx_i) / Σ(cost_i)
   d. price_pnl, fx_pnl 분해 (§6.2 알고리즘)
4. 프론트가 holdings 테이블·summary 카드에 분해 표시
5. 항등식 검증: pnl_abs (converted) == price_pnl + fx_pnl ± rounding
```

### 6.2 알고리즘 정의

기호:
- `q` = 보유 수량 (remaining_qty)
- `p_now` = 현재가 (현지통화)
- `p_avg` = 평균매수가 (현지통화, 이동평균)
- `fx_now` = 현재 환율 (from_currency → convert_to)
- `fx_buy_avg` = 거래일 환율의 cost-weighted 가중평균

**가격 손익** — "환율이 매수 시점과 동일하다고 가정 시 손익":
```
price_pnl = (p_now - p_avg) × q × fx_now
          = converted_latest_value - (cost_basis × fx_now)
```

**환차 손익** — "원금에 환율 변동이 미친 영향":
```
fx_pnl = p_avg × q × (fx_now - fx_buy_avg)
       = cost_basis × (fx_now - fx_buy_avg)
```

**항등식**: `price_pnl + fx_pnl == converted_pnl_abs`.

### 6.3 거래일 환율 가중평균 (`fx_buy_avg`)

매수 거래만 사용. 매수 거래 t_i 의 `traded_at` 기준 환율 `fx_i = repo.get_rate_at(base, quote, t_i.traded_at)`, 매수 비용 (현지통화) `cost_i = quantity_i × price_i`:

```
fx_buy_avg = Σ(cost_i × fx_i) / Σ(cost_i)   ;  i ∈ BUY transactions only
```

부분매도가 있어도 `p_avg` 는 이동평균으로 유지 — SELL 은 평균매수가/가중평균 환율 모두 갱신하지 않음 (기존 `total_bought_qty` / `total_bought_cost` 패턴과 동일).

### 6.4 환율 미가용 처리 (예외 경로)

| 시나리오 | 처리 |
|---------|------|
| BUY 거래 1건이라도 `get_rate_at` 이 None 반환 | `price_pnl=null`, `fx_pnl=null`, `fx_warning="missing_historical_rate"`. 기존 `converted_pnl_abs` 는 가능하면 그대로 (현재 환율만 있으면 됨). |
| 현재 환율 missing | 기존 동작 그대로 — 모든 converted_* null. price_pnl/fx_pnl 도 null. `fx_warning="missing_current_rate"`. |
| 동일 통화 (KRW asset → KRW report) | helper 가 직접 분기: `fx_pnl=0`, `price_pnl=total_pnl`, `fx_warning=null` (또는 응답에서 "same_currency" 로 표시 안 함, 단 frontend 가 분기 시 활용 가능하도록 `"same_currency"` 옵션 보유). 본 PR 은 backend 가 `fx_warning=null` 반환, frontend 가 `displayCurrency === asset.currency` 로 직접 KRW-only 분기. |
| 100% 매도 (remaining_qty = 0) | `cost_basis = 0`, `latest_value = 0` → `price_pnl = 0`, `fx_pnl = 0`. |

## 7. 데이터 모델

§13 (데이터 모델 상세) 참고.

## 8. API 계약 (요약)

### `GET /api/portfolio/holdings?convert_to={CCY}` — `HoldingResponse[]`

추가 필드 (모두 환산 모드 + 환율 가용 시에만 non-null):

```json
{
  "user_asset_id": 12,
  "asset_symbol": { ... },
  "quantity": "10.0000000000",
  "avg_cost": "170.500000",
  "cost_basis": "1705.00",
  "realized_pnl": "0",
  "latest_price": "175.20",
  "latest_value": "1752.00",
  "pnl_abs": "47.00",
  "pnl_pct": 2.76,
  "weight_pct": 21.4,
  "is_pending": false,
  "is_stale": false,
  "last_price_refreshed_at": "...",
  "converted_latest_value": "2417760.00",
  "converted_cost_basis": "2353900.00",
  "converted_pnl_abs": "63860.00",
  "converted_realized_pnl": "0",
  "display_currency": "KRW",

  "price_pnl": "48700.00",          // (p_now - p_avg) × q × fx_now
  "fx_pnl": "15160.00",             // p_avg × q × (fx_now - fx_buy_avg)
  "fx_warning": null                 // null | "missing_historical_rate" | "missing_current_rate" | "same_currency"
}
```

> 주: 이전 draft 의 `fx_buy_avg` 는 응답에서 제거 (디버깅 용도라면 별도 admin 엔드포인트). 본 PR 의 응답은 `price_pnl`, `fx_pnl`, `fx_warning` 3개만.

**불변식**: `Decimal(price_pnl) + Decimal(fx_pnl) ≈ Decimal(converted_pnl_abs)` 오차 ≤ 1 currency-unit.

### `GET /api/portfolio/summary?convert_to={CCY}` — `PortfolioSummaryResponse`

```json
{
  "converted_total_value": "...",
  "converted_total_cost": "...",
  "converted_pnl_abs": "...",

  "converted_price_pnl": "8000000.00",
  "converted_fx_pnl":    "2000000.00",
  "fx_warning": null
}
```

한 holding 이라도 `fx_warning="missing_historical_rate"` 면 summary 의 두 합계는 모두 null + `fx_warning="missing_historical_rate"`.

### 직렬화

- 모든 Decimal 값은 string 직렬화 (기존 패턴 일관).
- `fx_warning` 은 enum-ish string. Literal 권장: `"missing_historical_rate" | "missing_current_rate" | "same_currency" | null`.

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | `GET /api/portfolio/holdings?convert_to=KRW` p95 < 300ms (홀딩 50개 기준). snapshot 조회는 N+M 쿼리 회피 — `(base, quote)` 페어별로 batch fetch (BUY 거래의 traded_at 들을 모은 후 한 번의 `IN (...)` 쿼리). |
| 정확성 | Decimal-only 산술. float 중간 캐스트 금지. 항등식 오차 ≤ 1원 |
| 회귀 | 기존 `converted_pnl_abs` 동일 값 유지 |
| 로깅 | snapshot insert 성공/실패 `logger.info`. 환율 missing 시 `logger.debug` (event=fx_split_skip, currency, reason). PII 없음 |
| 호환성 | 신규 필드 모두 nullable + default null. 기존 클라이언트는 무시하고 동작 |
| 스토리지 | `fx_rate_snapshots` 행 크기 ≈ 80 byte. 페어 5개 × hourly = 연간 ~3.5MB. 보존 정책 §12 오픈 이슈 |

## 10. 의존성 / 리스크

### 10.1 거래일 환율 조회 인프라 — 결정 완료

| 옵션 | 채택 |
|-----|------|
| A. 별도 시계열 테이블 (`fx_rate_snapshots`) | **채택** |
| B. 외부 API 즉석 조회 | 미채택 — 거래일이 과거이면 일부 adapter 가 무료 플랜에서 historical 미지원 |
| C. `fx_buy_avg = fx_now` 근사 | 미채택 — 본 PR 의 분리 의미 자체 상실 |
| D. #97 (`convert_at`) 머지 대기 | 미채택 — #63 P0, 의존성 회피 |
| E. Stub (helper 만 추가, 항상 null 반환) | **사용자 거부** |

**결정**: §3 "포함" 의 모든 항목을 본 PR 안에서 처리한다. 마이그레이션·스케줄러·서비스 변경 모두 포함. 본 PR 머지 직후부터 fx_refresh_job tick 마다 snapshot 누적되며, 머지 후 신규 거래는 즉시 분리값 활성화. 기존 보유 자산은 snapshot 부족 분기로 `fx_warning="missing_historical_rate"`. 다음 환율 갱신부터 (그 이후 새로 추가된 매수에 한해) 누적.

마이그레이션 정책: **백필 없음** (시작 시점부터 누적). 기존 보유 USD 자산은 마이그레이션 직후 1회만 fx_pnl=null + warning, 다음 환율 갱신부터 새 매수가 일어나면 누적.

### 10.2 #97 충돌 회피

본 PR 은 origin/main 에서 시작했으므로 `FxRateService.convert_at` 미존재. snapshot 조회는 `FxRateRepository.get_rate_at` (신규) 직접 호출. 향후 #97 머지되면 `FxRateService.convert_at` 가 내부에서 `get_rate_at` 사용하도록 통합 — **별도 chore PR**.

### 10.3 리스크

- **혼동 가능성**: 환율 부족 시 `converted_pnl_abs` 는 표시되는데 분리 라벨만 사라지는 UX → 툴팁으로 "환율 데이터 누적 중" 명시.
- **항등식 부동소수 오차**: Decimal 28자리 정밀도이지만 곱셈 누적에서 누적 오차 가능 → 테스트 허용오차 1 currency-unit.
- **회계 일관성**: `realized_pnl` 은 분리하지 않음 → Total = unrealized split + realized lump. 이 비대칭은 §3 비목표 명시.
- **snapshot 무한 증가**: 페어 N개 × hourly tick 으로 시계열 증가. 보존 정책은 §12 오픈 이슈.

## 11. 범위 외 (Out of Scope)

§3 "제외" 동일.

## 12. 오픈 이슈

- [ ] **(결정 필요)** `fx_rate_snapshots` 보존 정책. 기본값 무한 보존 (스토리지 비용 미미). 환경변수 `FX_SNAPSHOT_RETENTION_DAYS` 옵션으로 cleanup job 추가 여부 — 후속 PR 검토. 본 PR 은 보존 무한.
- [ ] **(검증 필요)** Holdings 테이블 UI 가 "+10만원 (가격 +8만 · 환차 +2만)" 패턴인지, 별도 행으로 expand 인지 — `ui-designer` 와 합의.
- [ ] **(검증 필요)** snapshot 조회 batch 패턴 — BUY 거래 N건의 traded_at 을 한 쿼리로 가져올 때 `IN` 절 + Python 측 nearest-past 매칭 vs DB 측 lateral join. backend 구현 시 결정 (단 N+1 만은 회피).

## 13. 데이터 모델 — `fx_rate_snapshots` (신규)

```
fx_rate_snapshots
├ id              BIGINT PK AUTO_INCREMENT
├ base_currency   VARCHAR(10) NOT NULL
├ quote_currency  VARCHAR(10) NOT NULL
├ rate            NUMERIC(20, 8) NOT NULL
├ recorded_at     DATETIME(timezone) NOT NULL
└ created_at      DATETIME(timezone) NOT NULL DEFAULT NOW()

UNIQUE  (base_currency, quote_currency, recorded_at)   -- 중복 차단
INDEX   (base_currency, quote_currency, recorded_at DESC)  -- get_rate_at 의 nearest-past 조회
```

- `recorded_at` 은 환율을 fetch 한 timestamp (= `fx_rates.fetched_at` 과 동일 시점). UNIQUE 가 동일 tick 의 중복 insert 차단.
- `base_currency`/`quote_currency` 는 ISO-4217 코드 (현재 `fx_rates` 와 동일 변환 규칙).
- 기존 `fx_rates` 테이블 변경 없음 — single-row-per-pair 의미 유지.

`get_rate_at(base, quote, at)` 의미: `WHERE base=? AND quote=? AND recorded_at <= at ORDER BY recorded_at DESC LIMIT 1`. 매칭되는 행이 없으면 None.

---

## 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | DB migration · Model · Repository · Scheduler · Service · Schema · 단위/통합 테스트 | [`./fx-pnl-split/backend.md`](./fx-pnl-split/backend.md) |
| frontend | 타입 갱신, API 매핑, holdings 테이블·summary 카드 분해 표시, fallback UI, RTL 테스트 | [`./fx-pnl-split/frontend.md`](./fx-pnl-split/frontend.md) |

계약 변경 시 본 PRD §8 / §13 먼저 갱신 → 양쪽 프롬프트 업데이트.
