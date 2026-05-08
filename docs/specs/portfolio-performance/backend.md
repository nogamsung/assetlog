# Portfolio Performance — Backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**입니다.
> 대응하는 PRD: [`../portfolio-performance.md`](../portfolio-performance.md)
> 대응하는 스택: **python / FastAPI** (경로: `backend/`)
> 대응하는 브랜치: `feature/portfolio-performance` (worktree: `.worktrees/feature-portfolio-performance/`)
> 대응하는 GitHub Issue: **#61**

---

## 맥락 (꼭 읽을 것 — 순서대로)

1. **PRD 본문**: `docs/specs/portfolio-performance.md` — 특히 7절 (모듈 구조), 8절 (API 계약), 10절 (의존성 결정 — IRR 자체 구현 채택 근거)
2. **backend CLAUDE.md**: `backend/CLAUDE.md` — 필수 규칙 (async 일관성, DI 만 사용, Schema≠Model, Decimal 만 / float 금지, Router 메타 필수)
3. **재사용 대상 (그대로 import)**:
   - `backend/app/repositories/portfolio_history.py::PortfolioHistoryRepository`
     - `list_transactions(currency)` — currency 필터 있음. 본 슬라이스는 **모든 통화** 가 필요 → 새 메서드 `list_all_transactions()` 추가 (currency 파라미터 없음, AssetSymbol.currency 함께 반환)
     - `list_price_points_for_symbols(symbol_ids, since)` — 그대로 사용
   - `backend/app/services/portfolio_history.py::PortfolioHistoryService` — 시계열 빌더 패턴 참고 (포인터 스캔, `_ensure_utc`, `_price_at`)
   - `backend/app/services/fx_rate.py::FxRateService` — `convert(amount, from, to)` 그대로 사용. **단, 거래일 환율은 신규 메서드** `convert_at(amount, from, to, at)` 가 필요
   - `backend/app/repositories/fx_rate.py::FxRateRepository` — `get_latest(base, quote)` 만 있음. **신규 `get_at(base, quote, at)`** 필요
4. **테스트 패턴 참고**:
   - `backend/tests/services/test_portfolio_history_service.py` — AsyncMock + MagicMock(spec=…) 패턴, 한국어 테스트 이름
   - `backend/tests/routers/test_portfolio_history_router.py` — `app.dependency_overrides` + `httpx.AsyncClient` 패턴, 401/200/422 케이스
5. **Pydantic v2 + 직렬화 패턴**: `backend/app/schemas/portfolio.py` — `model_config = ConfigDict(from_attributes=True)`, `@field_serializer` 로 `Decimal → str`

## 이 역할의 책임 범위

### 포함
- `app/services/performance.py` (신규) — 순수 함수 4개 + `PerformanceService`. **재사용성 최우선** — 후속 #62/#66/#67 가 import.
- `app/schemas/performance.py` (신규) — `PerformanceResponse`, `CashflowEntry`, `PerformancePeriod`, `PerformanceMethod`.
- `app/domain/performance.py` (신규) — `PerformancePeriod` StrEnum, `PerformanceMethod` StrEnum, `Cashflow` / `ValuePoint` frozen dataclass.
- `app/repositories/portfolio_history.py` (수정) — `list_all_transactions()` 추가 (currency 미필터, AssetSymbol.currency 포함). 기존 메서드는 그대로.
- `app/repositories/fx_rate.py` (수정) — `get_at(base, quote, at: datetime)` 추가 (`at` 이전의 가장 최근 환율, 없으면 `None`).
- `app/services/fx_rate.py` (수정) — `convert_at(amount, from, to, at)` 추가 (Repository.get_at 호출).
- `app/routers/portfolio.py` (수정) — `GET /api/portfolio/performance` 엔드포인트 추가. 기존 라우터 메타 패턴 동일.
- `app/core/deps.py` (수정) — `PerformanceServiceDep` 추가.
- **Tests**: 4계층 — 순수 함수 단위 (`compute_twr`, `compute_mwr`, `extract_cashflows`, `build_value_series`), 서비스, 리포지토리, 라우터.

