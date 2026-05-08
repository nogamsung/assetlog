# fx-pnl-split — backend (python) 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**.
> 대응 PRD: [`../fx-pnl-split.md`](../fx-pnl-split.md) — 특히 §3 범위, §6 알고리즘, §8 API 계약, §10.1 결정, §13 데이터 모델
> 대응 스택: python (FastAPI) — 경로 `backend/`

---

## 맥락 (꼭 읽을 것)

- PRD `docs/specs/fx-pnl-split.md` — 결정 lock 됨. stub 폐기, `fx_rate_snapshots` 시계열 테이블 채택.
- `backend/CLAUDE.md` — async 일관성, Schema≠Model, mypy strict, Decimal-only 산술, alembic 새 revision, 테스트 없이 Service 추가 금지.
- 핵심 기존 파일:
  - `backend/app/models/fx_rate.py` — `FxRate` (single-row-per-pair, 변경 없음)
  - `backend/app/repositories/fx_rate.py` — `upsert`, `get_latest`, `list_all`. **여기에 `insert_snapshot`, `get_rate_at` 추가**.
  - `backend/app/services/fx_rate.py` — `FxRateService.refresh_all`. **upsert 직후 snapshot insert 호출 추가**.
  - `backend/app/scheduler/fx_refresh_job.py` — refresh_all 호출. (수정 불필요 — service 내부에서 snapshot 처리)
  - `backend/app/services/portfolio.py` — `get_holdings`, `get_summary`. **분리 helper + 통합**.
  - `backend/app/schemas/portfolio.py` — `HoldingResponse`, `PortfolioSummaryResponse`. **필드 추가**.
  - `backend/app/repositories/portfolio.py` — `list_holdings_with_aggregates`. **BUY 거래의 traded_at 노출 필요**.
  - `backend/app/domain/portfolio.py` — `HoldingRow` 확장.
  - `backend/app/exceptions.py` — `FxRateNotAvailableError` 이미 존재.
  - `backend/alembic/versions/` — 신규 revision 추가.

## 이 역할의 책임 범위

**포함**:
- 신규 ORM 모델 `FxRateSnapshot` + Alembic migration
- `FxRateRepository.insert_snapshot(base, quote, rate, recorded_at)` 신규
- `FxRateRepository.get_rate_at(base, quote, at)` 신규 — nearest-past 조회
- `FxRateService.refresh_all` 수정 — upsert 직후 snapshot insert (동일 trans)
- `services/portfolio.py::_compute_price_fx_split(...)` private helper
- 거래일 환율 가중평균 계산 — BUY 거래별 `repo.get_rate_at` 호출 (N+1 회피 — batch 조회)
- `repositories/portfolio.py::list_holdings_with_aggregates` 시그니처 확장 — BUY 거래의 `(traded_at, cost)` 리스트 노출
- `HoldingResponse.price_pnl | fx_pnl | fx_warning` 추가 (모두 nullable)
- `PortfolioSummaryResponse.converted_price_pnl | converted_fx_pnl | fx_warning` 추가
- 단위/통합 테스트 (helper, repository, service)

**제외**:
- UI / 프론트엔드
- `services/portfolio_history.py` 의 historical FX 통합 — #97 머지 후 별도 chore PR
- `FxRateService.convert_at` 메서드 신설 — 본 PR 은 `FxRateRepository.get_rate_at` 만. #97 머지 시 service 가 repo 를 위임하도록 통합
- snapshot 보존 정책 / cleanup job — PRD §12 오픈 이슈, 후속 PR
- snapshot backfill — PRD §10.1, 머지 시점부터 누적

## 변경할/생성할 파일 (체크리스트)

### 1. 신규 ORM 모델 (`backend/app/models/fx_rate_snapshot.py` — 신규 파일)

