# Bulk Transactions — frontend (Next.js) 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **frontend 역할 구현 지시서**입니다.
> 대응 PRD: [`../bulk-transactions.md`](../bulk-transactions.md)
> 대상 스택: Next.js 14+ (경로: `frontend/`)
> 실행 agent: `nextjs-generator` (신규 파일) + `nextjs-modifier` (기존 파일 수정 시)

---

## 맥락 (꼭 읽을 것)

- PRD: `docs/specs/bulk-transactions.md`
- frontend CLAUDE.md: `frontend/CLAUDE.md` — Server vs Client, MUST/NEVER, 폼·페칭 규칙
- 패턴 스킬: `.claude/skills/nextjs-patterns.md`, `.claude/skills/ui-design-impl.md`
- 기존 유사 코드 (재사용):
  - `frontend/src/components/features/assets/transaction-form.tsx` — RHF + Zod 단건 폼 패턴
  - `frontend/src/hooks/use-transactions.ts` — TanStack Query mutation 패턴, 에러 핸들링 (isAxiosError, 422 / 409 분기)
  - `frontend/src/lib/api-client.ts` — Axios baseURL/auth 인터셉터
  - `frontend/src/lib/schemas/transaction.ts` — `transactionCreateSchema` (Zod)

## 이 역할의 책임 범위

**포함**
- 일괄 등록 페이지 진입점 (페이지 라우트 또는 모달 — 6.UI 스펙 참고)
- 탭 컴포넌트: "CSV 업로드" / "직접 입력"
- CSV 클라이언트 파싱 + 미리보기 (첫 10행)
- 직접 입력 그리드 (행 추가 / 삭제, 셀 단위 검증, symbol/exchange 자동완성)
- API 클라이언트 훅 (`useBulkImportTransactions`)
- 에러 인라인 표시 (행/필드 강조)
- 컴포넌트·훅 단위 테스트 + 폼 통합 테스트

**제외**
- 백엔드 endpoint / 매핑 로직
- AssetSymbol 신규 등록 화면 (PRD 비목표)
- 실패 행만 골라 재제출 (PRD Out of Scope)

## 변경할/생성할 파일 (체크리스트)

### Types & Schemas
- [ ] `frontend/src/types/bulk-transaction.ts` — TS 인터페이스
  - `BulkTransactionRow`, `BulkTransactionRequest`, `BulkTransactionResponse`, `BulkTransactionError` (row, field, message)
- [ ] `frontend/src/lib/schemas/bulk-transaction.ts` — Zod schema
  - `bulkRowSchema` — 기존 `transactionCreateSchema` 의 필드 + `symbol`, `exchange` (min 1, max 50). type 은 `buy | sell` (한글 입력 허용 시 transform → 영문)
  - `bulkRequestSchema` — `z.object({ rows: z.array(bulkRowSchema).min(1).max(500) })`

### API 클라이언트 / Hook
- [ ] `frontend/src/hooks/use-bulk-import-transactions.ts`
  - `useBulkImportTransactions()` — TanStack Query `useMutation`
  - 두 가지 호출 형태:
    - `mutateAsync({ mode: "json", rows })` → `apiClient.post("/api/transactions/bulk", { rows }, { headers: { "Content-Type": "application/json" } })`
    - `mutateAsync({ mode: "csv", file })` → FormData 로 `file` 첨부 후 POST
  - `onSuccess`: `queryClient.invalidateQueries({ queryKey: ["transactions"] })` + `["user-asset-summary"]` 도 무효화
  - 에러 정규화: 422 응답 body 의 `errors[]` 를 그대로 throw (UI 가 필드별로 라우팅)

### 컴포넌트 (features)
- [ ] `frontend/src/components/features/transactions/bulk-import-dialog.tsx` — 진입 다이얼로그(또는 페이지). shadcn `Dialog` 사용. 안에 `Tabs` 2개
- [ ] `frontend/src/components/features/transactions/bulk-csv-tab.tsx`
  - 파일 input (accept=".csv,text/csv")
  - 클라이언트 측 파싱 — `papaparse` 미사용 시 자체 `splitCsv` (인용부호 처리 필요). 라이브러리 추가 권장 (`papaparse` + `@types/papaparse`)
  - 첫 10행 + 행 수 + 파일 크기 미리보기. 1MB / 500행 사전 차단 (인라인 에러)
  - "저장" 버튼 → `useBulkImportTransactions().mutateAsync({ mode: "csv", file })`
  - 422 응답 시 `errors[]` 를 미리보기 테이블에 매핑하여 행 강조
