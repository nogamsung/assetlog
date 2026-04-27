# cash-holdings — backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **backend 역할용 구현 지시서** 입니다.
> 대응하는 PRD: [`../cash-holdings.md`](../cash-holdings.md)
> 대상 스택: **python (FastAPI)** — 경로 `backend/`
> Agent: `python-generator` (신규 파일) · `python-modifier` (기존 파일 수정)

---

## 0. 사전 필독

1. `backend/CLAUDE.md` — MUST / NEVER 우선. 특히:
   - **services 에서 `fastapi.*` import 금지**, `HTTPException` 직접 raise 금지 → 커스텀 예외 (`NotFoundError`, `ValidationError`) 전파
   - **DI 는 FastAPI `Depends` 만**, 모듈 전역 인스턴스 금지
   - **ORM 은 `Mapped[...] = mapped_column(...)`**, `Column(...)` 단독 금지
   - **Schema ≠ Model** — 응답에 `SchemaResponse.model_validate(...)` 필수
   - **기존 Alembic revision 수정 금지** — 항상 신규 revision
   - **모든 라우터 메타** (`response_model`, `responses`, `summary`) 필수, dict 반환 금지
   - **타입 힌트** 모든 public 함수 (mypy strict)
2. PRD `docs/specs/cash-holdings.md` §7 (데이터 모델), §8 (API 계약) 정독 — 이것이 단일 진실
3. 기존 단순 CRUD 라우터 패턴 참고: `app/routers/user_asset.py`, `app/services/user_asset.py`, `app/repositories/user_asset.py`
4. 기존 owner 인증 의존성: `app/core/deps.py` 의 `CurrentUser`

## 1. 책임 범위

**포함**
- `cash_accounts` 테이블 신규 Alembic revision
- `CashAccount` 모델 (`app/models/cash_account.py`)
- Pydantic 스키마 (`app/schemas/cash_account.py`) — Create / Update / Response
- Repository (`app/repositories/cash_account.py`) — async CRUD
- Service (`app/services/cash_account.py`) — 비즈니스 로직 + 커스텀 예외
- Router (`app/routers/cash_account.py`) — REST 엔드포인트, OpenAPI 메타
- `app/core/deps.py` — `CashAccountServiceDep` 추가
- `app/main.py` — `cash_account_router` 등록
- `PortfolioService` / `PortfolioRepository` / `PortfolioSummaryResponse` 확장 — `cash_total_by_currency`, `total_value_by_currency` 합산, `allocation` 에 `cash` 항목
- pytest 테스트 (services, routers, repositories, integration)

**제외**
- 모든 UI / Next.js 코드 (frontend.md 담당)
- 입출금 트랜잭션 모델 (이번 스코프 X)
- `AssetType` enum 확장 (PRD §12 결정에 따라 enum 변경 X — allocation 응답 스키마에서만 union 처리)

## 2. 변경/생성할 파일 체크리스트

### 2.1 Migration
- [ ] `backend/alembic/versions/{auto-id}_create_cash_accounts_table.py`
  - `cash_accounts` 테이블 생성
  - 컬럼: `id INT PK AUTO_INCREMENT`, `label VARCHAR(100) NOT NULL`, `currency VARCHAR(4) NOT NULL`, `balance NUMERIC(20,4) NOT NULL`, `created_at DATETIME(timezone=True) NOT NULL DEFAULT NOW()`, `updated_at DATETIME(timezone=True) NOT NULL DEFAULT NOW() ON UPDATE NOW()`
  - 인덱스: `ix_cash_accounts_currency` (currency 단일)
  - DB CHECK 제약: `balance >= 0` (가능하면 — MySQL 8.0.16+ 에서 강제됨)
  - downgrade: `op.drop_table("cash_accounts")`
  - **base revision**: 현재 head (`c8a4f1e927b3` 또는 그 이후 가장 최신) 를 `down_revision` 으로 지정. 자동 감지 OK.
  - 명령: `uv run alembic revision --autogenerate -m "create_cash_accounts_table"` 후 자동 생성된 파일을 검토·정리