- [ ] 새 클래스 `FxRateSnapshot(Base)`:
  - `__tablename__ = "fx_rate_snapshots"`
  - 필드: `id PK`, `base_currency String(10)`, `quote_currency String(10)`, `rate Numeric(20,8)`, `recorded_at DateTime(timezone=True)`, `created_at DateTime(timezone=True) server_default=func.now()`
  - `__table_args__`:
    - `UniqueConstraint("base_currency", "quote_currency", "recorded_at", name="uq_fx_snap_base_quote_recorded")`
    - `Index("ix_fx_snap_pair_recorded", "base_currency", "quote_currency", "recorded_at")` (DESC 는 MySQL/SQLite 둘 다 인덱스 자체는 정렬 무관 — `ORDER BY ... DESC LIMIT 1` 쿼리에서 옵티마이저가 활용)
- [ ] `app/models/__init__.py` 에 export 추가

### 2. Alembic migration (`backend/alembic/versions/<rev>_create_fx_rate_snapshots.py` — autogenerate)

- [ ] `uv run alembic revision --autogenerate -m "create fx_rate_snapshots table"` 후 자동 생성된 파일 확인
- [ ] 자동 생성 후 다음 검증:
  - `op.create_table("fx_rate_snapshots", ...)` 존재
  - UNIQUE constraint `uq_fx_snap_base_quote_recorded` 존재
  - INDEX `ix_fx_snap_pair_recorded` 존재
  - **기존 `fx_rates` 테이블 ALTER 가 0건** (다른 변경 섞이지 않음 — 섞였다면 본 PR 외 변경. 수동으로 제거)
- [ ] `downgrade()` 가 `op.drop_table("fx_rate_snapshots")` + index/constraint drop 으로 정확히 reverse
- [ ] `uv run alembic upgrade head` & `downgrade -1` 양방향 검증 (테스트 DB)

### 3. Repository 변경 (`backend/app/repositories/fx_rate.py`)

- [ ] **신규 메서드** `async def insert_snapshot(self, base: str, quote: str, rate: Decimal, recorded_at: datetime) -> None`:
  - `FxRateSnapshot(base_currency=base, quote_currency=quote, rate=rate, recorded_at=recorded_at)` add
  - 동일 `(base, quote, recorded_at)` UNIQUE 충돌 시 — MySQL `INSERT IGNORE` 패턴 또는 try/except IntegrityError → debug log 후 swallow (잡 retry 케이스에서 같은 tick 중복 insert 안전 처리)
  - `_session.flush()` 호출하지 않음 (commit 은 호출자/Depends 책임)
  - `logger.debug("fx_rate_snapshot inserted", extra={"event": "fx_snapshot_insert", "base": base, "quote": quote, "recorded_at": recorded_at.isoformat()})`

- [ ] **신규 메서드** `async def get_rate_at(self, base: str, quote: str, at: datetime) -> FxRateSnapshot | None`:
  - 동일 통화 (`base == quote`) 면 early return — caller 에서 처리하도록 None 이 아닌 별도 신호 필요? **권장**: caller (`_compute_price_fx_split`) 가 동일 통화 분기를 직접 처리. 본 메서드는 동일 통화여도 그냥 DB 조회 (None 반환 가능성 높음).
  - 쿼리: `select(FxRateSnapshot).where(base_currency==base, quote_currency==quote, recorded_at <= at).order_by(recorded_at.desc()).limit(1)`
  - 매칭 없으면 None 반환

- [ ] **신규 메서드** `async def get_rates_at_batch(self, base: str, quote: str, ats: list[datetime]) -> dict[datetime, FxRateSnapshot | None]`:
  - 정당화: portfolio service 가 holding 1개당 N 번의 BUY 거래 traded_at 을 조회 — N+1 회피
  - 구현 옵션:
    - (간단) 페어의 모든 snapshot 을 fetch 후 Python 측에서 nearest-past 매칭 (snapshot 1만개 이하면 충분히 빠름)
    - (정확) `(SELECT ... ORDER BY recorded_at DESC LIMIT 1) UNION ALL ...` lateral 패턴
  - **권장**: 본 PR 은 옵션 1 (단순 fetch + Python 매칭) 채택. snapshot 증가율이 hourly × 페어 수 이므로 수년 내 1만개 미만 예상.
  - 매칭 키 일관성을 위해 `dict` 의 key 는 `at` 그대로 (timezone aware datetime).

