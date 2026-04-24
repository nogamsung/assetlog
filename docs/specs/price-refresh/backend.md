# Price Refresh — Backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**입니다.
> 대응하는 PRD: [`../price-refresh.md`](../price-refresh.md)
> 대응하는 상위 PRD: [`../asset-tracking.md`](../asset-tracking.md)
> 대응하는 스택: **python / FastAPI** (경로: `backend/`)
> 대응하는 브랜치: `feature/price-refresh` (worktree `.worktrees/feature-price-refresh/`)

---

## 맥락 (꼭 읽을 것)

1. **이 슬라이스 PRD**: `docs/specs/price-refresh.md` — 특히 §6 (핵심 플로우), §9 (심볼 정규화 규칙), §10 (비기능 요구사항).
2. **상위 PRD**: `docs/specs/asset-tracking.md` §6.3 (가격 자동 갱신 플로우), §9 (외부 의존성), §11 (R-1~R-5).
3. **backend CLAUDE.md**: `backend/CLAUDE.md` — async 일관성, DI, Schema≠Model, 예외 정책, `text()` 원칙.
4. **기존 패턴 참고**:
   - `backend/app/main.py` — 기존 `lifespan` (scheduler 훅을 이 지점에 추가)
   - `backend/app/models/asset_symbol.py` — `last_price`, `last_price_refreshed_at` 컬럼 **이미 존재**
   - `backend/app/repositories/user_asset.py`, `backend/app/repositories/transaction.py` — AsyncSession 기반 Repository 패턴
   - `backend/app/services/portfolio.py` — Service 계층 스타일
   - `backend/app/domain/asset_type.py` — `AssetType` StrEnum (`KR_STOCK`, `US_STOCK`, `CRYPTO`)
   - `backend/pyproject.toml` — `apscheduler`, `yfinance`, `pykrx`, `finance-datareader`, `ccxt` **이미 포함됨** (확인 완료)
5. **MUST 숙지** — `backend/CLAUDE.md` MUST / NEVER 섹션.

## 입력 전제 (현재 상태)

- ✅ `AssetSymbol` 모델에 `last_price: Decimal | None`, `last_price_refreshed_at: datetime | None` 이미 존재.
- ✅ `app/scheduler/` 패키지 비어있음 (`__init__.py` 만 존재). 이 슬라이스에서 채움.
- ✅ `app/main.py` 의 `lifespan` 은 DB 헬스체크만 수행 중. 스케줄러 시작/종료 훅을 여기에 추가.
- ⚠️ `app/models/price.py` (또는 `price_point.py`) — **존재하지 않음**. 이 슬라이스에서 신규 추가 + Alembic migration 생성 필요.
- ⚠️ `app/adapters/` 디렉토리 — **존재하지 않음**. 신규 생성.
- ⚠️ Portfolio API 는 이미 `last_price` 를 읽어 응답 중. API 경로에서 외부 호출 금지 원칙(상위 PRD §4.2) 유지.

## 이 역할의 책임 범위

### 포함
- **Alembic migration 1개** — `price_points` 테이블 신설 (존재하지 않는 경우). FK `asset_symbol_id → asset_symbols.id`, 인덱스 `(asset_symbol_id, fetched_at DESC)`.
- **모델**: `app/models/price_point.py` (신규).
- **어댑터 계층** (신규 디렉토리 `app/adapters/`):
  - `app/adapters/__init__.py`
  - `app/adapters/base.py` — `PriceAdapter` Protocol + dataclass `SymbolRef`, `PriceQuote`, `FetchFailure`, `FetchBatchResult`.
  - `app/adapters/kr_stock.py` — pykrx 1차 + finance-datareader fallback.
  - `app/adapters/us_stock.py` — yfinance.
  - `app/adapters/crypto.py` — ccxt (binance 기본, upbit fallback).
  - `app/adapters/normalize.py` — 심볼 정규화 유틸 (PRD §9).
- **Repository**:
  - `app/repositories/asset_symbol.py` — `list_distinct_refresh_targets()`, `bulk_update_cache(rows)`.
  - `app/repositories/price_point.py` — `bulk_insert(quotes)`.
