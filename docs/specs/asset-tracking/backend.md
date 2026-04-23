---
feature: asset-tracking
role: backend
stack_type: python
stack_path: backend
created_at: 2026-04-23
status: Draft
related_prd: ../asset-tracking.md
related_api_contract: ../../api/asset-tracking.yaml
---

# asset-tracking — backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **backend 역할 구현 지시서**입니다.
> 대응 PRD: [`../asset-tracking.md`](../asset-tracking.md)
> 대응 스택: **python / FastAPI** (경로: `backend`)
> 전제된 Agent: `python-generator` · `python-modifier` · `python-tester`

---

## 0. 맥락 (반드시 먼저 읽기)

| 파일 | 목적 |
|------|------|
| `../asset-tracking.md` | PRD 본문 — 유저 스토리 · API 계약 · 비기능 요구 |
| `backend/CLAUDE.md` | 스택 규칙 (**MUST / NEVER**) — 모든 구현이 이 규칙을 통과해야 함 |
| `.claude/stacks.json` | monorepo 매니페스트 (`role: backend, path: backend`) |
| `.claude/skills/python-patterns.md` | 패턴 스킬 (agent 자동 로드) |
| `memory/MEMORY.md` | 프로젝트 히스토리 (hourly refresh 요구, uv 전환 검토 등) |

---

## 1. 목표

AssetLog MVP 의 서버 사이드 전부를 구현한다.

- **인증** (email + password, JWT access token)
- **자산·거래·심볼·시세** 도메인 REST API
- **외부 시세 어댑터** (yfinance / pykrx / fdr / ccxt) — Strategy 패턴
- **시간 단위 가격 갱신 스케줄러** (apscheduler / FastAPI lifespan)
- **포트폴리오 집계 쿼리** (총평가액 · 총손익 · 클래스별 비중)

---

## 2. 스택 전제 (backend/CLAUDE.md 와 일치)

| 영역 | 선정 |
|------|------|
| 프레임워크 | FastAPI |
| ORM | **SQLAlchemy 2.0 async** (`Mapped[...] = mapped_column(...)`) |
| Migration | **Alembic** (autogenerate) |
| 검증 | Pydantic v2 |
| 테스트 | pytest + httpx (AsyncClient) + `pytest-asyncio` |
| 패키지 관리 | **uv** (`pyproject.toml` + `uv.lock`) — 현재 `requirements.txt` 에서 전환 |
| 린트·타입 | ruff + mypy (strict) |
| DB | **MySQL** (driver: `asyncmy`) — 현 스캐폴드의 `sqlite+sync` 교체 |
| 스케줄러 | apscheduler `AsyncIOScheduler` |
| 인증 | passlib[bcrypt] + python-jose (JWT HS256) |

### 현 스캐폴드와의 Gap (반드시 먼저 해소)
현재 `backend/app/` 은 **sync SQLAlchemy + sqlite + User 없는 Holding** 초기 스캐폴드 상태.
- [ ] `core/database.py` 를 **async engine + async_sessionmaker** 로 교체
- [ ] `models/holding.py`, `models/price.py` 는 새 스키마(`UserAsset`, `PricePoint`)로 **대체**. 삭제 또는 이름 변경 후 재작성
- [ ] `requirements.txt` → `pyproject.toml` 로 전환 + `uv sync`
- [ ] `alembic/` 디렉토리 신규 초기화 (`uv run alembic init alembic`)

---

## 3. 데이터베이스 설정

### 3.1 MySQL 준비
- [ ] `docker-compose.yml` (프로젝트 루트) 에 MySQL 8 컨테이너 추가
  - DB 이름 예: `assetlog`, user `assetlog`, password `.env` 주입
  - timezone `+09:00` 설정(세션에서 `SET time_zone='+00:00'` 고정 권장 — UTC 저장)
- [ ] `backend/.env.example` 에 `DATABASE_URL=mysql+asyncmy://assetlog:...@localhost:3306/assetlog` 추가