- [ ] `frontend/src/components/features/transactions/bulk-grid-tab.tsx`
  - RHF `useFieldArray` 로 동적 행. 디폴트 5행
  - 컬럼: symbol, exchange, type(select), quantity, price, traded_at(datetime-local), memo, tag
  - "행 추가" / 행별 "삭제" 버튼. 키보드: Tab 으로 셀 이동
  - symbol/exchange 자동완성: `useUserAssets()` 결과로 `<datalist>` 제공
  - 제출 시 zod parse → mutate({ mode: "json", rows })
  - 422 errors[].row 를 RHF `setError(`rows.${row}.${field}`, ...)` 로 매핑
- [ ] `frontend/src/components/features/transactions/bulk-error-list.tsx` — 422 errors[] 를 가독성 있게 요약 표시 (상단)

### 페이지 / 라우트 (둘 중 하나 선택 — 권장: 다이얼로그)
- [ ] **권장**: 거래 목록 페이지 / 헤더에 "일괄 등록" 버튼 추가 → `bulk-import-dialog.tsx` 오픈
- [ ] **대안**: `frontend/src/app/transactions/bulk/page.tsx` 신규 페이지 + `loading.tsx` + `error.tsx`. 이 경우 `Server Component → Client tabs` 분리

기존 거래 페이지 위치를 먼저 탐색 (`frontend/src/app/**/page.tsx`) 후 결정. PRD 가 진입 위치를 강제하지 않음 — 일관성 우선.

### 테스트 (Jest + RTL, 커버리지 ≥ 90%)
- [ ] `frontend/src/hooks/__tests__/use-bulk-import-transactions.test.ts`
  - 200 응답 시 `imported_count`, `preview` 정상 반환
  - 422 응답 시 `errors[]` 가 throw 됨
  - JSON / CSV 두 모드 분기
- [ ] `frontend/src/components/features/transactions/__tests__/bulk-csv-tab.test.tsx`
  - 1MB 초과 파일 → 인라인 에러, mutation 호출 안 됨
  - 500행 초과 CSV → 동일
  - 헤더 누락 CSV → 인라인 에러
  - 정상 CSV 업로드 → 미리보기 10행 표시 → 저장 버튼 동작
- [ ] `frontend/src/components/features/transactions/__tests__/bulk-grid-tab.test.tsx`
  - 행 추가/삭제 동작
  - quantity ≤ 0 입력 시 셀 인라인 에러
  - 정상 N행 제출 → mutation 호출, 인자 검증
  - 422 응답 시 해당 행에 에러 표시
- [ ] `frontend/src/components/features/transactions/__tests__/bulk-import-dialog.test.tsx`
  - 탭 전환, 다이얼로그 닫기

## UI 스펙

```
┌─ 일괄 등록 다이얼로그 ─────────────────────────────────┐
│  [ CSV 업로드 ]  [ 직접 입력 ]                         │
│ ───────────────────────────────────────────────────── │
│  CSV 탭:                                               │
│    [ 파일 선택 ]  example.csv (12 KB, 23 행)           │
│    헤더: symbol, exchange, type, quantity, price, ...  │
│    미리보기 (첫 10행 — 표)                             │
│    [에러 요약 박스 — 422 시]                           │
│    [ 저장 ]  [ 취소 ]                                  │
│                                                        │
│  직접 입력 탭:                                         │
│    ┌────┬────────┬─────────┬──────┬─────┬──────┐      │
│    │ #  │ symbol │ exchange │ type │ qty │ ... │ [x]  │
│    ├────┼────────┼─────────┼──────┼─────┼──────┤      │
│    │ 1  │ BTC    │ UPBIT   │ buy  │ 0.5 │ ... │ [-]  │
│    │ ...│        │         │      │     │     │      │
│    └────┴────────┴─────────┴──────┴─────┴──────┘      │
│    [ + 행 추가 ]                                       │
│    [ 저장 ]  [ 취소 ]                                  │
└────────────────────────────────────────────────────────┘
```

- 그리드 키보드 네비 (Tab/Shift+Tab) 필수
- 에러 행은 좌측 indicator + 셀 `aria-invalid` + 하단 message
- 422 응답 시 `bulk-error-list` 가 상단 요약 + 그리드 행에 인라인 표시

## 구현 제약