- **Service**:
  - `app/services/price_refresh.py` — `PriceRefreshService` + `async def refresh_all_prices() -> RefreshResult`.
- **Scheduler**:
  - `app/scheduler/__init__.py` — `build_scheduler(session_factory)`, `start_scheduler()`, `shutdown_scheduler()` 팩토리.
  - `app/scheduler/price_refresh_job.py` — `AsyncIOScheduler` 에 등록되는 wrapper coroutine.
- **Lifespan 통합**:
  - `app/main.py` (수정) — lifespan 에서 scheduler start/shutdown.
- **DI**:
  - `app/core/deps.py` (수정) — `PriceRefreshServiceDep`, `AssetSymbolRepositoryDep`, `PricePointRepositoryDep`, `AdapterRegistryDep`.
- **Tests**:
  - `backend/tests/adapters/test_kr_stock.py`, `test_us_stock.py`, `test_crypto.py`, `test_normalize.py`
  - `backend/tests/services/test_price_refresh.py`
  - `backend/tests/scheduler/test_lifespan.py`
  - 커버리지 ≥ 80% (새 모듈 내부 목표 100%).

### 제외
- 환율 변환 / 다중 통화 합산 (상위 PRD v2)
- 관리자 수동 트리거 REST 엔드포인트
- 분산 스케줄러 / leader election
- on-demand 초기 시세 fetch (자산 등록 직후)
- 재시도 백오프 전략
- 프론트엔드 변경 (`/portfolio/*` 계약 변화 없음)

## 변경할 / 생성할 파일 (체크리스트)

### Migration
- [ ] `backend/alembic/versions/{rev}_create_price_points_table.py`
  - `op.create_table('price_points', ...)`
    - `id: BigInteger primary key autoincrement`
    - `asset_symbol_id: Integer NOT NULL, FK → asset_symbols.id ON DELETE CASCADE`
    - `price: Numeric(20, 6) NOT NULL`
    - `currency: String(10) NOT NULL`
    - `fetched_at: DateTime(timezone=True) NOT NULL`
  - `op.create_index('ix_price_points_symbol_fetched', 'price_points', ['asset_symbol_id', sa.text('fetched_at DESC')])`
  - downgrade 는 역순 (`drop_index`, `drop_table`).

### Model
- [ ] `backend/app/models/price_point.py` (신규)
  - `Mapped[...] = mapped_column(...)` 스타일 (Column 단독 금지).
  - `asset_symbol_id` FK, `price: Decimal`, `currency: str`, `fetched_at: datetime` (tz-aware).
  - `__tablename__ = "price_points"`, `__table_args__` 에 인덱스 추가.

### Domain
- [ ] `backend/app/domain/price_refresh.py` (신규)
  - frozen dataclass `SymbolRef { asset_type: AssetType, symbol: str, exchange: str, asset_symbol_id: int }`
  - frozen dataclass `PriceQuote { ref: SymbolRef, price: Decimal, currency: str, fetched_at: datetime }`
  - frozen dataclass `FetchFailure { ref: SymbolRef, error_class: str, error_msg: str }`
  - frozen dataclass `FetchBatchResult { successes: list[PriceQuote], failures: list[FetchFailure] }`
  - frozen dataclass `RefreshResult { total: int, success: int, failed: int, elapsed_ms: int, failures: list[FetchFailure] }`

### Adapters (신규 `app/adapters/` 디렉토리)
- [ ] `backend/app/adapters/__init__.py` — `AdapterRegistry` (asset_type → PriceAdapter 인스턴스 매핑).
- [ ] `backend/app/adapters/base.py`
  - `class PriceAdapter(Protocol): asset_type: AssetType; async def fetch_batch(symbols: Sequence[SymbolRef]) -> FetchBatchResult`
  - 공통 유틸: `_wrap_failure(ref, exc) -> FetchFailure`.
- [ ] `backend/app/adapters/normalize.py`
  - `normalize_kr_stock_symbol(raw: str) -> str` — 6자리 zero-padded, 공백/대문자 제거.
  - `normalize_us_stock_symbol(raw: str) -> str` — upper() + strip.
  - `normalize_crypto_pair(raw: str, exchange: str) -> str` — `KRW-BTC` ↔ `BTC/KRW` 등 ccxt 포맷 통일 (PRD §9 규칙 테이블).