### 4. Service 변경 — fx_rate (`backend/app/services/fx_rate.py`)

- [ ] `FxRateService.refresh_all` 수정:
  - 기존: 각 페어 fetch → `repo.upsert(base, quote, rate, fetched_at)` 호출
  - 추가: upsert 직후 동일 인자로 `await repo.insert_snapshot(base, quote, rate, fetched_at)` 호출
  - 동일 트랜잭션 — Depends 가 commit 처리. 한 페어 실패해도 다른 페어는 계속 (기존 동작 유지)
  - 로그: snapshot insert 성공/실패 카운트도 함께 반환 (선택적). 최소 `logger.info` 의 extra 에 `snapshots_inserted` 추가.

### 5. Domain 수정 (`backend/app/domain/portfolio.py`)

- [ ] `HoldingRow` dataclass (`frozen=True`) 에 필드 추가:
  - `price_pnl: Decimal | None = None`
  - `fx_pnl: Decimal | None = None`
  - `fx_warning: str | None = None`  # `"missing_historical_rate" | "missing_current_rate" | "same_currency" | None`

> 주: frozen dataclass 이므로 default 값 필수. Repository 가 채우지 않는 필드는 service 에서 `dataclasses.replace` 로 덮어쓰기.

### 6. Repository 변경 — portfolio (`backend/app/repositories/portfolio.py`)

- [ ] `list_holdings_with_aggregates` 의 반환 객체에 BUY 거래의 `(traded_at, cost_local)` 리스트 노출 필요. 옵션:
  - (A) `HoldingRow` 자체에 `buy_lots: tuple[tuple[datetime, Decimal], ...]` 추가 (frozen 호환)
  - (B) 별도 메서드 `list_buy_lots(user_asset_id) -> list[(datetime, Decimal)]` 추가하여 service 에서 holding 마다 호출

  **권장**: (A) — service 가 holding loop 안에서 추가 쿼리 발행 시 N+1. 기존 `list_holdings_with_aggregates` 가 transactions 를 이미 조인 중이라면 같은 쿼리 결과에서 추출. 그렇지 않으면 holdings 조회 후 별도 1쿼리로 BUY transactions 만 조회 (`WHERE user_asset_id IN (...) AND tx_type = 'BUY'`).

- [ ] BUY lot 의 `cost_local` 정의: `quantity × price` (현지통화 기준). `traded_at` 은 거래 일자 timestamp. `tuple` 로 frozen dataclass 호환.

### 7. Service 변경 — portfolio (`backend/app/services/portfolio.py`)

- [ ] **신규 private dataclass + helper**:

  ```python
  @dataclass(frozen=True)
  class PriceFxSplit:
      price_pnl: Decimal | None
      fx_pnl: Decimal | None
      warning: str | None  # "missing_historical_rate" | "missing_current_rate" | "same_currency" | None
  ```

  ```python
  def _compute_price_fx_split(
      *,
      cost_basis_native: Decimal,        # p_avg × q (현지통화)
      latest_value_native: Decimal | None,  # p_now × q (현지통화)
      fx_now: Decimal | None,            # 현재 환율 (from_cur → convert_to). None = unavailable.
      fx_buy_avg: Decimal | None,        # 거래일 환율 cost-weighted 평균. None = historical missing.
      from_currency: str,
      to_currency: str,
  ) -> PriceFxSplit:
  ```

  로직:
  1. `from_currency == to_currency` (예: KRW asset → KRW report) → `price_pnl = (latest_value_native - cost_basis_native) if latest_value_native is not None else None`, `fx_pnl = Decimal("0")`, `warning = "same_currency"` (또는 None — 응답에서 frontend 가 분기하므로 None 권장. 본 PR 은 **None** 반환).
  2. `latest_value_native is None` (pending) 또는 `fx_now is None` → 모두 None + `warning = "missing_current_rate"`.
  3. `fx_buy_avg is None` (snapshot missing) → `price_pnl = None`, `fx_pnl = None`, `warning = "missing_historical_rate"`.
  4. 정상 경로:
     ```
     price_pnl = (latest_value_native - cost_basis_native) * fx_now
     fx_pnl    = cost_basis_native * (fx_now - fx_buy_avg)
     warning   = None
     ```
  5. 모든 산술은 Decimal — `float` 캐스트 금지. sync 함수 (DB 접근 없음).

