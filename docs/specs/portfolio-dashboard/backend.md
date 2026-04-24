# Portfolio Dashboard — Backend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**입니다.
> 대응하는 PRD: [`../portfolio-dashboard.md`](../portfolio-dashboard.md)
> 대응하는 스택: **python / FastAPI** (경로: `backend/`)
> 대응하는 브랜치: `feature/portfolio-dashboard` (worktree: `.worktrees/feature-portfolio-dashboard/`)

---

## 맥락 (꼭 읽을 것)

1. **상위 PRD**: `docs/specs/asset-tracking.md` — 제품 전체 범위, 4.2 범위 경계 원칙 (외부 API 는 비동기만, 요청 경로에서 금지)
2. **이 슬라이스 PRD**: `docs/specs/portfolio-dashboard.md` — 특히 섹션 7 (데이터 모델) · 8 (API 계약) · 10 (리스크)
3. **backend CLAUDE.md**: `backend/CLAUDE.md` — 필수 규칙 (async 일관성, DI, Schema≠Model, Router 메타 등)
4. **OpenAPI**: `docs/api/asset-tracking.yaml` — `PortfolioSummaryResponse` / `HoldingResponse` 스키마 정합 (본 작업에서 갱신)
5. **기존 패턴 참고**:
   - `backend/app/repositories/user_asset.py` — selectinload + scope-by-user 패턴
   - `backend/app/repositories/transaction.py::get_summary` — 집계 쿼리 패턴 (`func.sum`, `func.coalesce`)
   - `backend/app/routers/user_asset.py` — 라우터 메타 & 응답 모델 선언 스타일
   - `backend/app/core/deps.py` — DI 팩토리 배치
   - `backend/tests/routers/test_user_assets.py` · `backend/tests/services/test_user_asset.py` — 테스트 스타일

## 이 역할의 책임 범위

### 포함
- **Alembic migration 1개**: `asset_symbols` 테이블에 `last_price` (Numeric(20,6), nullable) + `last_price_refreshed_at` (DateTime(tz=True), nullable) + 인덱스 추가. 값 채움 로직은 **미포함**.
- **모델 갱신**: `app/models/asset_symbol.py` 에 두 컬럼 Mapped 필드 추가.
- **도메인 상수**: `app/domain/portfolio.py` 신설 (`STALE_THRESHOLD = timedelta(hours=3)`).
- **Repository**: `app/repositories/portfolio.py` — 사용자 스코프의 집계 조회 (단일 쿼리, N+1 금지).
- **Service**: `app/services/portfolio.py` — 통화별 그룹핑, pending/stale 분류, 비중 계산, 파생값 계산.
- **Schemas**: `app/schemas/portfolio.py` — `HoldingResponse`, `PortfolioSummaryResponse`, `PnlEntry`, `AllocationEntry`, `CurrencyAmountMap` (Pydantic v2, `model_config` + `field_serializer` 로 `Decimal → str`).
- **Router**: `app/routers/portfolio.py` — `GET /api/portfolio/summary`, `GET /api/portfolio/holdings`. 기존 `app/main.py` 에 include_router.
- **DI**: `app/core/deps.py` 에 `PortfolioRepositoryDep`, `PortfolioServiceDep` 추가.
- **Tests**: repository / service / router 3계층. 계약 테스트 포함 (응답 JSON 키 일치).
- **OpenAPI 갱신**: `docs/api/asset-tracking.yaml` 의 `/portfolio/summary`, `/portfolio/holdings` 경로와 스키마를 본 PRD 8절 예시에 맞춰 확정 (`HoldingResponse` 스키마 신설, `pending_count` / `stale_count` 필드 추가).

### 제외
- 외부 시세 API 호출 / yfinance/pykrx/ccxt 어댑터
- apscheduler 설정 / 가격 갱신 job
- `PricePoint` 테이블 신설 (후속 슬라이스)
- UI (frontend 담당)

## 변경할 / 생성할 파일 (체크리스트)

### Migration
- [ ] `backend/alembic/versions/{rev}_add_last_price_to_asset_symbols.py`
  - `op.add_column('asset_symbols', sa.Column('last_price', sa.Numeric(20, 6), nullable=True))`
  - `op.add_column('asset_symbols', sa.Column('last_price_refreshed_at', sa.DateTime(timezone=True), nullable=True))`
  - `op.create_index('ix_asset_symbols_last_refreshed', 'asset_symbols', ['last_price_refreshed_at'])`
  - downgrade 는 역순

### Model
- [ ] `backend/app/models/asset_symbol.py` (수정)
  - `last_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)`
  - `last_price_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)`
  - 테이블 `__table_args__` 에 신규 인덱스 추가

