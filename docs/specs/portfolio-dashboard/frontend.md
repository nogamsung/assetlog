# Portfolio Dashboard — Frontend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**입니다.
> 대응하는 PRD: [`../portfolio-dashboard.md`](../portfolio-dashboard.md)
> 대응하는 스택: **nextjs / Next.js App Router** (경로: `frontend/`)
> 대응하는 브랜치: `feature/portfolio-dashboard` (worktree: `.worktrees/feature-portfolio-dashboard/`)

---

## 맥락 (꼭 읽을 것)

1. **상위 PRD**: `docs/specs/asset-tracking.md` — US-7, US-8, US-10 참조
2. **이 슬라이스 PRD**: `docs/specs/portfolio-dashboard.md` — 특히 섹션 5 (유저 스토리) · 6 (플로우) · 8 (API 계약)
3. **frontend CLAUDE.md**: `frontend/CLAUDE.md` — 필수 규칙 (named export, TanStack Query, RHF+Zod, any 금지, 테스트 필수)
4. **OpenAPI**: `docs/api/asset-tracking.yaml` — backend 가 갱신한 `PortfolioSummaryResponse` / `HoldingResponse`
5. **기존 패턴 참고**:
   - `frontend/src/lib/api/asset.ts` — axios + snakeToCamel 어댑터 패턴
   - `frontend/src/hooks/use-assets.ts` — TanStack Query 훅 스타일, `assetKeys` 키 팩토리
   - `frontend/src/components/features/assets/asset-list.tsx` — 목록 렌더 + Skeleton/Empty/Error 상태
   - `frontend/src/components/features/assets/asset-type-badge.tsx` — 배지 컴포넌트
   - `frontend/src/app/(app)/assets/page.tsx` + `(app)/layout.tsx` — 인증 그룹 라우팅 (AppHeader)
   - `frontend/src/__tests__/hooks/use-assets.test.tsx`, `__tests__/components/features/assets/asset-list.test.tsx` — RTL + MSW 또는 mock 패턴

## 이 역할의 책임 범위

### 포함
- **페이지**: `app/(app)/dashboard/page.tsx` + `loading.tsx` + `error.tsx`
- **AppHeader 수정**: 네비에 "대시보드" 링크 추가 (`/dashboard`)
- **타입**: `src/types/portfolio.ts` — `HoldingResponse`, `PortfolioSummary`, `AllocationEntry`, `PnlEntry`, `CurrencyAmountMap`
- **API 클라이언트**: `src/lib/api/portfolio.ts` — `getPortfolioSummary()`, `getPortfolioHoldings()`. snake_case → camelCase 변환. `Decimal` 문자열은 그대로 string 유지 (표시 직전 변환).
- **훅**: `src/hooks/use-portfolio.ts` — `usePortfolioSummary()`, `usePortfolioHoldings()`. 공통 `portfolioKeys`.
- **컴포넌트**:
  - `src/components/features/portfolio/summary-cards.tsx` — 3 카드 (총평가액/총손익/요약 메타 "마지막 갱신 시각 · pending_count")
  - `src/components/features/portfolio/allocation-donut.tsx` — 자산 클래스 비중 도넛 차트. **라이브러리**: `recharts` (신규 추가) 또는 순수 SVG. **권장: `recharts`** (PRD 오픈 이슈 참조)
  - `src/components/features/portfolio/holdings-table.tsx` — 정렬 가능한 테이블 (열: 심볼·이름·수량·평균단가·현재가·평가액·손익·비중)
  - `src/components/features/portfolio/pending-badge.tsx` · `stale-badge.tsx` — 상태 배지 (기존 `asset-type-badge.tsx` 스타일 따라)
- **포맷터**: `src/lib/format.ts` (기존 없으면 신설) — `formatCurrency(amount: string, currency: string)`, `formatPercent(pct: number)`, `formatRelativeTime(iso: string | null)` (Korean locale, "12분 전 업데이트")
- **테스트**: 각 훅·컴포넌트·API 모듈 Jest + RTL. 계약 mock 은 PRD 8절 예시를 고정 fixture 로 사용.