- [ ] **신규 private async helper** `_compute_fx_buy_avg(...)`:

  ```python
  async def _compute_fx_buy_avg(
      *,
      fx_repo: FxRateRepository,
      base: str,
      quote: str,
      buy_lots: Sequence[tuple[datetime, Decimal]],  # (traded_at, cost_local) per BUY
  ) -> Decimal | None:
  ```

  로직:
  1. `base == quote` → `Decimal("1")` 반환 (early)
  2. `buy_lots` 비어있으면 None
  3. `traded_ats = [lot[0] for lot in buy_lots]` 로 batch 조회: `snapshots = await fx_repo.get_rates_at_batch(base, quote, traded_ats)`
  4. 한 lot 이라도 snapshot None 이면 전체 None 반환 (PRD §6.4)
  5. `weighted = Σ(cost_local × snapshot.rate) / Σ(cost_local)` Decimal 계산
  6. 분모 0 이면 None

- [ ] **`get_holdings` 통합**:
  - 환산 모드 (`convert_to is not None`):
    - 각 holding 마다:
      - `cost_basis_native = h.cost_basis`
      - `latest_value_native = h.latest_value`
      - `fx_now` = 기존 `convert` 또는 `get_all_rates_for_conversion` 결과의 페어 비율
      - `fx_buy_avg = await _compute_fx_buy_avg(fx_repo, base=h.asset_symbol.currency, quote=convert_to, buy_lots=h.buy_lots)`
      - `split = _compute_price_fx_split(cost_basis_native=..., latest_value_native=..., fx_now=fx_now, fx_buy_avg=fx_buy_avg, from_currency=h.asset_symbol.currency, to_currency=convert_to)`
      - `dataclasses.replace(h, price_pnl=split.price_pnl, fx_pnl=split.fx_pnl, fx_warning=split.warning)`
  - 환산 미사용 모드 → 모든 분리 필드 None.
  - **N+1 회피**: 페어별로 snapshot batch fetch. 즉 USD/KRW 페어에 대해 모든 holdings 의 traded_at 합집합으로 1쿼리.
  - 환율 missing 으로 fail 한 holding 만 분리값 null — 다른 holding 은 정상 (행 단위 partial).

- [ ] **`get_summary` 통합**:
  - 환산 모드:
    - `holdings = await self.get_holdings(...)` 재사용 (이미 split 채워짐)
    - 한 holding 이라도 `fx_warning == "missing_historical_rate"` → `converted_price_pnl=None`, `converted_fx_pnl=None`, `fx_warning="missing_historical_rate"` (전체 합산 금지)
    - 모두 정상 (또는 same-currency only) → `converted_price_pnl = sum(h.price_pnl or 0)`, `converted_fx_pnl = sum(h.fx_pnl or 0)`, `fx_warning=None`
    - `missing_current_rate` 인 경우 — 기존 `converted_pnl_abs` 도 partial 인 상태이므로 일관되게 summary 의 분리도 None + `fx_warning="missing_current_rate"`

### 8. Schema 수정 (`backend/app/schemas/portfolio.py`)