### Domain
- [ ] `backend/app/domain/portfolio.py` (신규)
  - `STALE_THRESHOLD = timedelta(hours=3)`
  - 필요 시 `HoldingValuation` NamedTuple / frozen dataclass (파생값 캐리어)

### Repository
- [ ] `backend/app/repositories/portfolio.py` (신규)
  - `list_user_holdings_with_aggregates(user_id: int) -> list[HoldingRow]`
    - 단일 쿼리: `UserAsset` + `selectinload(asset_symbol)` + 서브쿼리(tx BUY 집계).
    - 반환: `list[HoldingRow]` — `HoldingRow` 는 `user_asset_id`, `asset_symbol`, `total_qty: Decimal`, `total_cost: Decimal` 필드를 갖는 dataclass 또는 row proxy.
    - 없는 UserAsset(거래 0건) 은 `total_qty=Decimal("0")`, `total_cost=Decimal("0")` 으로 포함.

### Service
- [ ] `backend/app/services/portfolio.py` (신규)
  - `class PortfolioService`
  - `async def get_summary(user_id: int) -> PortfolioSummaryResponse`
  - `async def get_holdings(user_id: int) -> list[HoldingResponse]`
  - 파생값 계산은 Decimal 로. float 혼용 금지.
  - pending (`latest_price is None`) 은 합계에서 제외, `pending_count` 로 카운트.
  - stale 판정: `datetime.now(tz=UTC) - last_price_refreshed_at > STALE_THRESHOLD` (둘 다 naive 금지).
  - `last_price_refreshed_at` 전역 값 = 보유 종목의 `max(last_price_refreshed_at)`. 전부 None 이면 응답에서 `null`.
  - 비중(`weight_pct`) 분모 = `Σ latest_value` (pending 제외). 분자 = 개별 `latest_value`. 분모 0 이면 `weight_pct = 0.0`.
  - `allocation` = `asset_type` 으로 그룹 → 합 → 전체 대비 `pct` (0~100, float 소수점 2자리).

### Schemas
- [ ] `backend/app/schemas/portfolio.py` (신규)
  - `HoldingResponse` — PRD 8.2 예시와 정확히 일치. `Decimal` 필드는 `field_serializer` 로 `str` 직렬화.
  - `PortfolioSummaryResponse` — `total_value_by_currency: dict[str, str]` (Decimal→str), `pnl_by_currency: dict[str, PnlEntry]`, `allocation: list[AllocationEntry]`, `pending_count: int`, `stale_count: int`, `last_price_refreshed_at: datetime | None`.
  - `PnlEntry { abs: str (Decimal), pct: float }`
  - `AllocationEntry { asset_type: AssetType, pct: float }`
  - 모든 모델 `model_config = ConfigDict(from_attributes=True)` (필요 시).

### Router
- [ ] `backend/app/routers/portfolio.py` (신규)
  - `router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])`
  - `GET /summary` → `response_model=PortfolioSummaryResponse`, `CurrentUser` 의존성
  - `GET /holdings` → `response_model=list[HoldingResponse]`, `CurrentUser` 의존성
  - `responses={401: {"model": ErrorResponse, ...}}` 명시
  - `summary`, `description` 필수

### DI
- [ ] `backend/app/core/deps.py` (수정)
  - `PortfolioRepositoryDep`, `PortfolioServiceDep` factory 추가

### 메인 앱
- [ ] `backend/app/main.py` (수정)
  - `from app.routers.portfolio import router as portfolio_router`
  - `app.include_router(portfolio_router)`

### OpenAPI
- [ ] `docs/api/asset-tracking.yaml` (수정)
  - `/portfolio/holdings` 응답을 **신규 `HoldingResponse`** 배열로 변경 (기존: `UserAssetResponse` 배열 → 혼동 유발)
  - `components/schemas/HoldingResponse` 신설
  - `PortfolioSummaryResponse` 에 `pending_count`, `stale_count` 필드 추가
  - `SymbolResponse` 에 `last_price`, `last_price_refreshed_at` 필드 추가 (response only, nullable)

### Tests
- [ ] `backend/tests/repositories/test_portfolio.py`
  - 다중 사용자 격리 (다른 user 의 자산이 섞이지 않음)
  - BUY 거래 0건인 UserAsset 처리
  - BUY N건 집계 정확성 (가중평균, 총원가)
- [ ] `backend/tests/services/test_portfolio.py`
  - pending 만 있는 경우 → `total_value_by_currency` 빈 dict, `pending_count > 0`
  - mixed currency 집계 (KRW + USD 분리)
  - stale 판정 경계 (정확히 3h, 3h+1s)
  - 비중 합 100% 이내 오차 ≤ 0.01 (pending 제외)
  - allocation 합 100% (float 반올림 오차 허용 0.1)