- [ ] `backend/app/adapters/kr_stock.py`
  - `class KrStockAdapter(PriceAdapter)`
  - `fetch_batch` — pykrx `get_market_ohlcv_by_ticker` / `get_market_ohlcv` 호출. 실패 시 `FinanceDataReader.DataReader(code)` fallback. 휴장일 → 최근 거래일 종가 반환.
  - 외부 호출은 **별도 스레드 풀** (`asyncio.to_thread`) — pykrx/FDR 은 sync 라이브러리.
- [ ] `backend/app/adapters/us_stock.py`
  - `class UsStockAdapter(PriceAdapter)`
  - yfinance `Ticker(symbol).fast_info["last_price"]` 또는 `history(period="1d")["Close"][-1]` 사용. sync → `asyncio.to_thread`.
  - 다수 심볼 bulk 조회: `yf.download(tickers, ...)` 활용 권장.
- [ ] `backend/app/adapters/crypto.py`
  - `class CryptoAdapter(PriceAdapter)`
  - 기본 거래소 `ccxt.async_support.binance()`, fallback `ccxt.async_support.upbit()`.
  - 심볼 정규화는 `normalize_crypto_pair` 경유.
  - 거래소별 rate limit 준수 — `enableRateLimit=True` 설정.

### Repository
- [ ] `backend/app/repositories/asset_symbol.py` (신규 또는 기존 존재 시 수정)
  - `async def list_distinct_refresh_targets() -> list[SymbolRef]` — distinct `(asset_type, exchange, symbol, id)` 조회. `AssetSymbol` 전량 순회 (참조하는 `UserAsset` 이 있는 심볼만 가도 무방 — 성능 최적화는 후속).
  - `async def bulk_update_cache(rows: Sequence[tuple[int, Decimal, datetime]]) -> int` — `id → (last_price, last_price_refreshed_at)` bulk update. `text()` 금지 — `update(AssetSymbol).where(...).values(...)` 또는 `session.execute(update_stmt)` per batch.
- [ ] `backend/app/repositories/price_point.py` (신규)
  - `async def bulk_insert(quotes: Sequence[PriceQuote]) -> int` — `session.add_all(...)` 또는 `session.execute(insert(PricePoint), [dict(...), ...])`.

### Service
- [ ] `backend/app/services/price_refresh.py` (신규)
  - ```python
    class PriceRefreshService:
        def __init__(
            self,
            asset_symbol_repo: AssetSymbolRepository,
            price_point_repo: PricePointRepository,
            adapters: AdapterRegistry,
            clock: Callable[[], datetime] = _utcnow,
        ) -> None: ...

        async def refresh_all_prices(self) -> RefreshResult: ...
    ```
  - 단계:
    1. `targets = await asset_symbol_repo.list_distinct_refresh_targets()`
    2. `by_type = groupby(targets, key=.asset_type)`
    3. `results = await asyncio.gather(*(self._run_adapter(t, refs) for t, refs in by_type.items()), return_exceptions=True)` — adapter 예외도 개별 실패로 변환.
    4. 성공 분 → `price_point_repo.bulk_insert(successes)` + `asset_symbol_repo.bulk_update_cache([...])`.
    5. 구조화 로그 + `RefreshResult` 반환.
  - **HTTPException / fastapi import 금지** (backend CLAUDE.md).
  - Decimal 유지, float 혼용 금지.

### Scheduler
- [ ] `backend/app/scheduler/__init__.py` (수정 — 현재 빈 파일)
  - ```python
    def build_scheduler(
        session_factory: async_sessionmaker[AsyncSession],
        adapters: AdapterRegistry,
    ) -> AsyncIOScheduler: ...
    ```
  - `AsyncIOScheduler(timezone="Asia/Seoul")` 생성, `CronTrigger(minute=0)` 로 `price_refresh_job` 등록 (`id="price_refresh_hourly"`, `max_instances=1`, `coalesce=True`, `misfire_grace_time=60`).