### 제외
- 새 ORM 모델 / Alembic migration (PRD 7절 명시)
- 새 외부 패키지 의존성 (PRD 10절 명시 — `numpy_financial`, `scipy` 추가 금지)
- frontend 차트 / UI
- per-symbol / per-tag 분해
- DIVIDEND / INTEREST 트랜잭션
- `cash_accounts` 잔고 포함 (PRD 12절 오픈 이슈)

## 변경할 / 생성할 파일 (체크리스트)

### Domain (신규)
- [ ] `backend/app/domain/performance.py`
  ```python
  import enum
  from dataclasses import dataclass
  from datetime import datetime
  from decimal import Decimal


  class PerformancePeriod(enum.StrEnum):
      ONE_WEEK = "1W"
      ONE_MONTH = "1M"
      THREE_MONTHS = "3M"
      SIX_MONTHS = "6M"
      ONE_YEAR = "1Y"
      YTD = "YTD"
      ALL = "ALL"


  class PerformanceMethod(enum.StrEnum):
      TWR = "twr"
      MWR = "mwr"
      BOTH = "both"


  @dataclass(frozen=True)
  class Cashflow:
      """A signed cashflow in the report currency.

      BUY contributes negative (capital inflow to portfolio = outflow from investor).
      SELL contributes positive.
      """
      date: datetime
      amount: Decimal      # negative for BUY, positive for SELL
      kind: str            # "buy" | "sell"


  @dataclass(frozen=True)
  class ValuePoint:
      """Single timestamped portfolio value (already FX-converted)."""
      timestamp: datetime
      value: Decimal       # report-currency value at this instant
  ```

### Schema (신규)
- [ ] `backend/app/schemas/performance.py` — Pydantic v2 패턴 (`model_config`, `@field_serializer`).
  - `CashflowEntry` — `date: datetime`, `amount: Decimal` (str 직렬화), `kind: Literal["buy", "sell"]`.
  - `PerformanceResponse` — 모든 필드 PRD 8절 응답 스키마와 1:1.
    - `period: PerformancePeriod`, `method: PerformanceMethod`, `currency: str`
    - `start_date: datetime`, `end_date: datetime`
    - `twr: Decimal | None`, `mwr: Decimal | None`
    - `annualized_twr: Decimal | None`, `annualized_mwr: Decimal | None`
    - `start_value: Decimal | None`, `end_value: Decimal | None`
    - `cashflows: list[CashflowEntry]`
    - `warnings: list[str] = Field(default_factory=list)`
  - `Decimal → str` 필드는 모두 `@field_serializer` 로 직렬화 (기존 `portfolio.py` 와 동일 스타일).

### Repository 변경
- [ ] `backend/app/repositories/portfolio_history.py` (수정 — 추가만)
  - 신규 데이터 클래스 `AllTxRow`:
    ```python
    class AllTxRow:
        __slots__ = ("symbol_id", "currency", "traded_at", "quantity", "price", "tx_type")
        # currency = AssetSymbol.currency
    ```
  - 신규 메서드 `list_all_transactions() -> list[AllTxRow]`:
    - 기존 `list_transactions` 와 거의 동일하나 `where(AssetSymbol.currency == currency)` 제거.
    - `AssetSymbol.currency` 를 SELECT 에 포함.
    - 기존 메서드 / `TransactionRow` 는 변경 금지 (history 서비스가 사용 중).

- [ ] `backend/app/repositories/fx_rate.py` (수정 — 추가만)
  - 신규 메서드 `get_at(base_currency: str, quote_currency: str, at: datetime) -> FxRate | None`:
    - `where(base, quote, fetched_at <= at).order_by(fetched_at.desc()).limit(1)`.
    - 결과 없으면 `None` 반환 (예외 발생 금지 — 호출자가 분기).