### 3.2 엔진 & 세션
- [ ] `app/db/base.py` — `DeclarativeBase`
- [ ] `app/db/session.py` — `create_async_engine` + `async_sessionmaker(expire_on_commit=False)`
- [ ] `app/core/deps.py` — `get_db_session()` dependency (async generator, `async with session.begin():` 패턴)

### 3.3 Alembic
- [ ] `backend/alembic/` 초기화
- [ ] `alembic/env.py` 을 async 엔진에 맞게 수정 (`run_async_migrations` 패턴)
- [ ] `alembic.ini` 의 `sqlalchemy.url` 을 `settings.database_url` 에서 주입
- [ ] 초기 revision 1 개 생성: `V001_init_users_symbols_assets_transactions_prices`

> **NEVER**: 기존 Alembic revision 파일을 수정하지 않는다. 변경이 필요하면 **새 revision** 을 만든다.

---

## 4. 디렉토리 스캐폴드 (신규/변경 파일)

```
backend/
├── pyproject.toml                              # (신규) uv 전환
├── alembic.ini                                 # (신규)
├── alembic/                                    # (신규)
│   ├── env.py
│   └── versions/
│       └── 001_init_*.py
├── app/
│   ├── main.py                                 # (수정) async lifespan, 라우터 등록
│   ├── core/
│   │   ├── config.py                           # (수정) MySQL DATABASE_URL, JWT 설정
│   │   ├── security.py                         # (신규) password hash, JWT encode/decode
│   │   └── deps.py                             # (신규) get_db_session, get_current_user
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                             # (신규) DeclarativeBase
│   │   └── session.py                          # (신규) async engine / sessionmaker
│   ├── models/
│   │   ├── user.py                             # (신규)
│   │   ├── asset_symbol.py                     # (신규)
│   │   ├── user_asset.py                       # (신규)
│   │   ├── transaction.py                      # (신규)
│   │   └── price_point.py                      # (신규) 기존 price.py 대체
│   ├── schemas/
│   │   ├── auth.py                             # SignupRequest, LoginRequest, TokenResponse, UserResponse
│   │   ├── symbol.py                           # SymbolResponse, SymbolSearchQuery
│   │   ├── user_asset.py                       # UserAssetCreate, UserAssetResponse
│   │   ├── transaction.py                      # TransactionCreate, TransactionResponse
│   │   └── portfolio.py                        # PortfolioSummaryResponse, HoldingRow
│   ├── repositories/
│   │   ├── base.py                             # (선택) async CRUD 베이스
│   │   ├── user_repository.py
│   │   ├── asset_symbol_repository.py
│   │   ├── user_asset_repository.py
│   │   ├── transaction_repository.py
│   │   └── price_point_repository.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── symbol_service.py                   # 외부 어댑터 호출 + 캐시
│   │   ├── user_asset_service.py               # 평균단가 재계산
│   │   ├── transaction_service.py
│   │   ├── portfolio_service.py                # 집계 로직
│   │   └── price_refresh_service.py            # 스케줄러 job 본체
│   ├── routers/
│   │   ├── auth.py                             # /auth/signup, /auth/login, /auth/me
│   │   ├── symbols.py                          # /symbols (GET search, POST manual)
│   │   ├── user_assets.py                      # /user-assets CRUD
│   │   ├── transactions.py                     # 중첩 라우터 혹은 /user-assets/{id}/transactions
│   │   └── portfolio.py                        # /portfolio/summary, /portfolio/holdings
│   ├── adapters/
│   │   └── price/
│   │       ├── base.py                         # PriceAdapter 인터페이스 (async)
│   │       ├── yfinance_adapter.py             # us_stock
│   │       ├── pykrx_adapter.py                # kr_stock (primary)
│   │       ├── fdr_adapter.py                  # kr_stock (fallback)
│   │       ├── ccxt_adapter.py                 # crypto
│   │       └── registry.py                     # asset_type → adapter 라우팅
│   ├── scheduler/
│   │   ├── scheduler.py                        # AsyncIOScheduler 생성/lifespan 연결 (기존 파일 재사용 가능)
│   │   └── jobs.py                             # refresh_prices job
│   ├── exceptions.py                           # (신규) NotFoundError, ConflictError, AuthError, ExternalAdapterError
│   └── api/
│       └── router.py                           # (수정) 위 라우터 통합 등록
└── tests/
    ├── conftest.py                             # async test client, test DB fixture
    ├── fixtures/
    ├── repositories/
    │   ├── test_user_repository.py
    │   └── test_user_asset_repository.py
    ├── services/
    │   ├── test_auth_service.py
    │   ├── test_user_asset_service.py          # 평균단가 재계산 케이스
    │   ├── test_portfolio_service.py           # 집계 계산 케이스
    │   └── test_price_refresh_service.py       # adapter mock
    ├── routers/
    │   ├── test_auth.py
    │   ├── test_symbols.py
    │   ├── test_user_assets.py
    │   ├── test_transactions.py
    │   └── test_portfolio.py
    └── integration/
        └── test_full_flow.py                   # signup → asset add → price refresh → dashboard
```

