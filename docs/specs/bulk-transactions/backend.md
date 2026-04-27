# Bulk Transactions — backend (python/FastAPI) 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **backend 역할 구현 지시서**입니다.
> 대응 PRD: [`../bulk-transactions.md`](../bulk-transactions.md)
> 대상 스택: python/FastAPI (경로: `backend/`)
> 실행 agent: `python-generator` (신규 파일) + `python-modifier` (기존 파일 수정 시)

---

## 맥락 (꼭 읽을 것)

- PRD: `docs/specs/bulk-transactions.md`
- backend CLAUDE.md: `backend/CLAUDE.md` — 레이어 의존, MUST/NEVER, 스타일 규칙
- 패턴 스킬: `.claude/skills/python-patterns.md`
- 기존 유사 코드 (재사용/패턴 참고):
  - `backend/app/services/transaction.py` — 단일 종목 CSV import 패턴 (Pydantic 검증, 시간순 누적 잔고, all-or-nothing flush)
  - `backend/app/repositories/transaction.py` / `user_asset.py` / `asset_symbol.py`
  - `backend/app/schemas/transaction.py` — `_TransactionBase`, `CsvImportError`
  - `backend/app/exceptions.py` — `CsvImportValidationError`, `NotFoundError`
  - `backend/app/routers/transaction.py` — `_MAX_CSV_BYTES`, multipart UploadFile 패턴

## 이 역할의 책임 범위

**포함**
- 신규 schema (`schemas/bulk_transaction.py`) — request/response/error 모델
- 신규 service (`services/bulk_transaction.py`) — 매핑·검증·all-or-nothing 등록
- 신규 router (`routers/bulk_transaction.py`) — `POST /api/transactions/bulk` (JSON 모드 + multipart CSV 모드를 한 엔드포인트에서 Content-Type 으로 분기)
- `core/deps.py` 에 `BulkTransactionServiceDep` DI 추가
- `main.py` 에 라우터 등록
- 단위 테스트 (service) + 통합 테스트 (router)
- `app/services/transaction.py` 의 CSV 정규화 로직 (`_TYPE_NORMALISATION` 등) **재사용**. 중복 정의 금지 — 필요 시 공통 모듈로 추출

**제외**
- AssetSymbol 신규 등록 (PRD 비목표) — 매핑 실패 시 422 거부만
- DB 마이그레이션 (스키마 변경 없음 — 기존 테이블만 사용)
- 프론트엔드 코드 / OpenAPI 별도 파일
- 단건 transaction CRUD 변경

## 변경할/생성할 파일 (체크리스트)

### Schemas (신규)
- [ ] `backend/app/schemas/bulk_transaction.py`
  - `BulkTransactionRow(BaseModel)` — `_TransactionBase` 필드 + `symbol: str`, `exchange: str`. `_TransactionBase` 에서 상속하여 type/quantity/price/traded_at/memo/tag 검증 재사용. `symbol`, `exchange` 는 `Field(min_length=1, max_length=50, str_strip_whitespace=True)`
  - `BulkTransactionRequest(BaseModel)` — `rows: list[BulkTransactionRow] = Field(min_length=1, max_length=500)`
  - `BulkTransactionResponse(BaseModel)` — `imported_count: int`, `preview: list[TransactionResponse]` (기존 schemas.transaction.TransactionResponse 재사용, 첫 10건 traded_at ASC)
  - `BulkTransactionError` 는 기존 `CsvImportError` 를 그대로 재사용 (row, field, message 동일 시그니처)

### Service (신규)
- [ ] `backend/app/services/bulk_transaction.py`
  - 클래스 `BulkTransactionService` 의존성: `TransactionRepository`, `UserAssetRepository`, `AssetSymbolRepository`
  - 메서드:
    - `async def import_json(rows: list[BulkTransactionRow]) -> tuple[int, list[Transaction]]` — JSON 모드 진입점
    - `async def import_csv(csv_text: str) -> tuple[int, list[Transaction]]` — multipart CSV 모드 진입점. 헤더 검증 → `BulkTransactionRow` 행별 model_validate → `import_json` 으로 위임
    - `_resolve_user_asset_ids(rows) -> dict[int, int]` — (symbol, exchange) → user_asset_id 매핑. 일괄 SELECT 1회 (N+1 금지). 매칭 실패 시 행 인덱스별 에러 누적
    - `_validate_running_balance(rows, user_asset_ids)` — user_asset_id 별로 그룹핑 → 기존 거래 + 신규 거래를 traded_at ASC 정렬 → 누적 잔고 ≥ 0 검증. 음수 발생 시 해당 신규 행 인덱스를 errors 에 추가
