# symbol-search — backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **backend 전용 구현 지시서** 입니다.
> 대응하는 PRD: [`../symbol-search.md`](../symbol-search.md)
> 상위 PRD: [`../asset-tracking.md`](../asset-tracking.md) (US-2/3/4 수락 기준 상속)
> 스택: python (FastAPI) · 경로: `backend/`
> 브랜치: `feature/symbol-search`

---

## 맥락 (꼭 읽을 것)

- PRD 본문: `../symbol-search.md` — 오픈 이슈 중 `last_synced_at` 컬럼 존재 여부는 **이 작업 0단계에서 확인**
- 이 역할의 CLAUDE.md: `backend/CLAUDE.md` — **async 일관성**, **Depends DI**, **services 에서 fastapi import 금지**, **Schema ≠ Model**, **mypy strict**
- 스택 매니페스트: `.claude/stacks.json` (python)
- 관련 패턴 스킬: `.claude/skills/python-patterns.md`
- 기존 어댑터: `backend/app/adapters/{base,kr_stock,us_stock,crypto,normalize}.py` — 현재는 `fetch_batch` 만 존재
- 기존 서비스: `backend/app/services/symbol.py`
- 기존 리포지토리: `backend/app/repositories/asset_symbol.py`
- 기존 라우터: `backend/app/routers/symbol.py`

## 이 역할의 책임 범위

### 포함
1. 어댑터 프로토콜에 **`search_symbols`** 추가 + kr/us/crypto 각 구현
2. 어댑터별 심볼 리스트 **메모리 캐시 (TTL 24h, asyncio.Lock 기반 single-flight)**
3. `AssetSymbolRepository.upsert_many(...)` 추가 (ON DUPLICATE KEY UPDATE / ON CONFLICT DO UPDATE)
4. `SymbolService.search(...)` 파이프라인 개편 — DB hits → 부족 시 adapter fallback → upsert → 병합
5. `/api/symbols` 라우터: 시그니처 유지, 내부 파이프라인만 변경 (최소 침습)
6. `AdapterRegistry` 또는 `core/deps.py` 의 어댑터 레지스트리 — `asset_type → search-capable adapter`
7. 단위 테스트 (`tests/adapters`, `tests/services`, `tests/repositories`, `tests/routers`) — 외부 라이브러리 전부 모킹, 커버리지 ≥ 80%

### 제외
- 가격 즉시 조회 (on-demand fetch) — PRD 비목표
- 전체 심볼 사전 동기화 배치 — PRD 비목표
- 검색 랭킹/relevance 정렬 — PRD 비목표
- 프론트엔드 변경 — 없음
- 기존 `fetch_batch` 로직 변경 — 금지 (스코프 외)

## 변경할/생성할 파일 (체크리스트)

### 0단계 — 전제 확인
- [ ] `backend/app/models/asset_symbol.py` 에 `last_synced_at: Mapped[datetime] = mapped_column(...)` 존재 여부 확인
  - **없으면**: `alembic revision --autogenerate -m "add last_synced_at to asset_symbols"` 로 신규 revision. 기존 revision 수정 금지.
  - **있으면**: 스킵

### 1단계 — 도메인 / 어댑터 프로토콜
- [ ] `backend/app/domain/symbol_search.py` **신규**
  - `@dataclass(frozen=True) class SymbolCandidate` — 필드: `asset_type: AssetType`, `symbol: str`, `name: str`, `exchange: str`, `currency: str`
- [ ] `backend/app/adapters/base.py` **수정**
  - `PriceAdapter` Protocol 에 추가:
    ```python
    async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]: ...
    ```
  - Protocol 이름을 `PriceAdapter` 그대로 유지하거나 `SymbolAdapter` 를 별도 Protocol 로 분리 중 택일 (후자 권장 — 단일 책임).
  - 권장: `class SymbolSearchAdapter(Protocol)` 신규 + 각 어댑터 클래스가 두 Protocol 모두 만족.

### 2단계 — 어댑터 구현