---

## 5. REST API 엔드포인트 (최소 집합)

> 모든 경로는 `/api/v1` prefix. 인증 필요 엔드포인트는 `Authorization: Bearer <JWT>`. 응답은 **Pydantic v2 `*.model_validate(...)`** 로 ORM→Schema 변환 (**Schema ≠ Model** 원칙).

| 메서드 | 경로 | 핸들러 | 책임 |
|-------|------|--------|------|
| POST | `/auth/signup` | `routers/auth.signup` | 이메일 중복 검사 → bcrypt hash → User 저장 → `TokenResponse` 반환(자동 로그인) |
| POST | `/auth/login` | `routers/auth.login` | 비밀번호 검증 → JWT 발급 |
| GET | `/auth/me` | `routers/auth.me` | `Depends(get_current_user)` → `UserResponse` |
| GET | `/symbols?q=&type=` | `routers/symbols.search` | `SymbolService.search()` — 캐시 miss 시 외부 어댑터 |
| POST | `/symbols` | `routers/symbols.create` | 수동 등록 (fallback) |
| GET | `/user-assets` | `routers/user_assets.list` | 내 보유 자산 |
| POST | `/user-assets` | `routers/user_assets.create` | `UserAsset` 생성 + 최초 `Transaction` 동시 생성 |
| DELETE | `/user-assets/{id}` | `routers/user_assets.delete` | 소유자 검증 + soft delete(권장) |
| GET | `/user-assets/{id}/transactions` | `routers/transactions.list` | |
| POST | `/user-assets/{id}/transactions` | `routers/transactions.create` | BUY 만 허용 (MVP). `avg_cost` 가중평균 재계산 |
| GET | `/portfolio/summary` | `routers/portfolio.summary` | 통화별 총평가액/손익, 클래스별 비중, 마지막 갱신 시각 |
| GET | `/portfolio/holdings` | `routers/portfolio.holdings` | 행 단위 평가액·손익·비중 |

### 5.1 공통 라우터 요구사항 (backend/CLAUDE.md 재강조)
- 모든 Router 데코레이터에 `response_model=`, `summary=`, `responses=` 필수
- `dict` 반환 금지 — 반드시 Pydantic Schema
- Service 에서는 `fastapi.*` import 금지, `HTTPException` 대신 커스텀 예외 사용
- 예외 → HTTP 매핑은 `app/main.py` 의 `@app.exception_handler` 로 집중

---

## 6. 가격 소스 어댑터 (Strategy 패턴)