### 2.2 Domain / Model
- [ ] `backend/app/models/cash_account.py`
  ```
  class CashAccount(Base):
      __tablename__ = "cash_accounts"
      id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
      label: Mapped[str] = mapped_column(String(100), nullable=False)
      currency: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
      balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
      created_at, updated_at  # 기존 모델과 동일 패턴
  ```
- [ ] `app/models/__init__.py` 에 export 추가

### 2.3 Schemas (Pydantic v2)
- [ ] `backend/app/schemas/cash_account.py`
  - `CashAccountCreate(BaseModel)`:
    - `label: str = Field(..., min_length=1, max_length=100)`
    - `currency: str` — `@field_validator("currency", mode="before")` 로 `.strip().upper()` 후 정규식 `^[A-Z]{3,4}$` 검증 (PRD §12 USDT/USDC 호환)
    - `balance: Decimal = Field(..., ge=0, max_digits=20, decimal_places=4)`
    - `model_config = ConfigDict(...)` (str_strip_whitespace 등 필요 시)
  - `CashAccountUpdate(BaseModel)`:
    - `label: str | None = Field(default=None, min_length=1, max_length=100)`
    - `balance: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=4)`
    - `currency` 필드는 **선언하지 않음** (수정 불가 — PRD §5 US-2)
    - `model_config = ConfigDict(extra="forbid")` — currency 가 들어오면 422
    - `@model_validator(mode="after")` 로 `label is None and balance is None` → `ValueError("at least one field must be provided")`
  - `CashAccountResponse(BaseModel)`:
    - `model_config = ConfigDict(from_attributes=True)`
    - `id: int`, `label: str`, `currency: str`, `balance: Decimal`, `created_at: datetime`, `updated_at: datetime`
    - `@field_serializer("balance")` 로 `Decimal → str` (기존 portfolio.py 의 `_serialize_decimal_required` 패턴 따름)

### 2.4 Repository
- [ ] `backend/app/repositories/cash_account.py`
  - `class CashAccountRepository`
    - `__init__(self, session: AsyncSession)`
    - `async def list_all(self) -> Sequence[CashAccount]` — `select(CashAccount).order_by(CashAccount.created_at.desc())`
    - `async def get_by_id(self, id_: int) -> CashAccount | None`
    - `async def create(self, *, label: str, currency: str, balance: Decimal) -> CashAccount` — `session.add` + `await session.flush()` (commit 은 deps 에서)
    - `async def update(self, entity: CashAccount, *, label: str | None, balance: Decimal | None) -> CashAccount` — 필드 부분 갱신
    - `async def delete(self, entity: CashAccount) -> None`
    - `async def sum_balance_by_currency(self) -> dict[str, Decimal]` — `select(CashAccount.currency, func.sum(CashAccount.balance)).group_by(...)` → 딕트 변환. **PortfolioService 가 호출**.

### 2.5 Service
- [ ] `backend/app/services/cash_account.py`
  - `class CashAccountService`
    - `__init__(self, repository: CashAccountRepository)`
    - `async def list(self) -> list[CashAccount]`
    - `async def create(self, data: CashAccountCreate) -> CashAccount` — Repository 호출
    - `async def update(self, id_: int, data: CashAccountUpdate) -> CashAccount` — `get_by_id` → 없으면 `raise NotFoundError(f"CashAccount {id_} not found")`
    - `async def delete(self, id_: int) -> None` — 동일 패턴
  - **fastapi import 금지**. 예외는 `app.exceptions.NotFoundError` 만 사용.

### 2.6 DI
- [ ] `backend/app/core/deps.py` 에 추가:
  ```
  async def get_cash_account_service(
      session: AsyncSession = Depends(get_db_session),
  ) -> CashAccountService:
      return CashAccountService(CashAccountRepository(session))

  CashAccountServiceDep = Annotated[CashAccountService, Depends(get_cash_account_service)]
  ```
  (기존 `UserAssetServiceDep` 패턴과 동일)

