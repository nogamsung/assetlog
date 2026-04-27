# PRD — Bulk Transactions (대량 매수/매도 입력)

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-27 |
| 상태 | draft |
| 스택 범위 | backend (python/FastAPI) + frontend (Next.js) |
| 우선순위 | P1 |

---

## 1. 배경

현재 거래 입력은 **단건 폼** (`POST /api/user-assets/{id}/transactions`) 또는 **단일 종목 CSV import** (`POST /api/user-assets/{id}/transactions/import`) 만 지원. 사용자가 거래소 / 가계부에서 내려받은 멀티 종목 거래 내역을 한 번에 등록할 방법이 없어, 종목 수만큼 반복 작업이 필요하다.

신규 기능은 **여러 종목의 매수/매도를 한 번의 요청으로** 등록할 수 있는 multi-symbol bulk endpoint 와, CSV 업로드 + 스프레드시트형 직접 입력을 모두 지원하는 UI 를 도입한다.

## 2. 목표 (Goals)

- 사용자가 N 종목 × M 거래를 **한 번의 제출** 로 등록할 수 있다 (N, M ≤ 한도)
- all-or-nothing 트랜잭션 보장 — 한 행이라도 실패하면 **DB 변경 0건**
- 실패 시 **행별 에러 (row, field, message)** 를 응답에 포함하여 UI 에서 인라인 수정 가능
- 등록 성공 응답 p95 < 1.5 s @ 100 행 입력
- 1 MB 또는 500 행 (둘 중 먼저 도달) 초과 시 명시적 4xx 거부

## 3. 비목표 (Non-goals)

- 멀티 통화 자동 환산 — 입력한 price 는 해당 AssetSymbol 의 currency 그대로 저장
- 외부 거래소 API 직접 연동 (수동 CSV 업로드 / 직접 입력만)
- 부분 성공 (207 multi-status) — all-or-nothing 으로 단순화
- 기존 거래 일괄 수정·삭제 — 신규 등록만
- 신규 AssetSymbol **자동 생성** (master row 인 asset_symbols 는 사용자가 사전에 등록되어 있어야 함)
- BUY 전용으로 한정한 기존 단건 CSV import 대체 — 둘 다 공존

## 4. 대상 사용자

- 단일 owner (단일 사용자 모드, users 테이블 제거됨) 인증된 사용자
- 권한: `CurrentUser` dependency 통과 (기존 owner JWT 동일)

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-1 | 사용자로서 CSV 파일을 업로드하여 여러 종목의 매수/매도를 한 번에 등록할 수 있어야 한다 | 1) 업로드 → 미리보기 표시 (행 수, 첫 10행) 2) "저장" 클릭 시 모든 행이 트랜잭션으로 저장 3) 한 행이라도 검증 실패 시 0건 저장 + 행별 에러 표시 |
| US-2 | 사용자로서 스프레드시트형 그리드에서 직접 여러 행을 입력해 한 번에 저장할 수 있어야 한다 | 1) "행 추가" / "행 삭제" 버튼 동작 2) symbol/exchange 셀 선택은 기존 보유 종목(UserAsset) 자동완성 3) 제출 시 동일 bulk 엔드포인트 호출 |
| US-3 | 사용자로서 일부 행이 실패하면 어느 행/어느 필드가 왜 실패했는지 알 수 있어야 한다 | 1) 422 응답 body 에 `errors[]` (row, field, message) 4) UI 가 해당 행을 빨간 강조 + 메시지 인라인 표시 |
| US-4 | 사용자로서 등록되지 않은 (symbol, exchange) 행이 있으면 사전 거부됨을 즉시 알 수 있어야 한다 | 1) 알 수 없는 (symbol, exchange) → 422 with `field="symbol"` 메시지 2) 자동 생성하지 않음 (3.5 정책) |
| US-5 | 사용자로서 SELL 행을 포함시켰을 때 해당 종목 보유 수량이 음수가 되면 거부되어야 한다 | 1) 시간순 누적 잔고 계산 후 음수 발생 시 422 + 해당 행 식별 메시지 |

## 6. 핵심 플로우

### 행복 경로 — CSV 업로드