- [ ] `HoldingResponse` 에 3개 필드 추가:
  - `price_pnl: Decimal | None = None` — `description="(p_now - p_avg) × q × fx_now in display_currency. Null if convert_to absent or historical FX missing."`
  - `fx_pnl: Decimal | None = None` — `description="p_avg × q × (fx_now - fx_buy_avg) in display_currency. Null if convert_to absent or historical FX missing."`
  - `fx_warning: Literal["missing_historical_rate", "missing_current_rate", "same_currency"] | None = None`
  - `@field_serializer("price_pnl", "fx_pnl")` — string 직렬화 (기존 패턴 일관)
- [ ] `PortfolioSummaryResponse` 에 3개 필드 추가:
  - `converted_price_pnl: Decimal | None = None`
  - `converted_fx_pnl: Decimal | None = None`
  - `fx_warning: Literal[...] | None = None`
  - 직렬화: 기존 `_serialize_converted_decimal` 또는 동등 패턴에 두 필드 추가

> 주: `Literal` 사용 시 frontend 와 enum 값 동기화 — PRD §8 명세.

### 9. Tests (`backend/tests/`)

> backend/CLAUDE.md MUST: "테스트 없이 Service 메서드 추가 금지". 라인 커버리지 ≥ **90%** (pre-push).

- [ ] `tests/repositories/test_fx_rate.py` — 기존 파일 확장:
  - `test_insert_snapshot_basic` — 1행 insert → list 로 확인
  - `test_insert_snapshot_unique_violation_swallowed` — 동일 `(base, quote, recorded_at)` 두 번 insert → IntegrityError swallow, row 1개만 존재
  - `test_get_rate_at_returns_nearest_past` — 3개 snapshot seed (1h ago, 30m ago, 10m ago). `at=20m_ago` → 30m_ago 행 반환
  - `test_get_rate_at_no_match_returns_none` — `at` 이 모든 snapshot 보다 이전 → None
  - `test_get_rate_at_exact_match` — `at == recorded_at` 인 행이 있으면 그 행 반환
  - `test_get_rates_at_batch_basic` — 3개 traded_at 동시 조회 → dict 반환

- [ ] `tests/services/test_fx_rate.py` (또는 동등 위치):
  - `test_refresh_all_inserts_snapshot_alongside_upsert` — refresh_all 1회 호출 후 fx_rates 1행 + fx_rate_snapshots 1행 (페어당)
  - `test_refresh_all_idempotent_snapshot` — 같은 fetched_at 으로 두 번 호출 → snapshot 은 UNIQUE 로 중복 차단

- [ ] `tests/services/test_portfolio.py` (단위):
  - `test_split_helper_normal_case` — 환율 +10%, 가격 +20% (USD asset → KRW). `p_avg=100, p_now=120, q=10, fx_now=1100, fx_buy_avg=1000` (KRW per USD). 기댓값:
    - `price_pnl = (120-100) × 10 × 1100 = 220_000`
    - `fx_pnl = 100 × 10 × (1100-1000) = 100_000`
    - `total_pnl_converted = 120×10×1100 - 100×10×1000 = 1_320_000 - 1_000_000 = 320_000`
    - 항등식: `220_000 + 100_000 == 320_000 ✓`
  - `test_split_helper_loss_currency` — 환율 -10%, 가격 +20% (음수 fx_pnl 검증)
  - `test_split_helper_same_currency` — `from_currency == to_currency` → `fx_pnl=0`, `price_pnl=total_pnl`, `warning=None`
  - `test_split_helper_missing_historical` — `fx_buy_avg=None` → 모두 None + `warning="missing_historical_rate"`
  - `test_split_helper_missing_current` — `fx_now=None` → 모두 None + `warning="missing_current_rate"`
  - `test_split_helper_pending_holding` — `latest_value_native=None` → 모두 None + `warning="missing_current_rate"`
  - `test_split_helper_partial_sell_remainder` — 부분매도 후 잔여 — `cost_basis_native = p_avg × remaining_qty`, BUY 거래의 가중평균 환율은 SELL 무관. 항등식 통과
  - `test_split_helper_decimal_precision` — `Decimal("0.123456789012345678")` 같은 정밀도가 큰 입력에서도 항등식 오차 ≤ 1 unit
  - `test_split_helper_zero_qty_after_full_sell` — `cost_basis_native=0`, `latest_value_native=0` → `price_pnl=0`, `fx_pnl=0`