- [ ] `backend/app/scheduler/price_refresh_job.py` (신규)
  - ```python
    async def price_refresh_job(
        session_factory: async_sessionmaker[AsyncSession],
        adapters: AdapterRegistry,
    ) -> RefreshResult:
        async with session_factory() as session:
            service = PriceRefreshService(
                asset_symbol_repo=AssetSymbolRepository(session),
                price_point_repo=PricePointRepository(session),
                adapters=adapters,
            )
            result = await service.refresh_all_prices()
            await session.commit()
            return result
    ```
  - 구조화 로그는 service 내부에서 수행.

### Lifespan 통합
- [ ] `backend/app/main.py` (수정) — 의사코드:
  ```python
  @asynccontextmanager
  async def lifespan(_: FastAPI):
      logger.info("Starting up AssetLog API...")
      session_factory = _make_session_factory(settings.database_url)
      # DB 헬스체크 (기존)
      ...
      # 스케줄러 start
      adapters = build_default_adapter_registry()
      scheduler = build_scheduler(session_factory, adapters)
      scheduler.start()
      logger.info("price_refresh scheduler started (Asia/Seoul, every hour :00)")
      try:
          yield
      finally:
          scheduler.shutdown(wait=False)
          logger.info("price_refresh scheduler stopped")
  ```
  - `settings.enable_scheduler: bool = True` 환경변수 게이트 — 테스트/로컬에서 비활성화 가능 (`app/core/config.py` 에 필드 추가).

### DI
- [ ] `backend/app/core/deps.py` (수정)
  - `AssetSymbolRepositoryDep`, `PricePointRepositoryDep`, `PriceRefreshServiceDep` factory 추가. (테스트에서 override 가능하도록.)

### Tests
- [ ] `backend/tests/adapters/test_normalize.py`
  - 한국 주식 6자리 zero-pad (`'5930'` → `'005930'`).
  - 미국 주식 upper/strip (`' aapl '` → `'AAPL'`).
  - crypto `'KRW-BTC'` → `'BTC/KRW'`, `'BTC/USDT'` → `'BTC/USDT'` (idempotent).
- [ ] `backend/tests/adapters/test_kr_stock.py`
  - `pykrx.stock.get_market_ohlcv_by_ticker` monkeypatch → 가격 반환 확인.
  - pykrx raise → FDR fallback 호출 검증.
  - 장외시간 → 최근 거래일 종가 반환 검증 (mock 으로).
- [ ] `backend/tests/adapters/test_us_stock.py`
  - `yfinance.download` monkeypatch (DataFrame 모킹). 실제 네트워크 호출 없음.
- [ ] `backend/tests/adapters/test_crypto.py`
  - `ccxt.async_support.binance.fetch_tickers` 모킹. upbit fallback 검증.
- [ ] `backend/tests/services/test_price_refresh.py`
  - 10 종목 픽스처 (asset_type 3종 혼합). adapter 전부 모킹 → 성공 7건 / 실패 3건 시나리오.
  - `AssetSymbol.last_price` 갱신 건수 = 7.
  - `PricePoint` insert 건수 = 7.
  - 실패 3건은 `last_price` 미갱신 + warning 로그 (caplog 확인).
  - `RefreshResult { total=10, success=7, failed=3 }` 반환 검증.
  - Decimal precision 유지 (float 혼용 없음).
- [ ] `backend/tests/scheduler/test_lifespan.py`
  - FastAPI `TestClient` / `httpx.AsyncClient` 로 앱 기동 → scheduler 가 running 상태 확인 → shutdown 호출 확인.
  - **실제 cron 대기 금지** — `scheduler.get_jobs()` 로 등록 사실만 확인.
  - `settings.enable_scheduler=False` 시 스케줄러 start 생략 검증.
- [ ] `uv run pytest --cov=app` 전체 커버리지 ≥ 80%, 새 모듈 목표 100%.

## 구현 제약 (backend/CLAUDE.md 충돌 금지)