```
1. 사용자가 거래 페이지에서 "일괄 등록" 진입 (탭: CSV / 직접 입력)
2. CSV 탭에서 파일 선택 → 클라이언트 파싱 → 첫 10행 미리보기
3. "저장" 클릭 → multipart/form-data 로 POST /api/transactions/bulk
4. 서버: 헤더 검증 → 행별 Pydantic 검증 → (symbol, exchange) → user_asset_id 매핑
   → 시간순 누적 잔고 검증 → 단일 트랜잭션으로 INSERT
5. 200 OK { imported_count, preview[] }
6. 클라이언트가 거래 목록 invalidate + 토스트 "N건 등록 완료"
```

### 행복 경로 — 직접 입력

```
1. 사용자가 "직접 입력" 탭 선택
2. 빈 그리드 (5행 디폴트), "행 추가" 로 늘림. symbol/exchange 는 기존 보유 종목 datalist
3. "저장" 클릭 → JSON body 로 POST /api/transactions/bulk
4. 이후 4~6 동일
```

### 예외 경로

| 상황 | 응답 | UI |
|------|------|-----|
| 파일 > 1 MB | 413 | 파일 입력 위 인라인 에러 |
| 행 > 500 | 422 row=0 message="too many rows" | 그리드 상단 에러 |
| CSV 헤더 누락 | 422 row=0 field=null | 미리보기 영역에 에러 표시 |
| (symbol, exchange) 매칭 안 됨 | 422 row=k field="symbol" | 행 k 빨간 하이라이트 |
| 행 검증 실패 (quantity≤0 등) | 422 row=k field=<col> | 동일 |
| SELL 누적 잔고 < 0 | 422 row=k field="quantity" message="…running balance…" | 동일 |
| 미인증 | 401 | 로그인 화면으로 리다이렉트 |
| 서버 오류 | 500 | 토스트 + 재시도 버튼 (트랜잭션 보장으로 안전) |

## 7. 데이터 모델 (요약)

**스키마 변경 없음** — 기존 `transactions` / `user_assets` / `asset_symbols` 만 사용.

```
AssetSymbol (asset_type, symbol, exchange) UNIQUE
   1
   │
   N
UserAsset (asset_symbol_id) UNIQUE     ← bulk row 의 (symbol, exchange) → 매핑 키
   1
   │
   N
Transaction (user_asset_id, type, quantity, price, traded_at, memo, tag)
```

**매핑 규칙 (US-4)**:
- 행의 `(symbol, exchange)` 로 `AssetSymbol` 조회 → 그 `id` 로 `UserAsset` 조회
- AssetSymbol 없거나 UserAsset 으로 declare 되지 않았으면 **422 거부 (자동 생성 안 함)**
  - 사유: AssetSymbol 은 currency / asset_type / name 등 master 데이터가 필요. 사용자가 거래 입력 화면에서 임의 symbol 을 만들면 데이터 무결성 깨짐
  - 후속 PRD 에서 "신규 종목 등록 wizard" 로 분리

## 8. API 계약 (요약)

### 신규 엔드포인트

```
POST /api/transactions/bulk
  Content-Type: application/json   (직접 입력)
  Content-Type: multipart/form-data (CSV 업로드, field name: file)
  Auth: CurrentUser (기존 JWT)
```

#### Request — JSON 모드

```json
{
  "rows": [
    {
      "symbol": "BTC",
      "exchange": "UPBIT",
      "type": "buy",
      "quantity": "0.5",
      "price": "85000000",
      "traded_at": "2026-04-20T10:00:00+09:00",
      "memo": "DCA",
      "tag": "DCA"
    },
    { "symbol": "AAPL", "exchange": "NASDAQ", "type": "sell", "quantity": "10", "price": "190.50", "traded_at": "2026-04-21T14:30:00-04:00", "memo": null, "tag": null }
  ]
}
```

#### Request — CSV 모드 (multipart)

```
file: <UTF-8 CSV, ≤ 1 MB>
```

CSV 헤더 (필수, 순서 무관): `symbol, exchange, type, quantity, price, traded_at`
선택 헤더: `memo, tag`. 추가 컬럼은 무시.

#### Response — 200 OK (성공)

```json
{
  "imported_count": 2,
  "preview": [TransactionResponse, ...]   // 첫 10건 traded_at ASC
}
```

#### Response — 422 (검증 실패, all-or-nothing 롤백 후)

```json
{
  "detail": "Bulk validation failed",
  "errors": [
    { "row": 1, "field": "symbol",   "message": "Unknown (symbol, exchange) — register the asset first." },
    { "row": 3, "field": "quantity", "message": "Input should be greater than 0" },
    { "row": 0, "field": null,       "message": "Running balance would go negative at traded_at=..." }
  ]
}
```

#### 에러 코드