### 6.1 인터페이스
```
# app/adapters/price/base.py (설계 — 실제 코드는 python-generator 가 작성)
class PriceAdapter(Protocol):
    asset_type: str   # "kr_stock" | "us_stock" | "crypto"
    async def fetch_many(self, symbols: Sequence[str]) -> dict[str, PriceQuote]: ...
    async def fetch_one(self, symbol: str) -> PriceQuote | None: ...
```
- `PriceQuote` = dataclass/Pydantic: `price: Decimal`, `currency: str`, `fetched_at: datetime` (UTC)
- 실패 시 항목에서 해당 symbol 제외 (예외 전파 X, 로그 + `ExternalAdapterError` 선택적)

### 6.2 구현 순서 (우선순위)
1. `yfinance_adapter` (us_stock) — `yf.Tickers(...).tickers[sym].fast_info`
2. `pykrx_adapter` (kr_stock) — `stock.get_market_ohlcv_by_ticker(date, market='ALL')` bulk
3. `fdr_adapter` (kr_stock fallback) — 장외시간/휴장일 대응
4. `ccxt_adapter` (crypto) — 기본 `binance`, 사용자 자산 메타의 `exchange` 사용

### 6.3 라우팅
- [ ] `adapters/price/registry.py` 에 `get_adapter(asset_type: str) -> PriceAdapter` 팩토리
- [ ] yfinance · pykrx 는 **blocking** I/O → `asyncio.to_thread(...)` 로 비동기 래핑

---

## 7. 스케줄러

### 7.1 동작
- [ ] `AsyncIOScheduler` 를 `app/scheduler/scheduler.py` 에서 생성 (모듈 전역 X, factory 함수)
- [ ] FastAPI `lifespan` 에서 `scheduler.start()` / `shutdown()` 호출
- [ ] Job: `refresh_prices` — `CronTrigger(minute=0)` (매시 정각, KST)
- [ ] Job 본체는 `services/price_refresh_service.refresh_all()` 가 실행

### 7.2 Job 로직
```
1. AsyncSession 열기
2. asset_symbol 목록 조회 (distinct)
3. asset_type 별 그룹화 → adapter.fetch_many()
4. 성공 레코드 → PricePoint 삽입 (batch)
5. AssetSymbol.last_synced_at 갱신
6. 실패 목록은 warning 로그 (구조화 JSON)
7. Session commit
```
- [ ] 실패가 전체 실행을 중단하지 않도록 per-symbol try/except
- [ ] 실행 시간 / 성공·실패 건수 메트릭 로그 출력

### 7.3 제약
- MVP: **single-process** (`uvicorn --workers 1`) 전제. 다중 워커 배포 금지
- `manual trigger` 엔드포인트는 MVP 제외 (필요 시 v1.1)

---

## 8. 인증

