# cash-holdings — frontend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **frontend 역할용 구현 지시서** 입니다.
> 대응하는 PRD: [`../cash-holdings.md`](../cash-holdings.md)
> 대상 스택: **nextjs (Next.js App Router)** — 경로 `frontend/`
> Agent: `nextjs-generator` (신규 파일) · `nextjs-modifier` (기존 파일 수정)

---

## 0. 사전 필독

1. `frontend/CLAUDE.md` — MUST / NEVER 우선. 특히:
   - **Named export** 만 (라우팅 `page.tsx` 의 default 만 예외)
   - **TypeScript strict** — `any` 금지, `unknown` + narrowing
   - **데이터 페칭은 TanStack Query** — `useEffect + fetch` 금지
   - **폼은 React Hook Form + Zod** — 수동 state+validation 금지
   - **스타일은 Tailwind** — 인라인 `style` 금지
   - **목록 key 는 고유 id** — `index` 금지
   - **컴포넌트 파일 안에 비즈니스 로직 금지** (hooks 분리)
   - **테스트 없이 컴포넌트/훅 추가 금지** — Jest + RTL 라인 커버리지 ≥ 90%
   - **프로덕션 `console.log` 금지**
2. PRD `docs/specs/cash-holdings.md` §5 (US-1~7), §6 (플로우), §8 (API 계약) 정독
3. 기존 패턴 참고:
   - `src/lib/api/portfolio.ts` (snake → camel 변환, raw 타입 분리)
   - `src/hooks/use-assets.ts` (TanStack Query mutation 패턴)
   - `src/components/features/assets/asset-list.tsx` (목록 + 빈 상태)
   - `src/lib/schemas/asset.ts` (Zod 스키마)
   - `src/components/features/assets/transaction-form.tsx` (RHF + Zod 폼)

## 1. 책임 범위

**포함**
- `/assets` 페이지에 "현금" 섹션 추가 — 보유 자산 섹션 **위**
- `CashAccountList` 컴포넌트 — 카드 그리드 + 추가 버튼 + 빈 상태
- 추가 다이얼로그 (`CashAccountAddDialog`) — RHF + Zod
- 수정 다이얼로그 또는 인라인 수정 폼 (`CashAccountEditDialog`)
- 삭제 확인 다이얼로그
- `useCashAccounts` (list) / `useCreateCashAccount` / `useUpdateCashAccount` / `useDeleteCashAccount` 훅
- `lib/api/cash-account.ts` — Axios 호출 + raw → camel 변환
- `lib/schemas/cash-account.ts` — Zod 스키마 (Create / Update)
- `types/cash-account.ts` — 타입 정의 (`CashAccount`)
- 통화 옵션 상수 (`lib/constants/currencies.ts` 또는 schemas 내부)
- `types/portfolio.ts` 에 `cashTotalByCurrency` 필드 추가
- `lib/api/portfolio.ts` 의 `RawPortfolioSummary` / `toPortfolioSummary` 에 `cash_total_by_currency` 매핑 추가
- 포트폴리오 카드/요약 위젯에 현금 분리 표시 (대시보드 페이지 — 기존 컴포넌트 확장)
- Jest + RTL 테스트

**제외**
- 백엔드 API / DB / 모델 (backend.md 담당)
- 입출금 거래 기록 UI (이번 스코프 X)
- `/cash` 별도 페이지 (PRD §12 결정 — `/assets` 통합)

## 2. 변경/생성할 파일 체크리스트

### 2.1 타입
- [ ] `frontend/src/types/cash-account.ts`
  ```ts
  export interface CashAccount {
    id: number;
    label: string;
    currency: string;       // ISO 4217 3-letter or stable coin (USDT/USDC) 4-letter
    balance: string;        // Decimal as string (백엔드 직렬화 형식 그대로)
    createdAt: string;      // ISO-8601
    updatedAt: string;
  }
  ```
- [ ] `frontend/src/types/portfolio.ts` 수정 — `PortfolioSummary` 인터페이스에 `cashTotalByCurrency: CurrencyAmountMap` 추가. allocation 의 `assetType` 에 `"cash"` 허용 (`AssetType | "cash"` union).