| 코드 | 사유 |
|------|------|
| 400 | CSV UTF-8 디코드 실패, 헤더 행 누락 |
| 401 | 인증 실패 |
| 413 | 파일 > 1 MB |
| 422 | 행 검증 실패 (any) — `errors[]` 첨부, 0건 저장 |
| 500 | 서버 오류 |

#### 한도

| 항목 | 값 |
|------|-----|
| 최대 파일 크기 | 1,048,576 bytes (1 MB) — 기존 import 와 동일 |
| 최대 행 수 | 500 (요청 body 또는 CSV 데이터 행) |
| 컬럼 길이 | symbol ≤ 50, exchange ≤ 50, memo ≤ 255, tag ≤ 50 |

### 검증 규칙

| 필드 | 규칙 |
|------|-----|
| symbol | non-empty, length ≤ 50, AssetSymbol 에 존재해야 함 |
| exchange | non-empty, length ≤ 50, (symbol, exchange) 조합으로 AssetSymbol 존재해야 함 |
| type | `buy` / `sell` (대소문자 무관) 또는 `매수` / `매도` |
| quantity | Decimal > 0, max_digits=28, decimal_places=10 |
| price | Decimal > 0, max_digits=20, decimal_places=6 |
| traded_at | ISO 8601 timezone-aware, 미래 불가 (60s tolerance — 기존과 동일) |
| memo | optional, ≤ 255 |
| tag | optional, ≤ 50 |

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | 100 행 등록 p95 < 1.5 s (DB 단일 트랜잭션, bulk insert) |
| 트랜잭션 | SQLAlchemy AsyncSession 1개 — 모든 INSERT + 잔고 검증 동일 트랜잭션 |
| 멱등성 | 동일 요청 2회 → 2회 등록 (멱등 키 미제공). 향후 후속 |
| 보안 | 기존 JWT auth dependency 재사용. 파일 크기 / 행 수 한도 강제 |
| 로깅 | bulk_import: row_count, imported_count, error_count, duration_ms (PII 제외) |
| 접근성 | 그리드 키보드 네비, 에러 메시지 `role="alert"`, 셀 `aria-invalid` |
| i18n | 한국어 UI, 에러 메시지는 영문 (기존 백엔드와 동일) |

## 10. 의존성 / 리스크

- **의존성**:
  - 기존 `Transaction`, `UserAsset`, `AssetSymbol` ORM 모델 — 변경 없음
  - 기존 `TransactionService.import_csv` 의 패턴 (Pydantic 검증, 시간순 누적 잔고) 재사용
  - 단일 owner 모드의 `CurrentUser` dependency
- **리스크**:
  - 500 행 단일 트랜잭션이 InnoDB lock 시간을 길게 점유할 수 있음 → bulk insert (`session.add_all` + 단일 flush) 로 완화
  - CSV 모드에서 큰 파일 메모리 로드 — 1 MB 제한으로 상한
  - (symbol, exchange) 매핑 실패가 가장 흔한 에러 케이스 예상 → UI 에서 자동완성으로 사전 차단

## 11. 범위 외 (Out of Scope)

- 신규 종목(AssetSymbol) 자동 등록 — 후속 PRD
- 거래소별 export 포맷 자동 인식 (Upbit / Binance / 증권사 등) — 후속
- 실패한 행만 골라 재제출 — 후속 (현재는 사용자가 UI 에서 수정 후 전체 재제출)
- WebSocket 진행률 (대용량 처리) — 후속

## 12. 오픈 이슈

- [ ] 멱등성 키 (`Idempotency-Key` 헤더) 도입 시기 — MVP 에서는 미포함
- [ ] 직접 입력 그리드의 행 수 디폴트 (5? 10?) — 디자인 검토 필요. 본 PRD 는 5 가정
- [ ] tag 컬럼이 CSV 에 있을 때 자동 정규화(공백 → null) 정책 통일 — 기존 single-asset CSV 와 동일하게 처리

---

## 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | 신규 router + service + schema, AssetSymbol/UserAsset 매핑, all-or-nothing 트랜잭션, 단위·통합 테스트 | [`./bulk-transactions/backend.md`](./bulk-transactions/backend.md) |
| frontend | 일괄 등록 페이지(탭: CSV/직접 입력), CSV 클라이언트 파싱+미리보기, 그리드 입력, API 클라이언트, 에러 인라인 표시, 컴포넌트 테스트 | [`./bulk-transactions/frontend.md`](./bulk-transactions/frontend.md) |