### Service 변경
- [ ] `backend/app/services/fx_rate.py` (수정 — 추가만)
  - 신규 메서드 `convert_at(amount: Decimal, from_currency: str, to_currency: str, at: datetime) -> Decimal`:
    - `from == to` 면 amount 즉시 반환.
    - `repo.get_at(from, to, at)` 호출. `None` 이면 `FxRateNotAvailableError` raise (기존 `convert` 와 동일 정책).
    - 반환 = `amount * rate_row.rate`.

### Service (신규 — 본 슬라이스의 핵심)
- [ ] `backend/app/services/performance.py`

  **모듈 구조 (재사용성 — PRD 7절 모듈 구조와 1:1):**

  ```python
  """Performance metrics — TWR / MWR(IRR) / cashflow extraction / value series.

  Public functions are PURE — no I/O, no side effects. Repository / FX I/O is
  done in PerformanceService and the inputs are passed to the pure functions.
  This decoupling is intentional — issues #62 (benchmark), #66 (Sharpe / MDD),
  and #67 (monthly heatmap) reuse build_value_series / compute_twr by direct import.
  """
  ```

  **함수 시그니처 — 변경 금지 (후속 이슈가 import 함):**

  ```python
  def extract_cashflows(
      txs: list[AllTxRow],
      report_currency: str,
      fx_at: Callable[[Decimal, str, str, datetime], Decimal],
      window_start: datetime,
      window_end: datetime,
  ) -> list[Cashflow]:
      """Convert transactions in [window_start, window_end] to signed cashflows
      in report_currency.

      BUY  → -(quantity * price * fx)
      SELL → +(quantity * price * fx)

      Same-timestamp BUY+SELL are merged into one Cashflow (sum amounts, kind
      keeps the dominant sign or 'mixed' — pick: kind="buy" if sum < 0 else "sell").

      fx_at(amount, from_cur, to_cur, at) is injected so tests can stub it
      without async / DB. In production it wraps PerformanceService's internal
      sync helper that calls FxRateService.convert_at.
      """


  def build_value_series(
      txs: list[AllTxRow],
      price_index: dict[int, list[tuple[datetime, Decimal]]],
      symbol_currency: dict[int, str],
      fx_at: Callable[[Decimal, str, str, datetime], Decimal],
      report_currency: str,
      timestamps: list[datetime],
  ) -> list[ValuePoint]:
      """For each ts in `timestamps`, compute portfolio value in report_currency.

      Algorithm — same forward-pointer scan as PortfolioHistoryService but with
      per-tx FX conversion at the timestamp `ts`:
        1. Walk txs sorted by traded_at; maintain qty_by_symbol (BUY+, SELL-).
        2. For each ts, sum qty_by_symbol[sym] * price_at(sym, ts) converted
           via fx_at(.., symbol_currency[sym], report_currency, ts).
        3. Return list[ValuePoint].

      Pure — no I/O. price_at uses the existing _price_at helper from
      portfolio_history.py (re-export it from there or duplicate as a private
      _price_at_local — pick re-export to avoid drift).
      """


  def compute_twr(
      value_series: list[ValuePoint],
      cashflows: list[Cashflow],
  ) -> Decimal | None:
      """Time-Weighted Return over [value_series[0].timestamp, value_series[-1].timestamp].

      Algorithm:
        1. Sort cashflows by date.
        2. For each cashflow at time t with amount c:
           - V_before = value at t (interpolated from value_series — pick
             the value AT or just-before t; deterministic via pointer scan)
           - V_after  = V_before + c (cash effect, no market move)
           Subperiod return r_i = (V_before / V_prev_after) - 1
        3. TWR = ∏(1 + r_i) - 1
        4. Final subperiod uses end-of-window value as V_end.

      Returns None if value_series is empty or any V_prev_after <= 0.

      Implementation note — the "interpolated value at cashflow time" is
      typically taken as the value series sample whose timestamp is the latest
      one ≤ t. For typical inputs (daily series, intra-day cashflows) this is
      acceptable; document the choice.
      """


  def compute_mwr(
      cashflows: list[Cashflow],
      terminal_value: Decimal,
      terminal_date: datetime,
      *,
      initial_value: Decimal = Decimal("0"),
      initial_date: datetime | None = None,
  ) -> Decimal | None:
      """Money-Weighted Return = annualized IRR.

      Solves for r:
          -initial_value + Σ cashflows[i].amount / (1+r)^t_i
                         + terminal_value / (1+r)^t_terminal = 0

      where t_i = (cashflows[i].date - reference_date).days / 365.0.

      reference_date = initial_date or cashflows[0].date.
      initial_value treated as a synthetic cashflow at reference_date with
      amount = -initial_value.

      Algorithm — Newton-Raphson with seed r=0.10, max 100 iter, tol=1e-9.
      Fallback to bisection on [-0.99, 10] if Newton diverges or NPV doesn't
      change sign at the bracket. Returns None if both fail (e.g. all-same-sign
      cashflows have no IRR).

      Use Decimal throughout — convert (1+r) ** t via float ONLY for the
      exponent; cast back to Decimal each iteration to limit float drift.
      """
  ```

  **`PerformanceService` (DI-friendly):**

  ```python
  class PerformanceService:
      def __init__(
          self,
          history_repo: PortfolioHistoryRepository,
          fx_service: FxRateService,
      ) -> None:
          self._repo = history_repo
          self._fx = fx_service

      async def get_performance(
          self,
          period: PerformancePeriod,
          method: PerformanceMethod,
          currency: str,
      ) -> PerformanceResponse:
          # 1. Compute window (start_dt, end_dt) — see _compute_window below
          # 2. Load: txs = repo.list_all_transactions()
          #    Split into in-window vs pre-window (for opening position)
          # 3. Load price_index = repo.list_price_points_for_symbols(sym_ids, since=start_dt)
          # 4. Build symbol_currency map from txs (already in AllTxRow)
          # 5. Pre-fetch all needed (from, to, traded_at) FX conversions and cache
          #    in a dict — avoid awaits inside the pure functions.
          #    Then create fx_at_sync closure that reads from this dict.
          # 6. cashflows = extract_cashflows(in_window_txs, currency, fx_at_sync, ...)
          # 7. timestamps = [start_dt] + sorted(cf.date for cf in cashflows) + [end_dt]
          #    (deduped, sorted, all UTC-aware)
          # 8. value_series = build_value_series(all_txs, price_index, sym_cur,
          #                                      fx_at_sync, currency, timestamps)
          # 9. twr = compute_twr(value_series, cashflows) if method in (TWR, BOTH) else None
          # 10. mwr = compute_mwr(cashflows, terminal_value=value_series[-1].value,
          #                       terminal_date=end_dt, initial_value=value_series[0].value,
          #                       initial_date=start_dt) if method in (MWR, BOTH) else None
          # 11. Compute annualized variants (CAGR formula — see PRD 8 응답 필드)
          # 12. Build PerformanceResponse with warnings list (no_activity_in_period,
          #     fx_rate_missing, mwr_unsolvable as appropriate)
          ...
  ```

  **`_compute_window(period, end_dt, txs) -> tuple[datetime, datetime]`** —
  PRD 5절 US-3 수락 기준에 따라:
  - `1W` → end - 7d, `1M` → end - 30d, `3M` → end - 90d, `6M` → end - 180d, `1Y` → end - 365d
  - `YTD` → `datetime(end.year, 1, 1, tzinfo=UTC)`
  - `ALL` → `min(tx.traded_at for tx in txs)` (UTC). 거래 0건이면 `end - 30d` 폴백.

  **FX 캐싱 (성능 — PRD G-3):**
  - `get_performance` 진입 시 한 번 — 거래의 모든 `(from_currency, traded_at)` + `(symbol_currency, ts)` 페어를 수집해 `FxRateRepository.get_at` 을 batch 호출 (N 회 await — 대량이면 `asyncio.gather`).
  - 결과를 `dict[(from, to, at_truncated_to_hour), Decimal]` 에 캐시.
  - `fx_at_sync(amount, from, to, at)` 클로저는 이 dict 만 lookup — 미스 시 `FxRateNotAvailableError`.