### 8.1 요구
- [ ] `app/core/security.py`
  - `hash_password(plain: str) -> str` (bcrypt, rounds=12)
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(subject: str, expires_delta: timedelta | None = None) -> str`
  - `decode_token(token: str) -> TokenPayload` (Pydantic v2)
- [ ] JWT 설정: HS256, exp = **24 hours** (MVP). secret 은 `.env`
- [ ] `app/core/deps.py::get_current_user(token = Depends(OAuth2PasswordBearer(...)), session = Depends(get_db_session)) -> User`
  - 토큰 없음/만료/서명 오류 → `AuthError` → 401

### 8.2 라우트
- [ ] `POST /auth/signup` — 이메일 중복 시 `ConflictError` (409)
- [ ] `POST /auth/login` — `OAuth2PasswordRequestForm` 또는 JSON body(PRD 합의 필요 — **JSON body 권장**, FE 연동 쉬움)
- [ ] `GET /auth/me` — 200 + `UserResponse`

---

## 9. 테스트 요구

### 9.1 커버리지
- **라인 커버리지 ≥ 80%** (pre-push gate). 모든 Service · Router · Repository 에 테스트 필수 (CLAUDE.md).
- adapter 는 **mock** — 실제 외부 호출 금지 (pytest 시). `monkeypatch` 혹은 `respx` 활용.

### 9.2 레벨
| 레벨 | 위치 | 내용 |
|------|------|------|
| Repository | `tests/repositories/` | in-memory sqlite async 혹은 testcontainers MySQL |
| Service | `tests/services/` | Repository mock, 비즈니스 로직 단위 (평균단가 재계산·집계) |
| Router | `tests/routers/` | AsyncClient + `dependency_overrides` |
| Integration | `tests/integration/` | signup → asset add → (scheduler mock) → dashboard |

### 9.3 핵심 시나리오 (누락 없이 작성)
- [ ] 같은 심볼 BUY 2 회 → `avg_cost = (q1*p1 + q2*p2) / (q1+q2)` 검증
- [ ] `GET /portfolio/summary` — 통화별 분리 합계 검증 (KRW + USD + 코인)
- [ ] 타인 자산에 접근 시 404 (403 아닌 404 권장 — 존재 노출 회피)
- [ ] 가격 어댑터 1개 실패 시 나머지 asset_type 정상 갱신
- [ ] JWT 만료 → 401
- [ ] 이메일 중복 signup → 409

---

## 10. 작업 순서 (Step 1 → N)

> 한 스텝이 끝나면 `uv run pytest` + `uv run mypy .` + `uv run ruff check .` 통과 확인.

1. **[초기화]** `pyproject.toml`, `uv sync`, MySQL docker-compose, alembic init
2. **[DB]** `db/base.py`, `db/session.py`, `core/config.py` async 전환, `core/deps.py::get_db_session`
3. **[Auth 토대]** `core/security.py` + User 모델 + `auth_service` + `/auth/signup`, `/auth/login`, `/auth/me` + 테스트
4. **[심볼 마스터]** `AssetSymbol` 모델 + Repository + `SymbolService` (어댑터는 아직 mock) + `/symbols` 검색 라우터 + 테스트
5. **[자산·거래]** `UserAsset`, `Transaction` 모델 + Repository + `UserAssetService` (평균단가 재계산) + `/user-assets`, `/user-assets/{id}/transactions` + 테스트
6. **[Alembic revision]** 위 5 테이블 한꺼번에 `V001_init_*` autogenerate → 검수 → `upgrade head` 수동 동작 확인
7. **[Price Adapter 인터페이스]** `adapters/price/base.py` + `registry.py` + 인터페이스 테스트 (fake adapter)
8. **[Adapter 구현 순차]** yfinance → pykrx → fdr → ccxt. 각각 단위 테스트(실제 호출 X, 고정 픽스처)
9. **[Scheduler + PricePoint]** `PricePoint` 모델 + `price_refresh_service` + `scheduler/jobs.py` + `scheduler/scheduler.py` + lifespan 연결 + 테스트 (adapter mock)
10. **[Portfolio 집계]** `portfolio_service` 에 집계 쿼리 작성 — SQLAlchemy async + `select().join()` (raw SQL 금지). `/portfolio/summary`, `/portfolio/holdings` + 테스트
11. **[Integration]** 전 플로우 통합 테스트 + 커버리지 확인 (≥ 80%)
12. **[OpenAPI 검증]** FastAPI 자동 생성 `/openapi.json` 이 `docs/api/asset-tracking.yaml` 스펙과 엔드포인트·응답 필드 기준 일치하는지 확인

---

## 11. 다른 역할과의 계약 (→ frontend)

frontend 에게 제공하는 **응답 스키마 계약** (PRD 8. API 계약 · `docs/api/asset-tracking.yaml` 와 동일해야 함):

| 엔드포인트 | 응답 스키마 필드 |
|-----------|-----------------|
| `POST /auth/signup` · `POST /auth/login` | `{ access_token: str, token_type: "bearer", user: UserResponse }` |
| `GET /auth/me` | `UserResponse = { id, email, created_at }` |
| `GET /symbols?q=&type=` | `[{ id, asset_type, symbol, name, exchange, currency }]` |
| `POST /user-assets` | `UserAssetResponse = { id, asset_symbol: {…}, quantity, avg_cost, first_purchased_at, latest_price, latest_value, pnl_abs, pnl_pct, last_price_refreshed_at }` |
| `GET /portfolio/summary` | PRD §8 예시 JSON 참고 (통화별 분리) |
| `GET /portfolio/holdings` | 위 `UserAssetResponse` 의 배열 |

### 계약 변경 규칙
1. PRD `../asset-tracking.md` §8 **먼저 수정**
2. `docs/api/asset-tracking.yaml` 업데이트
3. `docs/specs/asset-tracking/frontend.md` 의 TypeScript 타입 동기화
4. 구현

---

## 12. 구현 제약 (backend/CLAUDE.md 재강조)

### MUST
- `Depends` 로만 DI — 모듈 전역 인스턴스 금지
- Service/Repository/Router 모두 `async def` — sync 혼용 금지 (blocking 외부 라이브러리는 `asyncio.to_thread`)
- Service 커스텀 예외 → Router/Handler 에서 `HTTPException` 변환
- 응답은 `SchemaResponse.model_validate(orm_obj)` — ORM 직접 반환 금지
- ORM 은 `Mapped[...] = mapped_column(...)`. 레거시 `Column(...)` 금지
- Pydantic v2: `model_config = ConfigDict(...)`, `@field_validator`
- Router 데코레이터에 `response_model`, `summary`, `responses` 필수
- 트랜잭션 경계는 `get_db_session` dependency 에서만 commit

### NEVER
- `models/` 에 비즈니스 로직 (Service 로 이동)
- `services/` 에서 `fastapi.*` / `HTTPException` import
- 기존 Alembic revision 수정 (**항상 새 revision**)
- raw SQL 문자열 하드코딩 (`text()` + 파라미터 바인딩 사용)
- `print()` 디버그 (`logging` 사용)
- 패스워드 · JWT · 이메일(평문) 로그 출력
- 테스트 없이 Service 메서드 추가
- `@pytest.mark.asyncio` 누락 (또는 `asyncio_mode = "auto"`)
- `# type: ignore` 사유 주석 없이 사용