### 2.2 Zod 스키마
- [ ] `frontend/src/lib/schemas/cash-account.ts`
  ```ts
  import { z } from "zod";

  // PRD §8.1 — currency: 3~4 letter uppercase (USDT/USDC 호환)
  const currencyCode = z
    .string()
    .trim()
    .transform((s) => s.toUpperCase())
    .pipe(z.string().regex(/^[A-Z]{3,4}$/, "통화 코드는 3~4자 영문 대문자 (예: KRW, USDT)"));

  // balance: Decimal as string, ≥ 0, 소수점 4자리
  const balanceString = z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,4})?$/, "0 이상의 숫자 (소수점 최대 4자리)");

  export const cashAccountCreateSchema = z.object({
    label: z.string().trim().min(1, "라벨을 입력하세요").max(100),
    currency: currencyCode,
    balance: balanceString,
  });

  export const cashAccountUpdateSchema = z
    .object({
      label: z.string().trim().min(1).max(100).optional(),
      balance: balanceString.optional(),
    })
    .refine((d) => d.label !== undefined || d.balance !== undefined, {
      message: "수정할 필드를 하나 이상 입력하세요",
    });

  export type CashAccountCreateInput = z.infer<typeof cashAccountCreateSchema>;
  export type CashAccountUpdateInput = z.infer<typeof cashAccountUpdateSchema>;
  ```

### 2.3 통화 옵션
- [ ] `frontend/src/lib/constants/currencies.ts`
  ```ts
  export const COMMON_CURRENCIES = [
    { code: "KRW", label: "KRW — 한국 원" },
    { code: "USD", label: "USD — 미국 달러" },
    { code: "JPY", label: "JPY — 일본 엔" },
    { code: "EUR", label: "EUR — 유로" },
    { code: "GBP", label: "GBP — 영국 파운드" },
    { code: "CNY", label: "CNY — 중국 위안" },
    { code: "HKD", label: "HKD — 홍콩 달러" },
    { code: "SGD", label: "SGD — 싱가포르 달러" },
    { code: "AUD", label: "AUD — 호주 달러" },
    { code: "CAD", label: "CAD — 캐나다 달러" },
    { code: "CHF", label: "CHF — 스위스 프랑" },
    { code: "USDT", label: "USDT — 테더" },
    { code: "USDC", label: "USDC — USD 코인" },
  ] as const;
  ```
  드롭다운에 위 목록 + "기타 (직접 입력)" 옵션. 기타 선택 시 텍스트 input 노출.

### 2.4 API 클라이언트
- [ ] `frontend/src/lib/api/cash-account.ts`
  ```ts
  // Raw shape (snake_case)
  interface RawCashAccount { id, label, currency, balance, created_at, updated_at }

  // 변환
  function toCashAccount(raw: RawCashAccount): CashAccount { ... }

  export async function getCashAccounts(): Promise<CashAccount[]>
  export async function createCashAccount(input: CashAccountCreateInput): Promise<CashAccount>
  export async function updateCashAccount(id: number, input: CashAccountUpdateInput): Promise<CashAccount>
  export async function deleteCashAccount(id: number): Promise<void>
  ```
  - `apiClient` (axios) 사용 — `lib/api-client.ts`
  - `withCredentials` 는 클라이언트 전역 설정 (이미 적용됨)
  - 변환에 `snakeToCamel` (`lib/case`) 활용 가능

### 2.5 TanStack Query 훅
- [ ] `frontend/src/hooks/use-cash-accounts.ts`
  - `useCashAccounts()` — `useQuery({ queryKey: ['cash-accounts'], queryFn: getCashAccounts })`
  - `useCreateCashAccount()` — `useMutation`, onSuccess: `queryClient.invalidateQueries({ queryKey: ['cash-accounts'] })` + `['portfolio-summary']` 도 invalidate
  - `useUpdateCashAccount()` — 동일
  - `useDeleteCashAccount()` — 동일
  - 모두 named export