### 2.7 Router
- [ ] `backend/app/routers/cash_account.py`
  - `router = APIRouter(prefix="/api/cash-accounts", tags=["cash-accounts"])`
  - 엔드포인트 4개 — PRD §8.1 그대로 따름:

| 메서드 | 경로 | response_model | status | responses 명시 |
|--------|------|----------------|--------|----------------|
| GET | `""` | `list[CashAccountResponse]` | 200 | 401 |
| POST | `""` | `CashAccountResponse` | 201 | 401, 422 |
| PATCH | `/{id_}` | `CashAccountResponse` | 200 | 401, 404, 422 |
| DELETE | `/{id_}` | (없음) | 204 | 401, 404 |

  - 모든 엔드포인트 `_current_user: CurrentUser` 의존성 필수
  - `summary`, `responses` (ErrorResponse model 명시) 작성
  - PATCH 경로 파라미터: `id_: int = Path(..., ge=1, alias="id")` (또는 path 그대로 `cash_account_id`)
  - 응답은 반드시 `CashAccountResponse.model_validate(entity)` — ORM 모델 직접 반환 금지

### 2.8 Main 등록
- [ ] `backend/app/main.py` 의 `app.include_router(...)` 블록에 `cash_account_router` 추가 (user_asset_router 다음 적절한 위치)

### 2.9 Portfolio 통합 (수정)
- [ ] `backend/app/repositories/portfolio.py` — `CashAccountRepository.sum_balance_by_currency` 를 호출할지 vs 직접 query 추가. **권장: PortfolioService 가 두 repository 를 모두 의존** (느슨한 결합)
- [ ] `backend/app/services/portfolio.py` 수정:
  - `__init__` 에 `cash_repository: CashAccountRepository | None = None` 파라미터 추가 (기본 None — 기존 호출처 호환)
  - `get_summary()` 내부에서:
    1. 기존 holdings 집계 후
    2. `cash_totals = await self._cash_repo.sum_balance_by_currency()` 호출 (None 이면 빈 dict)
    3. `total_value_by_currency` 의 통화별 합계에 `cash_totals` 합산
    4. 신규 `cash_total_by_currency: dict[str, str]` 필드 채움 (Decimal → str)
    5. `allocation` 계산 시 `grand_total` 분모에 `sum(cash_totals.values())` 포함, 별도 entry `{"asset_type": "cash", "pct": ...}` 추가 (값이 > 0 일 때만)
    6. `convert_to` 환산 시 `cash_totals` 도 `rate_map` 으로 변환하여 `converted_total_value` 에 합산
  - `pnl_by_currency`, `total_cost_by_currency`, `realized_pnl_by_currency` 는 **변경 없음** (현금에 cost 없음)

- [ ] `backend/app/schemas/portfolio.py` — `PortfolioSummaryResponse` 에 추가:
  ```
  cash_total_by_currency: dict[str, str] = Field(
      default_factory=dict,
      description="Sum of CashAccount.balance per currency (Decimal → string)",
      examples=[{"KRW": "1500000.0000"}],
  )
  ```
  - `AllocationEntry.asset_type` 의 타입을 `AssetType | Literal["cash"]` union 으로 변경 (PRD §12 결정 — enum 확장 X). **mypy 통과 검증 필수**.
  - 기존 frontend 가 `asset_type` 을 string 으로만 사용한다면 `str` 로 완화도 가능 — 안전한 union 우선.

- [ ] `backend/app/core/deps.py` 의 `PortfolioServiceDep` 빌더에 `cash_repository=CashAccountRepository(session)` 주입 추가.