---

## 13. 성공 기준

- [ ] PRD 의 US-1 ~ US-10 수락 기준을 백엔드 관점에서 모두 충족
- [ ] `/portfolio/summary`, `/portfolio/holdings` p95 < 500ms (100 종목 fixture)
- [ ] `refresh_prices` 1 사이클 < 5 분 (500 심볼 mock)
- [ ] `uv run pytest --cov=app` 라인 커버리지 ≥ 80%
- [ ] `uv run mypy .` + `uv run ruff check .` 무결점
- [ ] `uv run alembic upgrade head` 빈 DB 에서 성공
- [ ] `docker-compose up` 으로 MySQL + backend 기동 확인

---

## 14. 실행 지시 (agent 가 받으면)

1. `backend/CLAUDE.md` 먼저 정독
2. `../asset-tracking.md` PRD 정독 (특히 §7 데이터모델 · §8 API 계약)
3. `memory/MEMORY.md` 확인 (hourly refresh · Node 버전 참고)
4. 현재 스캐폴드(`backend/app/*`) 의 sync/sqlite 코드는 교체 대상 — §10 작업 순서 1 번부터 진행
5. 스텝마다 테스트 통과 후 다음 스텝 진행
6. 완료 시 요약 리포트: 생성·변경 파일 / 새 Alembic revision 이름 / frontend 에 공유할 스키마 변경사항 / 후속 수동 작업 (`uv sync`, `docker-compose up`, `alembic upgrade head`)

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 계약 변경은 반드시 PRD → YAML → 이 문서 순서로 업데이트하세요.