### 제외
- Backend API 변경 (backend 담당)
- 가격 갱신 로직 / 스케줄러
- `/assets` 페이지 수정 (단, Dashboard 테이블 "상세" 링크만 `/assets` 로 연결)
- 서버 컴포넌트에서 fetch — 기존 TanStack Query 패턴 유지

## 변경할 / 생성할 파일 (체크리스트)

### Page & Routing
- [ ] `frontend/src/app/(app)/dashboard/page.tsx`
  - 서버 컴포넌트. `<SummaryCards /> <AllocationDonut /> <HoldingsTable />` 구성
  - `export const metadata = { title: "대시보드 — AssetLog" }`
  - 빈 포트폴리오 (`holdings.length === 0`) → EmptyState + `/assets/new` CTA
- [ ] `frontend/src/app/(app)/dashboard/loading.tsx` — Skeleton 카드 3개 + 테이블 스켈레톤
- [ ] `frontend/src/app/(app)/dashboard/error.tsx` — "다시 시도" 버튼
- [ ] `frontend/src/app/(app)/layout.tsx` **(수정)** — AppHeader nav 에 `<Link href="/dashboard">대시보드</Link>` 추가 (보유 자산 링크 앞 또는 뒤)

### Types
- [ ] `frontend/src/types/portfolio.ts`
  ```ts
  export type CurrencyAmountMap = Record<string, string>;   // Decimal as string
  export interface PnlEntry { abs: string; pct: number; }
  export interface AllocationEntry { assetType: AssetType; pct: number; }
  export interface PortfolioSummary {
    totalValueByCurrency: CurrencyAmountMap;
    totalCostByCurrency: CurrencyAmountMap;
    pnlByCurrency: Record<string, PnlEntry>;
    allocation: AllocationEntry[];
    lastPriceRefreshedAt: string | null;
    pendingCount: number;
    staleCount: number;
  }
  export interface HoldingResponse {
    userAssetId: number;
    assetSymbol: AssetSymbolResponse;
    quantity: string;            // Decimal
    avgCost: string;             // Decimal
    costBasis: string;           // Decimal
    latestPrice: string | null;  // Decimal | null
    latestValue: string | null;  // Decimal | null
    pnlAbs: string | null;       // Decimal | null
    pnlPct: number | null;
    weightPct: number;
    lastPriceRefreshedAt: string | null;
    isStale: boolean;
    isPending: boolean;
  }
  ```

### API Client
- [ ] `frontend/src/lib/api/portfolio.ts`
  - `getPortfolioSummary(): Promise<PortfolioSummary>`
  - `getPortfolioHoldings(): Promise<HoldingResponse[]>`
  - snake_case → camelCase 변환 (기존 `snakeToCamel` 재사용)
  - raw 타입 (`RawPortfolioSummary`, `RawHolding`) 내부 정의

### Hooks
- [ ] `frontend/src/hooks/use-portfolio.ts`
  ```ts
  export const portfolioKeys = {
    summary: ['portfolio', 'summary'] as const,
    holdings: ['portfolio', 'holdings'] as const,
  };
  export function usePortfolioSummary() { /* staleTime 60_000 */ }
  export function usePortfolioHoldings() { /* staleTime 60_000 */ }
  ```

### Components
- [ ] `frontend/src/components/features/portfolio/summary-cards.tsx`
  - Card 3종: 총평가액 · 총손익 · 메타(갱신 시각, pending_count)
  - 통화 분리 표기: `12,500,000 KRW · 8,200.12 USD`
  - 손익 양수 녹색 / 음수 빨강 / 0 회색
  - pending_count > 0 시 "현재가 대기 중 N 건" 주석