### 2.6 컴포넌트
- [ ] `frontend/src/components/features/cash/cash-account-list.tsx` (`"use client"`)
  - `useCashAccounts()` 훅 사용
  - 로딩 스켈레톤 / 에러 / 빈 상태 / 목록 카드 그리드
  - 각 카드: label · currency 배지 · balance (formatCurrency) · 수정/삭제 버튼
  - 헤더: "현금" 제목 + "현금 추가" 버튼 → `CashAccountAddDialog` 오픈
  - key 는 `account.id`

- [ ] `frontend/src/components/features/cash/cash-account-add-dialog.tsx` (`"use client"`)
  - shadcn `Dialog`
  - RHF + zodResolver(cashAccountCreateSchema)
  - 필드: label (Input), currency (Select + "기타" 옵션 시 Input 노출), balance (Input type=text — Decimal 정밀도)
  - submit → `useCreateCashAccount().mutate(...)` → 성공 시 닫기 + 토스트 + form reset
  - 422 에러 시 RHF `setError` 로 인라인 표시

- [ ] `frontend/src/components/features/cash/cash-account-edit-dialog.tsx` (`"use client"`)
  - 기존 값 prefill, currency 는 readonly 표시
  - cashAccountUpdateSchema 사용
  - submit → useUpdateCashAccount

- [ ] `frontend/src/components/features/cash/cash-account-delete-dialog.tsx` (`"use client"`)
  - 확인 다이얼로그 — "삭제하면 복구할 수 없습니다"
  - 확인 → useDeleteCashAccount

- [ ] `frontend/src/components/features/cash/currency-select.tsx` (`"use client"`)
  - 재사용 가능 컴포넌트: COMMON_CURRENCIES 드롭다운 + "기타" 자유 입력 토글
  - props: `value`, `onChange`, `disabled` (수정 시)

### 2.7 페이지 통합
- [ ] `frontend/src/app/(app)/assets/page.tsx` 수정 — 보유 자산 위에 현금 섹션 추가
  ```tsx
  <div className="container ...">
    <div className="flex items-center justify-between mb-6">
      <h1>보유 자산</h1>
      <div>{/* BulkImportButton, 자산 추가 */}</div>
    </div>
    <section className="mb-8">
      <CashAccountList />
    </section>
    <AssetList />
  </div>
  ```
  - `CashAccountList` 의 헤더는 컴포넌트 내부에 둠 (페이지에는 import 만)

### 2.8 포트폴리오 응답 타입 / 변환 확장
- [ ] `frontend/src/lib/api/portfolio.ts` 수정:
  - `RawPortfolioSummary` 에 `cash_total_by_currency: CurrencyAmountMap` 추가
  - `toPortfolioSummary` 에 `cashTotalByCurrency: raw.cash_total_by_currency ?? {}` 매핑
  - `RawAllocationEntry.asset_type` 타입을 `AssetType | "cash"` 로 확장

- [ ] 포트폴리오 요약 위젯 (예: `src/components/features/portfolio/...`) 에서 `cashTotalByCurrency` 표시 — **별도 작은 카드 또는 툴팁** 으로 "현금: KRW 1,500,000 / USDT 200" 표시. 자산 분포 도넛 차트에 `cash` 카테고리 색상 추가 (lib/chart-format.ts 의 색상 매핑 확인).

### 2.9 포맷팅
- [ ] `lib/format.ts` 의 `formatCurrency` 가 임의의 currency 코드 (USDT, USDC) 를 처리할 수 있는지 확인.
  - `Intl.NumberFormat` 가 USDT/USDC 미지원 — try/catch 후 fallback `${formattedNumber} ${code}` 형식. 기존 함수 시그니처 변경 X.

### 2.10 테스트
- [ ] `frontend/src/lib/schemas/__tests__/cash-account.test.ts` — Zod 스키마 검증 (currency 3/4자, 음수 balance, 빈 update)
- [ ] `frontend/src/lib/api/__tests__/cash-account.test.ts` — axios mock 으로 GET/POST/PATCH/DELETE, snake→camel 변환
- [ ] `frontend/src/hooks/__tests__/use-cash-accounts.test.tsx` — QueryClientProvider wrap, list / create / invalidate 동작
- [ ] `frontend/src/components/features/cash/__tests__/cash-account-list.test.tsx` — 빈 상태 · 로딩 · 데이터 렌더링 · 추가 버튼 클릭으로 다이얼로그 오픈
- [ ] `frontend/src/components/features/cash/__tests__/cash-account-add-dialog.test.tsx` — 폼 검증 (currency 소문자 → 자동 대문자, 음수 balance 에러), submit → mutation 호출, 성공 시 닫힘
- [ ] `frontend/src/components/features/cash/__tests__/cash-account-edit-dialog.test.tsx` — currency readonly, 빈 update 에러
- [ ] `frontend/src/components/features/cash/__tests__/cash-account-delete-dialog.test.tsx` — 확인 흐름
- [ ] **라인 커버리지 ≥ 90%** (pre-push 게이트)