### 2.10 Tests (pytest, asyncio_mode=auto)
- [ ] `backend/tests/repositories/test_cash_account_repository.py` — CRUD + `sum_balance_by_currency` 통화별 합계 검증
- [ ] `backend/tests/services/test_cash_account_service.py` — `update` / `delete` 시 `NotFoundError`, create 정상 케이스
- [ ] `backend/tests/routers/test_cash_account_router.py` (httpx AsyncClient) —
  - `GET` 빈 목록 / 데이터 포함
  - `POST` 정상 (201), 음수 balance 422, 잘못된 currency (소문자, 2자, 5자) 422, label 미존재 422
  - `PATCH` balance 만, label 만, 둘 다, 빈 객체 422, currency 포함 시 422 (extra=forbid), 없는 id 404
  - `DELETE` 정상 204, 없는 id 404
  - 미인증 401 (인증 가드 동작)
- [ ] `backend/tests/services/test_portfolio_service.py` (기존 파일 확장) — 현금 합산 시나리오:
  - cash 만 있을 때 `total_value_by_currency` 에 cash 만 표시
  - holdings + cash 함께 있을 때 통화별 합산
  - `cash_total_by_currency` 필드 정확성
  - `allocation` 에 `cash` entry 정확한 % 계산
  - `convert_to=KRW` 시 cash 도 환산되어 `converted_total_value` 합산
- [ ] `backend/tests/integration/test_cash_holdings_flow.py` — POST → GET → PATCH → portfolio summary 반영 → DELETE 풀 플로우
- [ ] **커버리지 ≥ 80%** (pre-push 게이트 통과)

## 3. 구현 순서

1. Alembic revision 생성 → `alembic upgrade head` 로 로컬 DB 적용
2. Model → Schema → Repository → Service → Router → main 등록 → 인증 통과 확인 (httpx 수동)
3. Portfolio 통합 (Service / Repository / Schema 수정)
4. Tests 작성 → `uv run pytest --cov=app` 통과
5. `uv run ruff check . && uv run ruff format --check .` + `uv run mypy .` 통과

## 4. 다른 역할과의 계약 (frontend → backend)

frontend 가 호출할 요청 / 응답 — **PRD §8 와 100% 동일해야 함**:

```
GET  /api/cash-accounts           → 200 list[CashAccountResponse]
POST /api/cash-accounts           ← {label, currency, balance}  → 201 CashAccountResponse
PATCH /api/cash-accounts/{id}     ← {label?, balance?}          → 200 CashAccountResponse
DELETE /api/cash-accounts/{id}    → 204
```

응답 직렬화:
- `balance` 는 **string** (기존 portfolio.holdings 의 quantity / cost_basis 와 동일 컨벤션 — frontend 가 Decimal.js 또는 number 변환 결정)
- 모든 timestamp 는 ISO-8601 UTC (`+00:00` suffix)

## 5. 금지사항 재강조

- ❌ services 에서 `from fastapi import HTTPException`
- ❌ models 에 비즈니스 로직 (예: `def deposit(self, amount): ...`)
- ❌ 기존 Alembic revision 파일 수정
- ❌ raw SQL 문자열 (필요 시 `text()` + 파라미터 바인딩)
- ❌ `print()` 디버깅
- ❌ balance / 잔액 값 INFO 레벨 로깅 (DEBUG 만)
- ❌ `# type: ignore` 이유 주석 없이
- ❌ 응답에서 ORM 모델 직접 반환 (반드시 `model_validate`)

## 6. 성공 기준

- [ ] 신규 Alembic revision 1개, downgrade 동작
- [ ] `cash_accounts` 테이블 생성, 인덱스 정상
- [ ] 4개 엔드포인트 OpenAPI (`/docs`) 에 정상 표시 — summary, responses 메타 완비
- [ ] `GET /api/portfolio/summary` 응답에 `cash_total_by_currency`, `allocation` 의 `cash` entry 포함
- [ ] 기존 portfolio 테스트 모두 통과 (회귀 없음)
- [ ] backend 라인 커버리지 ≥ 80%
- [ ] `ruff`, `mypy` 무결점

---

> 이 프롬프트는 `python-generator` agent 에게 그대로 전달하세요. 기존 파일 수정 (portfolio.py, deps.py, main.py) 은 `python-modifier` 에게 분리해서 전달해도 됩니다.