### Router 변경
- [ ] `backend/app/routers/portfolio.py` (수정 — 엔드포인트 추가)
  ```python
  @router.get(
      "/performance",
      response_model=PerformanceResponse,
      status_code=status.HTTP_200_OK,
      summary="Get TWR / MWR(IRR) portfolio performance over a period",
      description=(
          "Returns time-weighted return (TWR) and money-weighted return / IRR "
          "(MWR) over the requested period in the requested report currency. "
          "Cashflows are signed (BUY=-, SELL=+) and converted at trade-date FX "
          "rates. If FX rates are missing for any required pair, twr/mwr are "
          "null and a 'fx_rate_missing' warning is returned (HTTP 200)."
      ),
      responses={
          401: {"model": ErrorResponse, "description": "Not authenticated"},
          422: {"model": ErrorResponse, "description": "Validation error"},
      },
  )
  async def get_portfolio_performance(
      _current_user: CurrentUser,
      perf_service: PerformanceServiceDep,
      period: PerformancePeriod = Query(default=PerformancePeriod.ONE_YEAR),
      method: PerformanceMethod = Query(default=PerformanceMethod.BOTH),
      currency: str = Query(default="KRW", min_length=3, max_length=10),
  ) -> PerformanceResponse:
      return await perf_service.get_performance(period, method, currency.upper())
  ```