## 3. 구현 순서

1. 타입 → Zod 스키마 → 통화 상수
2. API 클라이언트 → 훅 (TanStack Query)
3. CurrencySelect (재사용) → 다이얼로그 3종 → CashAccountList
4. `/assets` 페이지에 통합
5. portfolio.ts 응답 타입 확장 → 대시보드 위젯 갱신
6. Jest + RTL 테스트 작성 → `npx jest --coverage` 통과
7. `npx tsc --noEmit` + `npm run lint` 통과

## 4. 다른 역할과의 계약 (frontend ← backend)

backend 가 제공하는 API — **PRD §8 와 100% 동일** (backend.md 와 동기화):

```
GET  /api/cash-accounts           → 200 RawCashAccount[]
POST /api/cash-accounts           ← {label, currency, balance}  → 201 RawCashAccount  | 422
PATCH /api/cash-accounts/{id}     ← {label?, balance?}          → 200 RawCashAccount  | 404 | 422
DELETE /api/cash-accounts/{id}    → 204 | 404
```

응답 직렬화:
- `balance` 는 **string** (Decimal). 클라이언트는 표시용 변환 (Number / Intl.NumberFormat) 시 정밀도 손실 가능 — 입력값은 항상 string 으로 백엔드에 전달
- `created_at`, `updated_at` 은 ISO-8601 → `snakeToCamel` 후 `createdAt` / `updatedAt`

`GET /api/portfolio/summary` 응답에 신규 필드 `cash_total_by_currency`, allocation 에 `asset_type=cash` entry — backend 가 채워줌. 본 작업에서는 타입·UI 매핑만.

에러 응답: `{ "detail": "..." }` — 기존 axios 에러 핸들러 (`api-client.ts` 또는 toast 컴포넌트) 패턴 그대로 사용.

## 5. 금지사항 재강조

- ❌ `any` 타입 (`unknown` + narrowing)
- ❌ `useEffect` 안에서 직접 fetch
- ❌ 수동 form state + validation (RHF + Zod 만)
- ❌ default export (page.tsx 만 예외)
- ❌ 인라인 `style={{...}}` (Tailwind 만)
- ❌ 목록 key 에 index
- ❌ 비즈니스 로직을 컴포넌트 안에 (hook 분리)
- ❌ console.log (프로덕션 빌드)
- ❌ 테스트 없이 컴포넌트/훅 추가

## 6. 성공 기준

- [ ] `/assets` 페이지에 현금 섹션이 정상 노출 (보유 자산 위)
- [ ] CRUD 4개 동작 — 추가/수정/삭제 후 목록 즉시 반영
- [ ] currency 검증 — 소문자 입력 → 자동 대문자, 잘못된 형식 → 인라인 에러
- [ ] balance 음수/빈값 에러 인라인 표시
- [ ] 대시보드/포트폴리오 요약에 `cashTotalByCurrency` 노출, allocation 에 `cash` 카테고리 표시
- [ ] 다이얼로그 키보드 네비게이션 (Tab/Enter/Esc) 정상, focus trap
- [ ] 빈 상태 CTA — "현금 추가" 동작
- [ ] frontend 라인 커버리지 ≥ 90%
- [ ] `tsc --noEmit`, `lint` 무결점

---

> 이 프롬프트는 `nextjs-generator` agent 에게 그대로 전달하세요. 기존 파일 수정 (`/assets/page.tsx`, `lib/api/portfolio.ts`, `types/portfolio.ts`, 대시보드 위젯) 은 `nextjs-modifier` 에게 분리해서 전달해도 됩니다.
