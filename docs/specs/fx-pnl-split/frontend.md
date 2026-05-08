# fx-pnl-split — frontend (nextjs) 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **역할별 구현 지시서**.
> 대응 PRD: [`../fx-pnl-split.md`](../fx-pnl-split.md) — 특히 §5 US-1/US-2/US-3, §6.4 fallback, §8 API 계약
> 대응 스택: nextjs (Next.js 14 App Router) — 경로 `frontend/`

---

## 맥락 (꼭 읽을 것)

- PRD `docs/specs/fx-pnl-split.md` — 결정 lock 됨. backend 가 snapshot 인프라까지 본 PR 안에 포함하므로, 머지 직후부터 신규 거래는 즉시 분리값 활성. 기존 보유 자산은 `fx_warning="missing_historical_rate"` 응답 → frontend 가 fallback UI 처리.
- `frontend/CLAUDE.md` — TanStack Query v5, Tailwind only, named export, 라인 커버리지 ≥ **90%**.
- 핵심 기존 파일:
  - `frontend/src/types/portfolio.ts` — `HoldingResponse`, `PortfolioSummary`. **여기에 필드 추가**.
  - `frontend/src/lib/api/portfolio.ts` — `RawHolding`, `RawPortfolioSummary`, `toHolding`, `toPortfolioSummary`. **여기에 필드 추가**.
  - `frontend/src/components/features/portfolio/holdings-table.tsx` — 손익 셀 분해 표시 (데스크톱).
  - `frontend/src/components/features/portfolio/holdings-list.tsx` — 모바일 list 뷰. 동일 분해.
  - `frontend/src/components/features/portfolio/summary-cards.tsx` — "미실현 손익" 카드 분해.
  - `frontend/src/lib/format.ts` — `formatCurrency`, `pnlColor`, `formatPercent`. 재사용.
  - `frontend/src/lib/case.ts` — `snakeToCamel`.

## 이 역할의 책임 범위

**포함**:
- TypeScript 타입 (`HoldingResponse`, `PortfolioSummary`) 에 신규 필드 3 + 3 추가
- `lib/api/portfolio.ts` 의 raw 인터페이스 + camelCase 변환 추가
- `holdings-table.tsx` (데스크톱) 와 `holdings-list.tsx` (모바일) 손익 셀에 "+10만원 (가격 +8만 · 환차 +2만)" 분해 표시
- `summary-cards.tsx` "미실현 손익" 카드에 동일 분해
- `fx_warning` 분기 UI: `"missing_historical_rate"` 인포 아이콘 + tooltip
- KRW-only / 환산 비활성 모드 — 분해 라벨 숨김
- React Testing Library 테스트 — 정상 / missing / same_currency 3 분기

**제외**:
- 백엔드 API 변경 (backend.md 담당)
- 신규 페이지/라우트 추가
- 통화 토글 동작 변경

## 변경할/생성할 파일 (체크리스트)

### Types (`frontend/src/types/portfolio.ts`)

- [ ] `HoldingResponse` 인터페이스에 3개 필드 추가:
  ```ts
  pricePnl: string | null;        // Decimal as string — converted price-only PnL
  fxPnl: string | null;           // Decimal as string — converted FX-only PnL
  fxWarning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null;
  ```
- [ ] `PortfolioSummary` 인터페이스에 3개 필드 추가:
  ```ts
  convertedPricePnl: string | null;
  convertedFxPnl: string | null;
  fxWarning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null;
  ```
- [ ] `fxWarning` 타입은 union literal 로 — `string` 회피, 정확한 enum 보장.

> 주: 이전 draft 의 `fxBuyAvg` 는 응답에서 제거됨 (PRD §8). 타입에도 추가하지 않음.

### API Layer (`frontend/src/lib/api/portfolio.ts`)

- [ ] `RawHolding` 인터페이스에 snake_case 필드 3개 추가:
  ```ts
  price_pnl: string | null;
  fx_pnl: string | null;
  fx_warning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null;
  ```
- [ ] `RawPortfolioSummary` 인터페이스에 snake_case 필드 3개 추가:
  ```ts
  converted_price_pnl: string | null;
  converted_fx_pnl: string | null;
  fx_warning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null;
  ```
- [ ] `toHolding` 변환에 명시적 매핑 추가:
  ```ts
  pricePnl:  raw.price_pnl ?? null,
  fxPnl:     raw.fx_pnl ?? null,
  fxWarning: raw.fx_warning ?? null,
  ```
- [ ] `toPortfolioSummary` 변환에 명시적 매핑 추가:
  ```ts
  convertedPricePnl: raw.converted_price_pnl ?? null,
  convertedFxPnl:    raw.converted_fx_pnl ?? null,
  fxWarning:         raw.fx_warning ?? null,
  ```
- [ ] API URL / TanStack Query 키 변경 없음 — 기존 그대로.