- [ ] all-or-nothing: 모든 행 검증 통과 후 `session.add_all(new_txs)` + `session.flush()` 1회. **commit 은 deps 의 session 의존성에서 처리** (services 에서 commit 금지)
- [ ] CSV 헤더 필수: `{symbol, exchange, type, quantity, price, traded_at}`. 선택: `{memo, tag}`
- [ ] 행 수 > 500 또는 0 → `CsvImportValidationError([{"row": 0, "field": null, "message": "..."}])`
- [ ] 로깅: `bulk_import: imported=N row_count=M duration_ms=K` (PII 없음)

### Repository (수정 / 가능하면 신규 메서드만)
- [ ] `backend/app/repositories/asset_symbol.py` 또는 `user_asset.py` 에 `async def get_user_asset_ids_by_symbol_exchange(pairs: list[tuple[str, str]]) -> dict[tuple[str, str], int]` 추가
  - 단일 SQL 쿼리: `SELECT ua.id, asym.symbol, asym.exchange FROM user_assets ua JOIN asset_symbols asym ON ua.asset_symbol_id=asym.id WHERE (asym.symbol, asym.exchange) IN (:pairs)`
  - SQLAlchemy `tuple_(...).in_()` 또는 OR 체인. 파라미터 바인딩 필수 (raw SQL 금지)
- [ ] 기존 `TransactionRepository.list_all_for_user_asset` 을 user_asset_id **목록** 으로 한 번에 조회하는 헬퍼 추가 (N+1 회피): `async def list_all_for_user_assets(user_asset_ids: list[int]) -> dict[int, list[Transaction]]`

### Router (신규)
- [ ] `backend/app/routers/bulk_transaction.py`
  - `router = APIRouter(prefix="/api/transactions", tags=["bulk-transactions"])`
  - `POST /bulk` 엔드포인트 1개. **Content-Type 분기** 패턴:
    - `Request.headers["content-type"]` 가 `application/json` 으로 시작 → JSON body 파싱 → `BulkTransactionRequest` → `service.import_json(...)`
    - `multipart/form-data` 로 시작 → `UploadFile` 읽기 → 1 MB 검증 → utf-8-sig 디코드 → `service.import_csv(...)`
    - 그 외 → 415 Unsupported Media Type
  - `response_model=BulkTransactionResponse`, `status_code=200`
  - `responses={400, 401, 413, 415, 422}` 모두 명시. 422 응답 모델은 기존 `ErrorResponse` 패턴 + `errors[]` (router 가 `CsvImportValidationError` 캐치 후 변환). 가능하면 `BulkValidationErrorResponse` schema 신설.
  - `summary="Bulk import multi-symbol transactions (JSON or CSV)"`
- [ ] `backend/app/main.py` 에 신규 router 등록

### DI (수정)
- [ ] `backend/app/core/deps.py` 에 `BulkTransactionServiceDep = Annotated[BulkTransactionService, Depends(get_bulk_transaction_service)]` 추가. 기존 transaction 의존성 패턴 그대로 따라할 것

### 테스트 (커버리지 ≥ 80%, 가능하면 ≥ 90%)
- [ ] `backend/tests/services/test_bulk_transaction_service.py`
  - 정상 — JSON 2종목 × 각 1 BUY 등록 → imported=2
  - 정상 — JSON 1종목 BUY+SELL 시간순 잔고 OK → imported=2
  - 실패 — quantity≤0 행 1개 → 422 errors[].row 정확, **DB 변경 0건** (assert)
  - 실패 — 알 수 없는 (symbol, exchange) → errors[].field=="symbol"
  - 실패 — UserAsset 미선언 (AssetSymbol 만 존재) → errors[].field=="symbol"
  - 실패 — SELL 누적 잔고 음수 → errors[].message contains "running balance"
  - 실패 — 행 수 0 → 422
  - 실패 — 행 수 501 → 422
  - CSV — 헤더 누락 → 422 row=0
  - CSV — type 한글 (`매수`/`매도`) 정규화 OK
  - 트랜잭션 롤백 — `add_all` 중간 에러 시 0 row inserted (mock raise)
- [ ] `backend/tests/routers/test_bulk_transaction_router.py`
  - 200 JSON / 200 CSV / 400 헤더 누락 / 413 1MB 초과 / 415 wrong content-type / 422 행 에러 / 401 미인증