#### 공통: 어댑터 내부 캐시 구조
- [ ] `backend/app/adapters/_symbol_cache.py` **신규**
  - `class SymbolListCache` — generic 메모리 캐시.
    - `__init__(ttl_seconds: float = 86400)`
    - `async def get_or_load(self, loader: Callable[[], Awaitable[list[SymbolCandidate]]]) -> list[SymbolCandidate]` — `asyncio.Lock` 으로 single-flight
    - `def invalidate() -> None`
    - 시계는 `time.monotonic()` — 테스트에서 주입 가능하도록 `now: Callable[[], float] = time.monotonic` 파라미터
  - 캐시는 어댑터 인스턴스 속성으로 보유 (lifespan 단일 인스턴스 가정)

#### kr_stock
- [ ] `backend/app/adapters/kr_stock.py` **수정**
  - `_load_symbol_list_sync() -> list[SymbolCandidate]`:
    - `pykrx.stock.get_market_ticker_list(market="ALL")` → 종목코드 목록
    - 각 코드에 대해 `pykrx.stock.get_market_ticker_name(code)` → 이름
    - 실패 시 `finance-datareader` 의 `fdr.StockListing("KRX")` fallback (코드·이름 추출)
    - 반환: `SymbolCandidate(asset_type=KR_STOCK, symbol=<6자리 zfill>, name=<name>, exchange="KRX", currency="KRW")`
  - `async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]`:
    - `norm = normalize_kr_stock_symbol(query)` 와 원문 `query.strip()` 둘 다 유지
    - 캐시에서 리스트 로드 (`asyncio.to_thread(_load_symbol_list_sync)`)
    - exact symbol match 우선, 그 다음 symbol prefix, 그 다음 name `contains` (ko/en 대소문자 무관)
    - 상위 `limit` 개 반환

#### us_stock
- [ ] `backend/app/adapters/us_stock.py` **수정**
  - MVP 전략: **exact-match info 조회**
  - `async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]`:
    - `norm = normalize_us_stock_symbol(query)`
    - 캐시 확인: `(norm → SymbolCandidate | MISSING)` mapping
    - 미확인 시 `asyncio.to_thread(_fetch_info_sync, norm)`:
      - `yf.Ticker(norm).info` → `shortName` / `longName`, `exchange`, `currency`
      - 매칭 실패·필드 누락 → `None`
    - 결과를 캐시(positive + negative)에 저장 (TTL 24h)
    - exchange 는 info 의 `exchange` (예: `NMS`, `NYQ`) 를 그대로 쓰거나 정규화(`NASDAQ`/`NYSE`) — **정규화 맵을 `normalize.py` 에 추가**
    - `currency` 누락 시 `USD` 기본값
    - 반환: 최대 1건 (또는 빈 리스트)
  - **주의**: 후보 N개 반환 불가 — PRD 에서 허용됨. 로그에 `us_stock_search_exact_only` 이벤트 남김.

#### crypto
- [ ] `backend/app/adapters/crypto.py` **수정**
  - `async def _load_markets_sync(exchange_name: str = "binance") -> list[SymbolCandidate]`:
    - `ccxt.async_support.<exchange>().load_markets()` → `{symbol: market_info}`
    - 각 market 에 대해 `SymbolCandidate(asset_type=CRYPTO, symbol=<"BTC/USDT">, name=<base 또는 market['baseName'] 가 있으면>, exchange="binance", currency=<quote>)`
  - `async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]`:
    - `norm = normalize_crypto_pair(query, exchange="binance")` (exchange 인자 매칭)
    - 캐시에서 전체 리스트 로드 (single-flight)
    - `norm` 이 `/` 포함 → exact 우선
    - 포함 안 함 → `BASE` prefix 매칭 (예: `BTC` → `BTC/USDT`, `BTC/BUSD`, ...)
    - 상위 `limit` 개 반환

### 3단계 — normalize 보강 (필요 시)
- [ ] `backend/app/adapters/normalize.py` **수정**
  - `def normalize_us_exchange_code(raw: str) -> str` 추가 — `"NMS" → "NASDAQ"`, `"NYQ" → "NYSE"`, 기타는 upper 원문
  - 기존 함수 시그니처 변경 금지 (호출처 영향 최소화)