### Helper — 분해 표시 포맷터 (`frontend/src/lib/format.ts`)

- [ ] 신규 helper `formatPnlSplit(pricePnl, fxPnl, currency)`:
  ```
  Input:  pricePnl="80000", fxPnl="20000", currency="KRW"
  Output: "가격 +80,000 · 환차 +20,000"
  ```
  - 둘 다 non-null 일 때만 detail string 반환. 하나라도 null 이면 `null` 반환 → 컴포넌트에서 라벨 숨김.
  - 양수/음수 부호 처리 (`+` / `-`) 일관.
  - `formatCurrency` 또는 컴팩트 포맷 재사용.
  - 단위 테스트 작성.

### Holdings Table — 데스크톱 (`frontend/src/components/features/portfolio/holdings-table.tsx`)

- [ ] 손익 셀 (`<td>` — `dispPnl` 계산 부분) 수정:
  - **정상 분해 표시 조건**: `holding.fxWarning === null && holding.pricePnl !== null && holding.fxPnl !== null && holding.displayCurrency !== null && holding.assetSymbol.currency !== holding.displayCurrency` (즉 환산 모드 + 외화 자산 + 분리값 정상)
  - 표시 패턴 (한 줄): `+100,000원 (가격 +80,000 · 환차 +20,000)` — 폭이 빠듯하면 컴팩트 (K 단위 또는 두 번째 줄)
  - **`fxWarning === "missing_historical_rate"`**: 기존 `dispPnl` 만 표시 + 작은 인포 아이콘 (`<FxWarningInfo reason="missing_historical_rate" />`) — tooltip "아직 거래일 환율 기록이 없어 분리 표시 불가"
  - **`fxWarning === "missing_current_rate"`**: 기존 `dispPnl` 만 표시 + 인포 아이콘 — tooltip "현재 환율 캐시 없음. 잠시 후 다시 시도"
  - **동일 통화** (`holding.assetSymbol.currency === holding.displayCurrency` 또는 환산 비활성): 분해 라벨 숨김 (분해 의미 없음). 인포 아이콘도 표시하지 않음.
- [ ] 정렬은 기존 `pnlAbs` 기준 그대로.

### Holdings List — 모바일 (`frontend/src/components/features/portfolio/holdings-list.tsx`)

- [ ] 동일 분해 표시. 모바일 폭에서 한 줄에 안 들어가면 두 번째 줄로:
  ```
  +100,000원 (+5.2%)
  가격 +80,000 · 환차 +20,000
  ```
- [ ] fallback / 동일 통화 분기 동일.

### Summary Cards (`frontend/src/components/features/portfolio/summary-cards.tsx`)

- [ ] "미실현 손익" 카드의 `pnlMain` 렌더링 수정:
  - **정상 분해 조건**: `summary.convertedPricePnl !== null && summary.convertedFxPnl !== null && summary.fxWarning === null` 일 때:
    ```
    +1,000,000원
    가격 +800,000 · 환차 +200,000
    ```
  - **`fxWarning !== null`**: 기존 합산만 표시 + 작은 인포 아이콘
  - **동일 통화 only** (KRW only — 환산 비활성, `summary.convertedPnlAbs === null` 또는 `summary.convertedPricePnl === null`): 분해 라벨 숨김
- [ ] 색상: `pnlColor(convertedPnlAbs)` 그대로 (총합 기준). 분해값에 별도 색 입히지 않음.

### 신규 컴포넌트 — `FxWarningInfo` (`frontend/src/components/features/portfolio/fx-warning-info.tsx`)

- [ ] 작은 inline 인포 아이콘 (i 또는 ⓘ). props: `reason: "missing_historical_rate" | "missing_current_rate"`
- [ ] 텍스트 / tooltip:
  - `missing_historical_rate` → label "환율 데이터 누적 중", tooltip "아직 거래일 환율 기록이 없어 가격/환차 분해 불가. 다음 환율 갱신부터 누적됩니다."
  - `missing_current_rate` → label "현재 환율 부족", tooltip "현재 환율 캐시 없음. 잠시 후 다시 시도"
- [ ] shadcn/ui `Tooltip` 또는 단순 `title` 속성 (기존 `StaleBadge`/`PendingBadge` 패턴 따라가기)
- [ ] `aria-label` 명시.

### Tests (`frontend/src/components/features/portfolio/__tests__/`)

> frontend/CLAUDE.md MUST: 라인 커버리지 ≥ **90%**.