- **async 일관성** — Service / Repository / job / adapter 전부 `async def`. sync 라이브러리 호출은 `asyncio.to_thread(...)` 로 오프로드.
- **DI** — 모듈 전역 인스턴스 금지. `AdapterRegistry` 는 lifespan 에서 1회 생성 → `Depends` 로 주입.
- **Schema ≠ Model** — 본 슬라이스는 외부 응답 엔드포인트 없음. 내부 dataclass 는 **Pydantic 이 아닌 `dataclass(frozen=True)`** 로 표현 가능.
- **예외** — Service / adapter 에서 `HTTPException`, `fastapi.*` import 금지.
- **ORM** — `Mapped[...] = mapped_column(...)` 필수. `Column(...)` 단독 금지.
- **raw SQL 금지** — `text()` 없이 `update(...)`, `insert(...)`, `select(...)` 표현식만. distinct 조회는 `select(...).distinct()`.
- **logging** — `print()` 금지. `logger = logging.getLogger("app.scheduler.price_refresh")`. structured 는 `extra={"event": "...", ...}` 사용.
- **PII 로그 금지** — email, 비밀번호, 토큰 로깅 금지. 심볼·거래소·에러 클래스만.
- **Alembic** — 기존 revision 파일 **수정 금지**. 항상 신규 revision (`alembic revision --autogenerate` 사용 권장 후 수동 검증).
- **테스트 없는 Service/adapter 추가 금지** — 각 public 메서드 1 테스트 이상.
- **단일 프로세스 가정** — uvicorn `--workers 1`. `docker-compose.yml` / README 에 명시 (필요 시 업데이트).
- **mypy strict 통과** — `type: ignore` 는 이유 주석 필수.

## 주요 함수 시그니처 초안

```python
# app/adapters/base.py
from typing import Protocol, Sequence
from app.domain.asset_type import AssetType
from app.domain.price_refresh import SymbolRef, FetchBatchResult


class PriceAdapter(Protocol):
    asset_type: AssetType

    async def fetch_batch(
        self,
        symbols: Sequence[SymbolRef],
    ) -> FetchBatchResult:
        ...


# app/adapters/__init__.py
class AdapterRegistry:
    def __init__(self, adapters: dict[AssetType, PriceAdapter]) -> None: ...
    def get(self, asset_type: AssetType) -> PriceAdapter: ...


def build_default_adapter_registry() -> AdapterRegistry:
    return AdapterRegistry({
        AssetType.KR_STOCK: KrStockAdapter(),
        AssetType.US_STOCK: UsStockAdapter(),
        AssetType.CRYPTO: CryptoAdapter(),
    })


# app/services/price_refresh.py
async def refresh_all_prices(self) -> RefreshResult: ...


# app/scheduler/__init__.py
def build_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    adapters: AdapterRegistry,
) -> AsyncIOScheduler: ...
```

### apscheduler lifespan 연동 의사코드

```python
# app/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.adapters import build_default_adapter_registry
from app.scheduler.price_refresh_job import price_refresh_job


@asynccontextmanager
async def lifespan(_: FastAPI):
    session_factory = _make_session_factory(settings.database_url)
    # ... 기존 DB 헬스체크 ...

    scheduler: AsyncIOScheduler | None = None
    if settings.enable_scheduler:
        adapters = build_default_adapter_registry()
        scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        scheduler.add_job(
            price_refresh_job,
            trigger=CronTrigger(minute=0),
            kwargs={"session_factory": session_factory, "adapters": adapters},
            id="price_refresh_hourly",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
            replace_existing=True,
        )
        scheduler.start()
        logger.info("price_refresh scheduler started")

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info("price_refresh scheduler stopped")
```

## 심볼 정규화 규칙 (PRD §9 재게시)

| asset_type | exchange 예 | DB `symbol` | adapter 호출 포맷 | 변환 규칙 |
|-----------|------------|-------------|--------------------|-----------|
| `kr_stock` | `KRX` | `005930` (6자리 zero-pad) | pykrx: `005930`, FDR: `005930` | `symbol.strip().zfill(6)` — 6자리 숫자 강제 |
| `us_stock` | `NASDAQ` / `NYSE` | `AAPL`, `VOO` | yfinance: `AAPL` | `symbol.strip().upper()` |
| `crypto` | `binance` | `BTC/USDT` | ccxt binance: `BTC/USDT` | ccxt 표준 (대문자, `/` 구분) |
| `crypto` | `upbit` | `BTC/KRW` | ccxt upbit: `BTC/KRW` | `KRW-BTC` 입력 시 `BTC/KRW` 로 변환 (legacy accept) |