### 4단계 — 리포지토리 upsert
- [ ] `backend/app/repositories/asset_symbol.py` **수정**
  - 메서드 추가:
    ```python
    async def upsert_many(
        self,
        candidates: Sequence[SymbolCandidate],
        *,
        now: datetime,
    ) -> list[AssetSymbol]:
        """Insert or update-on-conflict (asset_type, symbol, exchange).

        On match → UPDATE name, currency, last_synced_at.
        On insert → set last_synced_at = now.
        Returns the persisted rows in input order.
        """
    ```
  - MySQL(asyncmy): `from sqlalchemy.dialects.mysql import insert as mysql_insert` + `.on_duplicate_key_update(...)`.
  - SQLite 테스트 경로: `from sqlalchemy.dialects.sqlite import insert as sqlite_insert` + `.on_conflict_do_update(index_elements=[...], set_=...)`.
  - dialect 분기 — `self._session.bind.dialect.name` (또는 Engine 조회). dialect 분기 유틸을 `repositories/_dialect.py` 로 분리 권장.
  - insert 후 `select(...).where(tuple in)` 으로 refetch 하여 ORM 인스턴스 반환.

### 5단계 — 서비스 파이프라인
- [ ] `backend/app/services/symbol.py` **수정**
  - `SymbolService.__init__` 시그니처 확장: `adapters: Mapping[AssetType, SymbolSearchAdapter]` 주입 (DI).
  - `async def search(...)` 로직:
    1. `db_hits = await self._repo.search(q, asset_type, exchange, limit, offset)`
    2. `if not q or not q.strip() or asset_type is None: return db_hits`
    3. `remaining = max(0, limit - len(db_hits))`
    4. `if remaining == 0: return db_hits`
    5. `adapter = self._adapters.get(asset_type)` — 없으면 `return db_hits`
    6. `try: candidates = await adapter.search_symbols(q.strip(), limit=remaining * 2) except Exception: candidates = []` — 로그는 `warning`, re-raise 금지
    7. 중복 제거 키 `(asset_type, symbol, exchange)` 로 db_hits 에 없는 신규만 필터
    8. `persisted = await self._repo.upsert_many(new_candidates, now=datetime.now(UTC))`
    9. `merged = db_hits + [p for p in persisted if (p.asset_type, p.symbol, p.exchange) not in seen]`
    10. `return merged[:limit]`
  - **예외 정책**: 어댑터 실패는 graceful degrade. `ConflictError`/`NotFoundError` 와 별개.

### 6단계 — DI 배선
- [ ] `backend/app/core/deps.py` **수정**
  - `@lru_cache` 또는 `lifespan` 기반으로 어댑터 싱글톤 생성 (인스턴스별 캐시 보존 목적)
  - `SymbolServiceDep` 가 adapter registry 를 함께 주입하도록 업데이트
  - 모듈 전역 인스턴스 금지 (CLAUDE.md) — `Depends` 로 fan-out

### 7단계 — 라우터
- [ ] `backend/app/routers/symbol.py` **수정**
  - 엔드포인트 시그니처·쿼리 파라미터 **변경 없음**
  - `response_model`, `responses`, `summary` 유지
  - 문서 업데이트: docstring 에 "DB 우선 + 외부 fallback" 동작 명시

### 8단계 — 테스트 (커버리지 ≥ 80%)

#### 단위
- [ ] `backend/tests/adapters/test_symbol_cache.py` — TTL 만료·single-flight·invalidate (monotonic clock 모킹)
- [ ] `backend/tests/adapters/test_kr_stock_search.py`
  - `monkeypatch` 로 `pykrx.stock.get_market_ticker_list` / `get_market_ticker_name` 모킹
  - `005930` / `5930` / `삼성` / `samsung` 쿼리 검증
  - pykrx 예외 시 FDR fallback 경로
- [ ] `backend/tests/adapters/test_us_stock_search.py`
  - `yf.Ticker.info` 모킹 (`{"shortName": "Apple Inc.", "exchange": "NMS", "currency": "USD"}`)
  - exact match / 미매칭 빈 리스트 / info 예외 처리
  - `normalize_us_exchange_code` 통합
- [ ] `backend/tests/adapters/test_crypto_search.py`
  - `ccxt.async_support.binance().load_markets()` 모킹 (dict 반환)
  - `BTC` → N개 후보 / `BTC/USDT` → exact 우선 / exchange 예외 처리