### DI
- [ ] `backend/app/core/deps.py` (수정 — 추가만)
  ```python
  def get_performance_service(
      history_repo: PortfolioHistoryRepositoryDep,
      fx_service: FxRateServiceDep,
  ) -> PerformanceService:
      return PerformanceService(history_repo=history_repo, fx_service=fx_service)


  PerformanceServiceDep = Annotated[PerformanceService, Depends(get_performance_service)]
  ```

### Tests (라인 커버리지 ≥ 90% 달성 책임)

#### `backend/tests/services/test_performance_pure.py` — 순수 함수 단위 (DB / 비동기 없음)

| 케이스 | 입력 | 기대 출력 | 검증 함수 |
|--------|------|-----------|-----------|
| **단일매수 TWR** — 1년 전 100만원 매수, 현재 120만원 평가 | value_series=[(t0, 1_000_000), (t1, 1_200_000)], cashflows=[(t0, -1_000_000)] | TWR ≈ 0.20 | `compute_twr` |
| **단일매수 MWR** — 동일 fixture | cashflows=[(t0, -1_000_000)], terminal_value=1_200_000, terminal_date=t1 (1y later) | MWR ≈ 0.20 (±1bp) | `compute_mwr` |
| **추가매수 TWR (기하평균)** — t0 100만 (가격 100), t6m 추가 매수 100만 (가격 110), t1y 가격 130 | value_series=[1M @t0, 2.1M @t6m_after, 2.4M @t1y], cashflows=[-1M, -1M] | TWR = (110/100) * (130/110) - 1 = 0.30 | `compute_twr` |
| **부분매도 TWR** — t0 100만 매수, t6m 50% 매도 (가격 110, 회수 55만), t1y 보유분 가격 130 → 평가 65만 | value_series=[1M, 1.1M, 0.65M], cashflows=[-1M, +0.55M] | TWR ≈ 0.30 (시점 영향 X — 매도해도 수익률 동일) | `compute_twr` |
| **부분매도 MWR** — 동일 fixture | cashflows=[-1M @t0, +0.55M @t6m], terminal_value=0.65M @t1y | MWR ≈ 0.30 (±1bp) | `compute_mwr` |
| **거래 없음** | value_series=[] | None | `compute_twr` |
| **현금흐름 부호 단일 (해 없음)** | cashflows=[+100, +200], terminal_value=300, terminal_date later | None (Newton + 이분법 모두 실패) | `compute_mwr` |
| **같은 timestamp BUY+SELL 병합** | txs=[BUY@t, SELL@t] | extract_cashflows 결과 길이 1 (병합) | `extract_cashflows` |
| **window 외 거래 제외** | txs=[BUY@t-2y, BUY@t-3m], window=[t-1y, t] | -3m 거래만 cashflow 로 포함 | `extract_cashflows` |
| **build_value_series 다중 통화** | tx USD 종목 + tx KRW 종목, fx_at stub | report_currency 단일 합계 일치 | `build_value_series` |