`frontend/CLAUDE.md` 규칙을 우선합니다. 특히:
- Named export 만 (라우트 `page.tsx` 제외)
- `any` 금지 — `unknown` + narrow 또는 명시 타입
- 폼은 React Hook Form + Zod, 수동 state 금지
- `useEffect` 안에서 fetch 금지 — TanStack Query 사용
- `console.log` 금지 (개발 중 임시 사용 시 제출 전 제거)
- `next/image` 필요 시 사용 (본 기능은 텍스트 위주이므로 미해당 가능)
- 비즈니스 로직은 hooks/util 로 분리, 컴포넌트 파일에 직접 두지 않음
- TypeScript strict, `npx tsc --noEmit` 통과
- Jest 라인 커버리지 ≥ 90%

## 다른 역할과의 계약 (Interface)

### ← backend 가 제공 (이미 구현되어 있다고 가정)

**Endpoint**: `POST /api/transactions/bulk`

**Request — JSON 모드** (Content-Type: `application/json`)
```json
{ "rows": [{ "symbol": "BTC", "exchange": "UPBIT", "type": "buy", "quantity": "0.5", "price": "85000000", "traded_at": "2026-04-20T10:00:00+09:00", "memo": "DCA", "tag": "DCA" }] }
```

**Request — CSV 모드** (Content-Type: `multipart/form-data`)
- Form field: `file` (UTF-8 CSV, ≤ 1 MB)
- CSV 헤더 필수: `symbol, exchange, type, quantity, price, traded_at`. 선택: `memo, tag`

**Response 200**
```json
{ "imported_count": 2, "preview": [TransactionResponse, ...] }
```

**Response 422**
```json
{
  "detail": "Bulk validation failed",
  "errors": [
    { "row": 1, "field": "symbol", "message": "Unknown (symbol, exchange) — register the asset first." },
    { "row": 0, "field": null, "message": "..." }
  ]
}
```

**기타**: 400 (bad CSV/header), 401 (auth — interceptor 가 처리), 413 (>1MB), 415 (wrong content-type)

### → backend 에 요구

- 행 인덱스 `row` 는 **1-based** (헤더 0, 첫 데이터 행 1) — backend.md 와 동일
- `field` 는 응답 row 의 컬럼명 (`symbol`, `exchange`, `type`, `quantity`, `price`, `traded_at`, `memo`, `tag`) 또는 `null` (행 단위 / 전역 에러)
- 422 응답 body 는 항상 `{ detail, errors[] }` 구조

> 계약 변경 시 PRD "API 계약" 섹션 먼저 수정 → backend.md / frontend.md 동기 업데이트.

## 실행 지시 (agent 가 따를 순서)

1. `frontend/CLAUDE.md` + 본 프롬프트 읽기
2. 기존 코드 탐색:
   - `transaction-form.tsx` 의 RHF+Zod 패턴, 에러 매핑 방식
   - `use-transactions.ts` 의 mutation/invalidate 패턴
   - 거래 목록 페이지 위치 — "일괄 등록" 진입점 결정
3. 파일 생성 순서: types → schemas → hook → bulk-error-list → bulk-csv-tab → bulk-grid-tab → bulk-import-dialog → 진입점(버튼) 통합 → 테스트
4. 사전 차단 검증을 클라이언트에서 강하게 (1MB, 500행, 헤더 필수). 백엔드도 동일 검증하지만 UX 를 위해 라운드트립 절약
5. CSV 파싱은 `papaparse` 라이브러리 도입 권장 — `npm install papaparse @types/papaparse`. 미사용 시 표준 라이브러리 없으므로 인용부호 / 줄바꿈 escape 케이스 테스트 추가 필수
6. `npm run lint` + `npx tsc --noEmit` + `npm test -- --coverage` 통과
7. 요약 리포트:
   - 생성 파일 목록 (절대경로)
   - 변경 기존 파일 (진입 버튼 추가된 페이지)
   - 새로 추가된 npm 패키지
   - 후속 수동 작업 (없으면 "없음")

## 성공 기준

- 체크리스트 모든 항목 완료
- `npm test` 전체 통과, 라인 커버리지 ≥ 90%
- `npx tsc --noEmit` 에러 0
- `frontend/CLAUDE.md` 의 NEVER 항목 위반 0
- PRD 의 US-1 ~ US-5 가 컴포넌트 테스트로 모두 검증됨
- 키보드만으로 그리드 입력·제출 가능 (수동 확인 또는 RTL `userEvent.tab()` 테스트)