- [ ] `backend/tests/routers/test_portfolio.py`
  - 401 (미인증) / 200 (정상 경로) / 빈 포트폴리오 (summary 에 0/빈 구조)
  - 응답 JSON 키가 OpenAPI 스키마와 일치 (계약 검증)
- [ ] 커버리지 ≥ 80%

## 구현 제약 (backend/CLAUDE.md 와 충돌 금지)

- **async 일관성** — Service·Repository·Router 전부 `async def`. sync 혼용 금지.
- **Schema ≠ Model** — `HoldingResponse.model_validate(...)` 또는 명시적 매핑. ORM 모델 직접 반환 금지.
- **Router 메타** — `response_model` / `responses` / `summary` / `description` 필수. dict 반환 금지.
- **DI** — 모듈 전역 인스턴스 금지. `Depends` 경유.
- **예외** — Service 에서 `HTTPException` / `fastapi.*` import 금지. 필요 시 커스텀 예외 → `@app.exception_handler` 에서 변환.
- **ORM** — `Mapped[...] = mapped_column(...)` 필수. `Column(...)` 단독 금지.
- **Pydantic v2** — `model_config = ConfigDict(...)`, `@field_validator`, `@field_serializer`.
- **raw SQL 금지** — `text()` 없이 ORM / SQLAlchemy Core 표현식만.
- **트랜잭션 경계** — `session.commit()` 은 `get_db_session` 에서만. 이 슬라이스는 read-only 이므로 commit 불필요.
- **테스트 없는 Service 추가 금지** — 각 public 메서드 1 테스트 이상.

## 다른 역할과의 계약 (Interface)

### → frontend 로 제공

**`GET /api/portfolio/summary`** — 응답:

```yaml
PortfolioSummaryResponse:
  total_value_by_currency: {KRW: "12500000.00", USD: "8200.12"}   # Decimal → string
  total_cost_by_currency:  {KRW: "11000000.00", USD: "7500.00"}
  pnl_by_currency:
    KRW: {abs: "1500000.00", pct: 13.64}
    USD: {abs: "700.12",     pct:  9.34}
  allocation: [{asset_type: "us_stock", pct: 48.3}, ...]
  last_price_refreshed_at: "2026-04-24T09:00:00+09:00"  # nullable
  pending_count: 1
  stale_count: 0
```

**`GET /api/portfolio/holdings`** — PRD 8.2 예시의 배열.

- `Decimal` 필드 직렬화: **문자열**. 프론트는 `Number(...)` 로 변환 후 `Intl.NumberFormat` 포맷.
- `weight_pct`, `pnl_pct`, `allocation[].pct` 는 **float** (소수점 2자리 권장).
- 인증 실패 → `401` + `{detail: string}`.

### 계약 변경 절차

1. PRD `docs/specs/portfolio-dashboard.md` 의 "API 계약" 절 업데이트
2. `docs/api/asset-tracking.yaml` 업데이트
3. frontend 프롬프트(`./frontend.md`) 의 "← backend 에서 받음" 섹션 동기화

## 실행 지시

1. `backend/CLAUDE.md` 재확인 → 금지사항 숙지
2. `backend/app/models/asset_symbol.py`, `backend/app/repositories/user_asset.py`, `backend/app/repositories/transaction.py::get_summary` 를 읽고 기존 패턴 흡수
3. 생성 순서: **Migration → Model → Domain → Repository → Schemas → Service → Router → DI → main.py 등록 → OpenAPI 갱신 → Tests**
4. 작업 중 파일:
   - `uv run alembic upgrade head` 로 마이그레이션 적용 가능성 확인
   - `uv run ruff check . && uv run ruff format --check . && uv run mypy .`
   - `uv run pytest --cov=app` — 커버리지 ≥ 80%
5. 리포트:
   - 생성된 파일 목록
   - 변경된 기존 파일 목록 (`asset_symbol.py`, `deps.py`, `main.py`, `asset-tracking.yaml`)
   - frontend 에게 알려야 하는 계약 변경사항 (`HoldingResponse` 필드, Decimal → string 직렬화)
   - 후속 수동 작업: `uv run alembic upgrade head` (local DB)

## 성공 기준

- [ ] 모든 체크리스트 항목 체크됨
- [ ] `uv run pytest --cov=app` 커버리지 ≥ 80%, 새 모듈 100%
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .` 모두 0 warning
- [ ] `backend/CLAUDE.md` 의 NEVER 항목 위반 없음
- [ ] `docs/api/asset-tracking.yaml` 이 실제 응답과 일치 (계약 테스트로 검증)
- [ ] 100 종목 mock 데이터에서 `/portfolio/summary` + `/portfolio/holdings` 합산 p95 < 500ms (단순 로컬 벤치 로그 첨부)

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 실제 구현은 `python-generator` / `python-modifier` / `python-tester` agent 를 통해 진행하세요.