**Known fixture 검증 (PRD G-4 — 1bp 이내):**
- `compute_mwr([Cashflow(t0, Decimal("-1000000"), "buy")], Decimal("1200000"), t0 + 365d) == Decimal("0.20")` (±0.0001)
- `compute_twr([(t0, 1_000_000), (t1, 1_200_000)], [(t0, -1_000_000)]) == Decimal("0.20")` (±0.0001)

#### `backend/tests/services/test_performance_service.py` — 서비스 (AsyncMock 리포지토리)

- 정상 시나리오 (`method=both`) → 응답에 twr / mwr 둘 다 채워짐
- `method=twr` → mwr 필드 None
- 환율 부족 → twr/mwr 모두 None, warnings=["fx_rate_missing"]
- 거래 없음 → cashflows=[], twr/mwr None, warnings=["no_activity_in_period"]
- 거래 1건만 → 정상 계산
- `period=YTD` → start_date 가 정확히 해당 연도 1월 1일 UTC
- `period=ALL` → start_date 가 가장 오래된 tx.traded_at

#### `backend/tests/repositories/test_portfolio_history_repository.py` (수정 — 추가)
- `list_all_transactions` — currency 필터 없이 모든 거래 반환, 각 행에 `currency` 포함
- 거래 0건 → 빈 list

#### `backend/tests/repositories/test_fx_rate_repository.py` (또는 신규)
- `get_at` — `at` 이전의 가장 최근 환율 반환
- `at` 보다 모든 환율이 미래 → None
- 같은 base/quote 의 여러 환율 중 가장 최근 (≤ at) 만 반환

#### `backend/tests/routers/test_portfolio_performance_router.py` (신규)
- 401 (미인증) — `await async_client.get("/api/portfolio/performance")` → 401
- 200 (정상) — `app.dependency_overrides` 로 PerformanceService mock 주입 → 응답 키 검증
- 422 (잘못된 period) — `?period=INVALID` → 422
- 422 (잘못된 method) — `?method=foo` → 422
- 200 (warnings 포함) — mock 이 warnings=["fx_rate_missing"] 응답 시 응답 본문에 그대로 직렬화

## 구현 제약 (backend CLAUDE.md 와 충돌하지 않을 것)

- **Decimal 만**: TWR / MWR 계산 중간값 모두 `Decimal`. **단 IRR 의 `(1+r)^t` 지수 연산 한정으로 float 사용 허용** (Decimal 은 비정수 지수 미지원). 매 iteration 끝에 Decimal 로 캐스팅.
- **async 일관성**: `PerformanceService.get_performance` 는 `async def`. 순수 함수 (`compute_twr` 등) 는 sync — 명시적으로 분리.
- **DI 만**: 모듈 전역 인스턴스 금지. 모든 의존성은 `Depends` 통해.
- **services → fastapi.HTTPException 금지**: 비즈니스 예외만 (`FxRateNotAvailableError` 는 catch 해서 warnings 로 변환 — raise 하지 않음).
- **Router 메타 필수**: `response_model`, `responses`, `summary`, `description` 모두 명시. dict 반환 금지.
- **Schema ≠ Model**: 서비스 응답은 `PerformanceResponse.model_validate(...)` 로 빌드 — ORM 모델 직접 반환 금지.
- **로깅**: `print()` 금지. `logger = logging.getLogger(__name__)` 사용. IRR 수렴 실패 / 환율 부족 / 거래 없음은 `logger.info` (warn 아님 — 정상 흐름).
- **`# type: ignore`**: 사용 시 항상 이유 주석 (`# type: ignore[arg-type]  # Decimal ** float`).
- **mypy strict 통과**: 모든 public 함수 타입 힌트. `dataclass` 는 `frozen=True` + 명시 타입.
- **ruff 통과**: import 순서, line length 100, B/UP/I/C4 룰.
- **테스트 async**: `asyncio_mode = "auto"` 활성화됨 — `@pytest.mark.asyncio` 불필요. `AsyncMock` / `MagicMock(spec=...)` 패턴 그대로.