**구현**: `app/adapters/normalize.py` 에 순수 함수 + 단위 테스트.

## 다른 역할과의 계약 (Interface)

이 슬라이스는 **외부 API 계약 변경 없음**. Portfolio API (`/api/portfolio/summary`, `/holdings`) 의 `last_price_refreshed_at` 값이 **자동으로 채워지게 되는 행위 변화**만 있음. frontend 프롬프트 변경 불필요.

내부 인터페이스:
- `PriceAdapter` Protocol — 새 거래소·자산 클래스 추가 시 구현체만 등록 (AdapterRegistry 주입).
- `RefreshResult` — 향후 `/admin/refresh-prices` 엔드포인트에서 반환 포맷으로 재사용 가능.

### 계약 변경 절차 (변경 발생 시)
1. PRD `docs/specs/price-refresh.md` 업데이트
2. 상위 PRD `docs/specs/asset-tracking.md` 연관 섹션 (§6.3 등) 업데이트
3. 본 프롬프트 업데이트

## 실행 지시

구현 순서:

1. `backend/CLAUDE.md` 재확인 → MUST / NEVER 숙지
2. `backend/app/main.py`, `backend/app/models/asset_symbol.py`, `backend/app/services/portfolio.py`, `backend/app/core/deps.py` 를 읽고 기존 패턴 흡수
3. **확인**: `backend/app/models/price_point.py` 존재 여부 — 없으면 신규 생성 + migration
4. 생성 순서:
   1. Migration (`price_points`) → `uv run alembic upgrade head` 로 적용 가능성 확인
   2. Model (`price_point.py`)
   3. Domain dataclass (`domain/price_refresh.py`)
   4. Adapter base + normalize → 단위 테스트
   5. 각 adapter (kr_stock / us_stock / crypto) → 단위 테스트 (외부 호출 전부 mock)
   6. Repository (asset_symbol / price_point)
   7. Service (`services/price_refresh.py`) → 서비스 단위 테스트
   8. Scheduler (`scheduler/__init__.py` + `price_refresh_job.py`)
   9. Lifespan 통합 (`main.py`) + config 에 `enable_scheduler` 플래그
   10. DI 갱신 (`deps.py`)
   11. Lifespan 테스트 (실제 cron 대기 금지)
5. 품질 게이트:
   - `uv run alembic upgrade head` 성공
   - `uv run ruff check . && uv run ruff format --check .` 0 warning
   - `uv run mypy .` 0 error
   - `uv run pytest --cov=app` 커버리지 ≥ 80%
6. 리포트:
   - 생성 파일 목록
   - 변경 파일 목록 (`main.py`, `core/config.py`, `core/deps.py`, `scheduler/__init__.py`)
   - 후속 수동 작업: `uv run alembic upgrade head` (local DB)
   - 운영 주의사항: uvicorn `--workers 1` 고정 필수 (중복 실행 방지)

## 성공 기준

- [ ] 모든 체크리스트 항목 체크됨
- [ ] `uv run pytest --cov=app` 커버리지 ≥ 80% (새 모듈 100% 목표)
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` 모두 0 warning/error
- [ ] `backend/CLAUDE.md` NEVER 항목 위반 없음 (HTTPException 경계, async 일관성, raw SQL 금지 등)
- [ ] 테스트는 **네트워크 호출 없이** 실행 가능 (pykrx/yfinance/ccxt 전부 모킹)
- [ ] 앱 기동 시 scheduler 가 정상 start, 종료 시 shutdown 되는 것이 로그로 검증
- [ ] 10 종목 중 3 종목 실패 시나리오에서 나머지 7 종목이 정상 갱신되는 실패 격리 검증 테스트 통과

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 실제 구현은 `python-generator` / `python-modifier` / `python-tester` agent 를 통해 진행하세요.