- [ ] 픽스쳐: `tests/fixtures/` 에 `seeded_user_assets` (BTC/UPBIT, AAPL/NASDAQ 사전 declare) 추가

## 구현 제약

`backend/CLAUDE.md` 규칙을 우선합니다. 특히:
- Service 에서 `fastapi.*` import 금지, `HTTPException` 금지 — `CsvImportValidationError` 등 도메인 예외 raise → router 또는 `@app.exception_handler` 에서 매핑
- `commit()` 호출 금지 — `Depends(get_db_session)` 가 처리
- `models/` 수정 없음 (스키마 변경 없음)
- raw SQL 금지 — SQLAlchemy `select`, `tuple_(...).in_()` 사용
- `print()` 금지, `logging.getLogger(__name__)` 사용
- mypy strict 통과, ruff format 통과
- `# type: ignore` 사용 시 이유 주석 필수

## 다른 역할과의 계약 (Interface)

### → frontend 에 제공

**Endpoint**: `POST /api/transactions/bulk`

**Request — JSON 모드**
```json
{
  "rows": [
    {
      "symbol": "BTC", "exchange": "UPBIT",
      "type": "buy", "quantity": "0.5", "price": "85000000",
      "traded_at": "2026-04-20T10:00:00+09:00",
      "memo": "DCA", "tag": "DCA"
    }
  ]
}
```
- Header: `Content-Type: application/json`, `Authorization: Bearer <jwt>`

**Request — CSV 모드**
- Header: `Content-Type: multipart/form-data`, `Authorization: Bearer <jwt>`
- Form field: `file` — UTF-8 encoded CSV
- CSV 헤더 필수: `symbol, exchange, type, quantity, price, traded_at` (순서 무관). 선택: `memo, tag`

**Response 200** — `BulkTransactionResponse`
```json
{
  "imported_count": 2,
  "preview": [{ "id": 101, "user_asset_id": 1, "type": "buy", "quantity": "0.5000000000", "price": "85000000.000000", "traded_at": "...", "memo": "DCA", "tag": "DCA", "created_at": "..." }]
}
```

**Response 422** — Bulk validation error
```json
{
  "detail": "Bulk validation failed",
  "errors": [
    { "row": 1, "field": "symbol", "message": "Unknown (symbol, exchange) — register the asset first." },
    { "row": 0, "field": null, "message": "Running balance would go negative at traded_at=..." }
  ]
}
```

**기타 에러**: 400 (bad CSV/header), 401 (auth), 413 (>1MB), 415 (wrong content-type)

### ← frontend 가 호출

- 인증: 기존 JWT (`apiClient` 가 자동 첨부)
- 한도: 1 MB / 500 행. 클라이언트도 동일 제한을 적용해 사전 차단

> 계약 변경 시 PRD 의 "API 계약" 섹션 먼저 수정 → 본 backend.md 와 frontend.md 동기 업데이트.

## 실행 지시 (agent 가 따를 순서)

1. `backend/CLAUDE.md` + 본 프롬프트 읽기
2. 기존 코드 탐색:
   - `services/transaction.py` 의 `import_csv` 메서드 — Pydantic 검증, 누적 잔고, `add_all`+`flush` 패턴 그대로 차용
   - `repositories/asset_symbol.py`, `repositories/user_asset.py` — 기존 lookup 메서드 시그니처 확인
3. 파일 생성 순서: schemas → service → repository (helper 추가) → router → deps → main.py 등록 → tests
4. `uv run ruff format .` + `uv run ruff check .` + `uv run mypy .` 통과 확인
5. `uv run pytest --cov=app tests/services/test_bulk_transaction_service.py tests/routers/test_bulk_transaction_router.py` 통과 + 커버리지 ≥ 80% (가능하면 90%)
6. 요약 리포트:
   - 생성 파일 목록 (절대경로)
   - 변경 기존 파일 (deps.py, main.py, repositories/*)
   - frontend 에 알려야 할 변경 사항 (계약 변경 있었으면 명시)
   - 후속 수동 작업 (없으면 "없음")

## 성공 기준

- 체크리스트 모든 항목 완료
- `uv run pytest` 전체 통과
- 커버리지 ≥ 80% (목표 90%)
- `CLAUDE.md` 의 NEVER 항목 위반 0
- PRD 의 모든 수락 기준 (US-1 ~ US-5) 가 자동 테스트로 검증됨