- [ ] `tests/services/test_portfolio.py` (통합 — fx_rate_snapshots seed 후 Service 응답 검증):
  - `test_get_holdings_split_with_seeded_snapshot` — fx_rate_snapshots 에 BUY 시점 환율 seed → Service 가 `price_pnl`, `fx_pnl` 정확히 채움
  - `test_get_holdings_split_missing_snapshot_returns_warning` — snapshot 비어있음 → `fx_warning="missing_historical_rate"`
  - `test_get_holdings_identity_invariant` — `Decimal(price_pnl) + Decimal(fx_pnl) == Decimal(converted_pnl_abs) ± 1` USD/KRW 자산
  - `test_get_summary_aggregation_all_normal` — 2개 holdings 모두 정상 → 합계 정확
  - `test_get_summary_aggregation_one_missing_blocks_total` — 한 holding 만 missing → 두 합계 None + warning
  - `test_get_holdings_krw_only_returns_zero_fx_pnl` — KRW 자산만 → `fx_pnl=0`, `price_pnl=converted_pnl_abs`, `fx_warning=None`

- [ ] `tests/routers/test_portfolio.py` — 응답 키 존재 확인:
  - `test_holdings_response_has_split_fields_when_convert_to`
  - `test_summary_response_has_aggregated_split_fields`
  - `test_holdings_response_no_split_fields_without_convert_to` — `price_pnl=None`, `fx_pnl=None`, `fx_warning=None`

- [ ] **회귀 검증**: 기존 `tests/services/test_portfolio.py` 의 holdings/summary 테스트 모두 통과 (기존 `pnl_abs`, `converted_pnl_abs` 의미 동일).

### 10. OpenAPI / 응답 메타

- [ ] `routers/portfolio.py` 의 `response_model=` 자동 반영. `responses=` 메타 추가 작업 불필요.

## 구현 제약 (`backend/CLAUDE.md` 와 충돌 회피)

- **MUST**: async 일관성. `_compute_price_fx_split` 은 sync (DB 접근 없음). `_compute_fx_buy_avg` 는 async (repo 호출).
- **MUST**: Decimal 산술. `float` 캐스트 금지.
- **MUST**: Schema ≠ Model. Pydantic `model_config = ConfigDict(from_attributes=True)` 유지.
- **MUST**: ORM 은 `Mapped[...] = mapped_column(...)` 패턴.
- **MUST**: Alembic 새 revision 만 생성, 기존 revision 수정 금지.
- **NEVER**: `services/` 에서 `HTTPException` import 금지. `FxRateNotAvailableError` 도 service 에서 catch → warning 으로 변환 (graceful fallback).
- **NEVER**: `print()` — `logger.debug` / `logger.info` 사용.
- **NEVER**: 테스트 없이 Service 메서드 추가.
- **NEVER**: raw SQL 하드코딩 — `select(...)` ORM 또는 `text()` + 바인딩.
- **의존성 추가 0** — 외부 패키지 신설 없음. SQLAlchemy / Pydantic / Alembic 모두 기존.

## 다른 역할과의 계약 (Interface)

- **→ frontend 로 제공** (response schema):
  ```
  HoldingResponse {
    ...existing,
    price_pnl:  string | null,        // Decimal as string
    fx_pnl:     string | null,        // Decimal as string
    fx_warning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null,
  }
  PortfolioSummaryResponse {
    ...existing,
    converted_price_pnl: string | null,
    converted_fx_pnl:    string | null,
    fx_warning:          "missing_historical_rate" | "missing_current_rate" | "same_currency" | null,
  }
  ```
- **불변식**: `Decimal(price_pnl) + Decimal(fx_pnl) == Decimal(converted_pnl_abs) ± 1 unit` (둘 다 non-null 일 때).
- **계약 변경 시**: PRD §8 / §13 먼저 갱신 → frontend 프롬프트 동기화.