#### 리포지토리
- [ ] `backend/tests/repositories/test_asset_symbol_upsert.py`
  - SQLite in-memory: insert 경로, 중복 시 update 경로, 순서 유지 검증

#### 서비스
- [ ] `backend/tests/services/test_symbol_search_pipeline.py`
  - DB hits 충분 → 어댑터 호출 0회 (fake adapter 호출 카운터)
  - DB hits 부족 + asset_type 있음 → 어댑터 호출 1회 + upsert 발생
  - `q` 빈 값 → 어댑터 호출 0회
  - `asset_type` 없음 → 어댑터 호출 0회
  - 어댑터 예외 주입 → 엔드포인트 정상, DB hits 만 반환

#### 라우터 (integration)
- [ ] `backend/tests/routers/test_symbol_search_endpoint.py`
  - `GET /api/symbols?q=AAPL&asset_type=us_stock` → 200, shape 검증 (US-2)
  - `GET /api/symbols?q=005930&asset_type=kr_stock` → 200 + `name="삼성전자"` (US-3)
  - `GET /api/symbols?q=BTC&asset_type=crypto` → 200 + `BTC/USDT` 포함 (US-4)
  - `GET /api/symbols?q=AAPL` (asset_type 미지정) → DB hits 만 (외부 호출 0회)
  - 2회차 호출 → 외부 호출 0회 (캐시 + DB hit)
  - 외부 예외 주입 시 200 + 부분 결과

## 구현 제약 (backend/CLAUDE.md 우선)

- **services/ 에서 `fastapi.*` / `HTTPException` import 금지** — 어댑터 실패도 커스텀 예외(또는 graceful return)로 처리
- **async 일관성** — 모든 신규 public 메서드 `async def`. 어댑터 내부 sync 라이브러리 호출은 `asyncio.to_thread` 로만
- **Schema ≠ Model** — 라우터는 `AssetSymbolResponse.model_validate(...)` 유지. Service 가 ORM 반환해도 router 에서 변환
- **Depends DI** — 어댑터 레지스트리는 `core/deps.py` 의 Depends 로 주입. 모듈 전역 인스턴스 금지
- **기존 Alembic revision 수정 금지** — 0단계에서 추가 필요 시 새 revision
- **`# type: ignore`** 사용 시 사유 주석 필수
- **로깅** — `print` 금지. 토큰·PII 로깅 금지. 외부 응답 raw echo 금지

## 계약 (다른 역할에 알릴 사항)

- **엔드포인트 시그니처 변경 없음** — frontend 측 변경 불필요
- **응답 스키마(`AssetSymbolResponse`) 변경 없음**
- 내부적으로 `last_synced_at` 이 갱신될 수 있음 — 현재 응답에는 미노출. 노출 필요 시 상위 PRD 의 API 계약 업데이트 먼저.

## 실행 지시

1. `backend/CLAUDE.md` 먼저 읽어 스택 규칙 숙지
2. 0단계 — `last_synced_at` 컬럼 확인. 없으면 Alembic revision 생성
3. 위 체크리스트 순서대로 구현 (domain → adapter base → 각 adapter → normalize → repository → service → deps → router → tests)
4. 각 단계 후 `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest --cov=app` 로 검증
5. 완료 리포트:
   - 생성/변경 파일 목록
   - 추가된 Alembic revision (있는 경우)
   - 외부 라이브러리 API 호출부 모킹 포인트 (후속 테스트에서 재사용)
   - 오픈 이슈 갱신 사항 (PRD 의 `[ ]` 항목 상태)

## 성공 기준

- [ ] 체크리스트 전 항목 체크됨
- [ ] `uv run pytest --cov=app` 통과, 라인 커버리지 ≥ 80%
- [ ] `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy .` 통과
- [ ] `/api/symbols` 엔드포인트 시그니처·응답 스키마 변경 없음
- [ ] 외부 라이브러리 전부 모킹된 상태에서 e2e 3종(US-S1/S2/S3) 통과
- [ ] 어댑터 실패 주입 테스트에서 엔드포인트 200 유지 (US-S5)

---

> `/new backend` 로 개별 파일 생성 시 이 프롬프트의 해당 섹션을 컨텍스트로 넘길 것.