- [ ] `frontend/src/components/features/portfolio/allocation-donut.tsx`
  - `recharts` `PieChart` + `Tooltip` + `Legend`
  - 빈 배열일 때 "데이터 없음" placeholder
  - `aria-label="자산 클래스별 비중 도넛 차트"` + 텍스트 대안 리스트 제공 (스크린리더용)
- [ ] `frontend/src/components/features/portfolio/holdings-table.tsx`
  - `<table>` 시맨틱 + `<caption>` + `<th scope="col">`
  - 정렬 가능 열: 평가액 · 손익 · 비중 (기본: 평가액 desc)
  - 정렬 상태 → 컴포넌트 로컬 state (PRD 오픈 이슈: URL 쿼리 보존은 v1.1)
  - 각 행 클릭 시 `/assets` 이동 (상세 페이지는 후속)
  - pending 행: 현재가·평가액·손익·비중 셀 전부 `—` + `<PendingBadge />`
  - stale 행: 현재가 셀 옆 `<StaleBadge />`
- [ ] `frontend/src/components/features/portfolio/pending-badge.tsx`
- [ ] `frontend/src/components/features/portfolio/stale-badge.tsx`

### Formatters
- [ ] `frontend/src/lib/format.ts`
  - `formatCurrency(amount: string, currency: string): string` — `Intl.NumberFormat('ko-KR', { style: 'currency', currency })` + Decimal 정확도를 위해 소수부는 `Number(amount)` 변환 시 precision 손실 경고 (금액 범위에서는 허용)
  - `formatPercent(pct: number, digits = 2): string` — `"13.64%"`
  - `formatRelativeTime(iso: string | null): string` — null → "—", 아니면 한국어 상대 표기
  - `formatQuantity(qty: string, assetType: AssetType): string` — crypto 는 8자리, 주식은 4자리

### Dependencies
- [ ] `frontend/package.json` (수정) — `recharts` 추가. `npm install recharts` → `package-lock.json` 갱신. 번들 사이즈 영향을 커밋 메시지에 언급.

### Tests (Jest + RTL, 커버리지 ≥ 90%)
- [ ] `frontend/src/__tests__/lib/api-portfolio.test.ts` — snake/camel 변환, 에러 처리
- [ ] `frontend/src/__tests__/hooks/use-portfolio.test.tsx` — `usePortfolioSummary`, `usePortfolioHoldings` 정상/에러
- [ ] `frontend/src/__tests__/components/features/portfolio/summary-cards.test.tsx` — 손익 양/음/0, pending_count 주석, 통화 분리 표기
- [ ] `frontend/src/__tests__/components/features/portfolio/allocation-donut.test.tsx` — 빈 배열 placeholder, aria-label 존재
- [ ] `frontend/src/__tests__/components/features/portfolio/holdings-table.test.tsx` — 정렬 토글, pending/stale 배지 렌더, 빈 상태
- [ ] `frontend/src/__tests__/lib/format.test.ts` — 모든 포맷터 분기
- [ ] `frontend/src/__tests__/app/(app)/dashboard/page.test.tsx` — happy path 렌더 (훅을 `jest.mock`)

## 구현 제약 (frontend/CLAUDE.md 와 충돌 금지)

- **Named export** — default export 는 `page.tsx` / `loading.tsx` / `error.tsx` / `layout.tsx` 에서만
- **any 금지** — `unknown` + narrowing. Decimal 문자열은 `string` 유지
- **데이터 페칭** — TanStack Query 만. `useEffect + fetch` 금지
- **스타일** — Tailwind, 인라인 `style` 금지. 색상은 기존 shadcn/ui 토큰 (primary/destructive/muted-foreground 등)
- **인터랙티브 요소** — `aria-label` 또는 visible text. 정렬 버튼은 `aria-sort` 속성
- **이미지** — `next/image` (필요 시에만)
- **console.log 금지** (프로덕션 코드)
- **클라이언트 컴포넌트** — `"use client"` 는 훅/이벤트 필요한 컴포넌트만. Dashboard `page.tsx` 는 가능하면 서버 컴포넌트로 두고 아래 컴포넌트에 `"use client"` 배치
- **목록 key** — `asset.userAssetId` 등 고유 id