## #97 와의 관계

- 본 PR 은 origin/main 위에서 시작 → `FxRateService.convert_at` 미존재. 본 PR 의 snapshot 조회는 **`FxRateRepository.get_rate_at` 직접 호출**.
- 향후 #97 머지 후 별도 chore PR 에서 `FxRateService.convert_at(amount, from, to, at)` 가 내부에서 `get_rate_at` 사용하도록 통합. portfolio service 는 그때 `fx_service.convert_at(...)` 로 교체.
- `services/portfolio_history.py` (TWR/IRR) 의 historical FX 통합도 위 chore PR 에서 일괄 처리. 본 PR 은 portfolio holdings/summary 만.

## 실행 지시

이 프롬프트를 받은 agent 는:

1. `backend/CLAUDE.md` 정독 (async, mypy strict, Decimal-only, alembic 정책)
2. PRD `docs/specs/fx-pnl-split.md` §3, §6, §8, §10.1, §13 정독
3. 기존 코드 정독: `services/portfolio.py`, `services/fx_rate.py`, `repositories/fx_rate.py`, `repositories/portfolio.py`, `models/fx_rate.py`, `domain/portfolio.py`, `schemas/portfolio.py`
4. **변경 순서**:
   1. Model (`fx_rate_snapshot.py`) → Alembic migration
   2. Repository (`insert_snapshot`, `get_rate_at`, `get_rates_at_batch`)
   3. Service `fx_rate.refresh_all` 수정 (snapshot insert 추가)
   4. Domain (`HoldingRow` 필드 추가)
   5. Repository `portfolio.list_holdings_with_aggregates` 의 buy_lots 노출
   6. Service `portfolio` (`_compute_price_fx_split`, `_compute_fx_buy_avg`, `get_holdings`/`get_summary` 통합)
   7. Schema (`HoldingResponse`, `PortfolioSummaryResponse`)
   8. Tests (repositories → services → routers)
5. 검증:
   - `uv run alembic upgrade head` & `downgrade -1` (테스트 DB)
   - `uv run pytest --cov=app tests/`. 라인 커버리지 ≥ **90%**
   - `uv run mypy .`
   - `uv run ruff check . && uv run ruff format --check .`
6. 완료 후 리포트:
   - 변경된 파일 목록
   - 신규 schema 필드 정확한 키와 타입 (frontend 동기화용)
   - migration revision id
   - 후속 작업 안내: "#97 머지 후 chore PR — `FxRateService.convert_at` 통합 + portfolio_history 적용"

## 성공 기준

- [ ] `fx_rate_snapshots` 테이블 + Alembic migration 1건 (기존 fx_rates 변경 0)
- [ ] `FxRateRepository.insert_snapshot`, `get_rate_at`, `get_rates_at_batch` 신규 메서드 3개 + 단위 테스트
- [ ] `FxRateService.refresh_all` 이 upsert 직후 snapshot insert 호출 + 통합 테스트
- [ ] `_compute_price_fx_split` 항등식 단위 테스트 (정상 / 손실 / 동일통화 / missing historical / missing current / pending / 부분매도 / Decimal 정밀도 / 0 수량) 9개 모두 통과
- [ ] Schema 신규 필드 6개 (Holding 3 + Summary 3) 직렬화 검증
- [ ] USD→KRW 환산 + snapshot seed → 항등식 통과 (오차 ≤ 1원)
- [ ] USD→KRW 환산 + snapshot 부재 → `fx_warning="missing_historical_rate"`, 두 분리값 null, 기존 `converted_pnl_abs` 정상 응답
- [ ] KRW→KRW → `fx_pnl=0`, `price_pnl=converted_pnl_abs`
- [ ] 기존 holdings/summary 테스트 0건 회귀
- [ ] 라인 커버리지 ≥ **90%**
- [ ] mypy strict 통과, ruff 통과
- [ ] 의존성 추가 0건