## 다른 역할과의 계약 (Interface)

본 슬라이스는 **backend-only**. frontend 변경 없음. 다만 후속 이슈가 import 할 인터페이스를 잠근다 (PRD 10절 R-4):

**→ 후속 이슈 #62/#66/#67 가 import:**
- `from app.services.performance import build_value_series, compute_twr, extract_cashflows`
- `from app.domain.performance import Cashflow, ValuePoint`
- 시그니처 변경 시 PRD 7절 + 본 프롬프트의 함수 시그니처 블록 먼저 갱신.

**→ frontend 가 호출 (후속 이슈 통합 시):**
- `GET /api/portfolio/performance?period=&method=&currency=` — 응답 스키마는 PRD 8절 참고.
- 응답 필드 변경 시 PRD 8절 먼저 갱신.

## 실행 지시

이 프롬프트를 받은 agent (`python-generator`) 는 아래 순서로 진행합니다:

1. **`backend/CLAUDE.md` + `backend/app/services/portfolio_history.py` + `backend/app/repositories/portfolio_history.py` 먼저 읽기** — 패턴 숙지.
2. **Domain → Schema → Repository (수정) → Service (수정) → Service (신규) → Router → DI** 순서로 생성.
3. **테스트 먼저 작성 권장** — 순수 함수는 TDD 가 적합. fixture 는 PRD G-4 의 known case 부터.
4. **검증**:
   - `cd backend && uv run ruff check . && uv run ruff format --check .` 통과
   - `uv run mypy .` 통과 (strict)
   - `uv run pytest tests/services/test_performance_pure.py -v` 통과
   - `uv run pytest tests/services/test_performance_service.py -v` 통과
   - `uv run pytest tests/routers/test_portfolio_performance_router.py -v` 통과
   - `uv run pytest --cov=app/services/performance --cov-report=term-missing` 라인 커버리지 ≥ 90%
5. **요약 리포트**:
   - 생성된 파일 목록 (절대경로)
   - 변경된 기존 파일 목록 + 변경 요약
   - 후속 이슈에 노출되는 공개 시그니처 (`build_value_series`, `compute_twr`, `compute_mwr`, `extract_cashflows`)
   - 후속 수동 작업 (예: OpenAPI 스펙 갱신 — `docs/api/*.yaml` 에 `/portfolio/performance` 추가가 필요한지 확인)

## 성공 기준

- [ ] 모든 체크리스트 항목 체크됨
- [ ] PRD G-4 fixture 3종 (단일매수 / 추가매수 / 부분매도) 모두 TWR · MWR 1bp 이내 일치
- [ ] PRD G-3 응답 p95 < 700ms — 100 종목 / 5년 fixture 로 직접 측정 (`pytest --durations=10`)
- [ ] `app/services/performance.py` 라인 커버리지 ≥ 90%
- [ ] mypy strict 통과 / ruff 통과
- [ ] 신규 외부 의존성 0 — `pyproject.toml` 의 `dependencies` 미변경 (uv.lock 도 미변경)
- [ ] 기존 테스트 (`tests/services/test_portfolio_history_service.py`, `tests/routers/test_portfolio_history_router.py` 등) 모두 그대로 통과 — 회귀 없음

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 수동 수정 후 agent 에게 전달해도 됩니다.