## 다른 역할과의 계약 (Interface)

### ← backend 에서 받음

**`GET /api/portfolio/summary`** — `PortfolioSummaryResponse`:

```json
{
  "total_value_by_currency": {"KRW": "12500000.00", "USD": "8200.12"},
  "total_cost_by_currency":  {"KRW": "11000000.00", "USD": "7500.00"},
  "pnl_by_currency": {
    "KRW": {"abs": "1500000.00", "pct": 13.64},
    "USD": {"abs": "700.12",     "pct":  9.34}
  },
  "allocation": [{"asset_type": "kr_stock", "pct": 42.1}, ...],
  "last_price_refreshed_at": "2026-04-24T09:00:00+09:00",
  "pending_count": 1,
  "stale_count": 0
}
```

**`GET /api/portfolio/holdings`** — 배열:

```json
[{
  "user_asset_id": 12,
  "asset_symbol": {...SymbolResponse...},
  "quantity": "10.0000000000",
  "avg_cost": "170.500000",
  "cost_basis": "1705.00",
  "latest_price": "175.200000",
  "latest_value": "1752.00",
  "pnl_abs": "47.00",
  "pnl_pct": 2.76,
  "weight_pct": 21.4,
  "last_price_refreshed_at": "2026-04-24T09:00:00+09:00",
  "is_stale": false,
  "is_pending": false
}]
```

**중요 변환 규칙**:
- `Decimal` 은 **string** — 포맷 직전까지 string 유지 (정밀도 보존)
- 인증: httpOnly 쿠키 자동 전송 (`apiClient` 의 `withCredentials: true`)
- 401 → axios 인터셉터가 `/login` 리다이렉트 (기존 동작)
- 에러 응답 shape: `{ detail: string }`

### 계약 변경 절차

`docs/api/asset-tracking.yaml` 를 SoT 로. 프론트 요구는 PRD "API 계약" 절 갱신 → backend 합의 → YAML 수정 → 구현.

## 실행 지시

1. `frontend/CLAUDE.md` 재확인 → 금지사항 숙지
2. `frontend/src/lib/api/asset.ts`, `frontend/src/hooks/use-assets.ts`, `frontend/src/components/features/assets/asset-list.tsx` 를 읽고 기존 패턴 흡수
3. 생성 순서: **Types → API → Hooks → Formatters → Components (badge → summary-cards → donut → holdings-table) → Page/loading/error → Layout 수정 → Tests**
4. 작업 중 명령:
   - `npm install recharts` (도넛 차트) — 커밋에 포함
   - `npx tsc --noEmit`
   - `npm run lint`
   - `npx jest --coverage` — 라인 커버리지 ≥ 90%
5. 리포트:
   - 생성된 파일 목록
   - 변경된 기존 파일 목록 (`(app)/layout.tsx`, `package.json`, `package-lock.json`)
   - backend 에게 알려야 하는 계약 이슈 (없어야 정상 — 있다면 PRD 업데이트 트리거)
   - 후속 수동 작업: (Node 18 환경이면) `nvm use 20` (MEMORY 주의)

## 성공 기준

- [ ] 모든 체크리스트 항목 체크됨
- [ ] `npx jest --coverage` 라인 커버리지 ≥ 90%
- [ ] `npx tsc --noEmit` + `npm run lint` 모두 에러 없음
- [ ] `frontend/CLAUDE.md` 의 NEVER 항목 위반 없음
- [ ] `/dashboard` 수동 시연: 100% pending 상태 (스케줄러 전) 에서도 정상 렌더 — 카드 3개 + 빈 도넛 placeholder + 테이블 모든 행 pending 배지
- [ ] 키보드만으로 정렬 토글 조작 가능 (aria-sort 반영)

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 실제 구현은 `nextjs-generator` / `nextjs-modifier` / `nextjs-tester` agent 를 통해 진행하세요.