- [ ] `holdings-table.test.tsx` — 3 분기 검증:
  - **정상**: USD asset, convert_to=KRW, `pricePnl="80000"`, `fxPnl="20000"`, `fxWarning=null` → DOM 에 "가격" 과 "환차" 라벨 모두 존재
  - **missing**: `fxWarning="missing_historical_rate"` → 분해 라벨 부재 + 인포 아이콘 존재
  - **same_currency** (`holding.assetSymbol.currency === holding.displayCurrency`, 또는 환산 비활성): 분해 라벨 부재, 인포 아이콘도 없음
  - 추가: pending holding (`isPending=true`) → 분해 라벨 부재 + "—"

- [ ] `holdings-list.test.tsx` — 동일 3 분기

- [ ] `summary-cards.test.tsx`:
  - 정상: `convertedPricePnl="800000"`, `convertedFxPnl="200000"`, `fxWarning=null` → 두 라벨 존재
  - missing: `fxWarning="missing_historical_rate"` → 분해 라벨 부재 + 인포 아이콘
  - 동일 통화 only (`convertedPnlAbs=null`) → 기존 per-currency 표시 유지, 분해 부재

- [ ] `format.test.ts` (또는 `formatPnlSplit.test.ts`):
  - 양수 / 음수 / 0 / null 입력 모든 분기

- [ ] `fx-warning-info.test.tsx`:
  - 두 reason 별 텍스트·tooltip 검증, aria-label 검증

- [ ] `lib/api/portfolio.test.ts`:
  - `toHolding` / `toPortfolioSummary` 가 신규 3+3 필드 정상 매핑
  - raw 응답에 신규 필드 부재 시 기본값 null

## 구현 제약 (`frontend/CLAUDE.md` 와 충돌 회피)

- **MUST**: Named export 만.
- **MUST**: TypeScript strict. `any` 금지 — `fxWarning` 은 union literal type.
- **MUST**: TanStack Query v5 — 본 PR 은 기존 `useQuery` 그대로.
- **MUST**: Tailwind 만. 색상은 `pnlColor`, `text-toss-textWeak` 재사용.
- **MUST**: 접근성 — `FxWarningInfo` 에 `aria-label`. tooltip 키보드 접근 가능.
- **NEVER**: `console.log` — dev-only 가드.
- **NEVER**: `useEffect` 안 fetch.
- **NEVER**: 컴포넌트 파일 안 비즈니스 로직 — 분해 포맷팅은 `lib/format.ts` 의 helper 로 분리.

## 다른 역할과의 계약 (Interface)

- **← backend 가 제공** (response schema):
  ```
  HoldingResponse {
    ...existing,
    price_pnl:  string | null,
    fx_pnl:     string | null,
    fx_warning: "missing_historical_rate" | "missing_current_rate" | "same_currency" | null,
  }
  PortfolioSummaryResponse {
    ...existing,
    converted_price_pnl: string | null,
    converted_fx_pnl:    string | null,
    fx_warning:          "missing_historical_rate" | "missing_current_rate" | "same_currency" | null,
  }
  ```
- **불변식**: backend 가 `Decimal(price_pnl) + Decimal(fx_pnl) ≈ Decimal(converted_pnl_abs)` 보장 — frontend 별도 검증 불필요. 단 dev-only assert 추가 가능.
- **계약 변경 시**: PRD §8 먼저 갱신 → 양쪽 동기화.

## 실행 지시

이 프롬프트를 받은 agent 는:

1. `frontend/CLAUDE.md` 정독
2. PRD `docs/specs/fx-pnl-split.md` §5, §6.4, §8 정독
3. 기존 코드 정독: `types/portfolio.ts`, `lib/api/portfolio.ts`, `holdings-table.tsx`, `holdings-list.tsx`, `summary-cards.tsx`, `lib/format.ts`
4. **변경 순서**: Types → API Layer → format helper → FxWarningInfo → holdings-table → holdings-list → summary-cards → Tests
5. 검증:
   - `npm run test -- --coverage`. 라인 ≥ **90%**
   - `npx tsc --noEmit`
   - `npm run lint`
6. 완료 후 리포트:
   - 변경된 파일 목록
   - `FxWarningInfo` 사용 위치
   - 백엔드 의존: `fx_warning` enum 값 ("missing_historical_rate" / "missing_current_rate" / "same_currency") — backend 와 동일 사용 중인지 재확인
   - 실패한 테스트 (있다면) + 원인

## 성공 기준

- [ ] 신규 6개 필드 (Holding 3 + Summary 3) 모두 type + raw + 변환 매핑
- [ ] holdings-table / holdings-list / summary-cards 에서 정상 / missing / same_currency 3 분기 처리
- [ ] `FxWarningInfo` 컴포넌트 신규 + 두 reason 모두 텍스트/tooltip 동작
- [ ] RTL 테스트 5개 파일 모두 통과 (holdings-table, holdings-list, summary-cards, format, fx-warning-info, api/portfolio)
- [ ] 라인 커버리지 ≥ **90%**
- [ ] tsc strict 통과, ESLint 통과
- [ ] 기존 테스트 0건 회귀
