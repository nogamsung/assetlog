# UI / Mobile Polish — frontend (Next.js) 구현 프롬프트 (토스 스타일)

> 이 파일은 `/planner` 가 생성한 **frontend 단독 구현 지시서**입니다.
> 대응 PRD: [`../ui-mobile-polish.md`](../ui-mobile-polish.md) — **§9.5 토스 디자인 언어 반드시 먼저 읽을 것**
> 대응 스택: nextjs (경로: `frontend`)
> 사용 agent: `nextjs-modifier` (대부분 기존 파일 수정), 신규 파일은 `nextjs-generator`
> **시각 기조**: 토스(Toss) 앱 — 큰 숫자, 넉넉한 여백, 둥근 카드(rounded-2xl), 단색 토스블루 강조, 한국식 손익색(상승=빨강 / 하락=파랑), 모바일 바텀시트.

---

## 맥락 (꼭 읽을 것)

- PRD 본문: `../ui-mobile-polish.md` — 특히 §9 (모바일 가이드라인) / §10 (changeset) / §11 (리스크)
- 스택 규칙: `frontend/CLAUDE.md` — Tailwind, named export, RHF+Zod, no `any`, TanStack Query
- 디자인 토큰: `.claude/skills/ui-design-impl.md`, `frontend/src/app/globals.css`
- 기존 포매터: `frontend/src/lib/format.ts`, `frontend/src/lib/chart-format.ts`
- 작업 브랜치 / worktree: `feature/ui-mobile-polish` → `.worktrees/feature-ui-mobile-polish/`

## 이 역할의 책임

PRD §10 의 모든 changeset 을 frontend 에서 구현. backend 호출·계약 변경 없음.

- 포함: 포매터 확장, 글로벌 layout, 대시보드 / 자산 / 현금 / 거래 / 설정 / 인증 컴포넌트의 mobile-first 보강, 신규 모바일 카드 컴포넌트, UI primitives 확장, 단위/스모크 테스트.
- 제외: 새 라우트, 새 hooks (기존 재사용), backend 호출 시그니처 변경, 차트 라이브러리 교체, 디자인 토큰 색상 추가.

## 작업 순서 (반드시 이 순서)

0. **토스 디자인 토큰** — `globals.css` CSS 변수, Pretendard 폰트, `tailwind.config.ts` `theme.extend.colors.toss`, `lib/toss-tokens.ts` (class 상수). 이 작업이 끝나야 이후 모든 컴포넌트 작업이 토스 스타일로 통일됨.
1. **포매터** — 다른 모든 표시의 입구. 시그니처 호환 유지, 옵션 추가 방식. `pnlColor` 는 토스 컬러(toss-up/toss-down) 반환.
2. **포매터 단위 테스트** — 분기 매트릭스 통과 후 다음 단계로.
3. **글로벌 layout / globals.css** — sticky 헤더(토스 스타일), font-family 정정(Pretendard), iOS auto-zoom 방지 CSS.
4. **UI primitives** — `Button` 토스 variant 3종(`toss-primary`, `toss-secondary`, `toss-destructive`) + `icon-touch` 사이즈, `Input`/`Card` 토스 토큰 적용, `Dialog` 모바일 바텀시트 variant.
5. **고-트래픽 페이지 우선** — 대시보드(`SummaryCards` 의 큰-숫자 hero, `HoldingsTable` + 신규 `HoldingsList`).
6. **그 외 페이지로 전파** — 자산 목록·상세, 현금, 거래 일괄, 설정, 로그인 순. **모든 컴포넌트는 토스 토큰 사용**.
7. **컴포넌트 스모크 테스트** — 모바일 viewport 가정 케이스 + 토스 토큰 적용 확인.
8. **수동 회귀 체크리스트** 수행 후 PR.

## 변경/생성할 파일 (체크리스트)

### 토스 디자인 토큰 (0단계 — 가장 먼저)
- [ ] `frontend/src/app/globals.css` — PRD §9.5.7 의 CSS 변수 블록을 `@layer base { :root { ... } .dark { ... } }` 에 그대로 추가. `body` 의 `font-family` 를 Pretendard 우선으로 정정. `font-feature-settings: 'tnum' 1` 으로 tabular nums 기본화.
- [ ] **Pretendard 폰트** — 두 가지 옵션 중 택1:
  - (A) CDN: `globals.css` 상단에 `@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');`
  - (B) self-host: `frontend/src/app/layout.tsx` 에 `next/font/local` 로 woff2 호스팅 — 1차는 (A) 채택해 빠르게.
- [ ] `frontend/tailwind.config.ts` — `theme.extend.colors.toss` 추가:
  ```ts
  toss: {
    blue: 'var(--toss-blue)',
    blueBg: 'var(--toss-blue-bg)',
    up: 'var(--toss-up)',
    down: 'var(--toss-down)',
    bg: 'var(--toss-bg)',
    card: 'var(--toss-card)',
    border: 'var(--toss-border)',
    text: 'var(--toss-text)',
    textStrong: 'var(--toss-text-strong)',
    textWeak: 'var(--toss-text-weak)',
    textDisabled: 'var(--toss-text-disabled)',
  }
  ```
  → 클래스 사용: `bg-toss-card`, `text-toss-up`, `border-toss-border` 등.
- [ ] **신규** `frontend/src/lib/toss-tokens.ts` — class 상수 export. 컴포넌트는 이 상수를 import.
  ```ts
  export const tossCard = 'rounded-2xl border border-toss-border bg-toss-card p-5 sm:p-6';
  export const tossCardTappable = `${tossCard} active:scale-[0.99] transition-transform duration-100 cursor-pointer`;
  export const tossButtonPrimary = 'inline-flex h-12 sm:h-11 w-full sm:w-auto items-center justify-center rounded-xl bg-toss-blue px-5 font-bold text-white transition-all active:scale-[0.98] hover:brightness-95 disabled:opacity-50';
  export const tossButtonSecondary = 'inline-flex h-12 sm:h-11 w-full sm:w-auto items-center justify-center rounded-xl bg-toss-card px-5 font-medium text-toss-text border border-toss-border active:scale-[0.98] hover:bg-toss-border';
  export const tossButtonDestructive = 'inline-flex h-12 sm:h-11 items-center justify-center rounded-xl bg-toss-up/10 px-5 font-bold text-toss-up active:scale-[0.98]';
  export const tossInput = 'h-12 w-full rounded-xl border border-toss-border bg-toss-card px-4 text-base text-toss-textStrong placeholder:text-toss-textDisabled focus:border-toss-blue focus:outline-none focus:ring-2 focus:ring-toss-blue/20';
  export const tossLabel = 'text-sm font-medium text-toss-textWeak mb-2 block';
  export const tossPageHeading = 'text-2xl sm:text-3xl font-bold tracking-tight text-toss-textStrong';
  export const tossSectionHeading = 'text-lg sm:text-xl font-bold text-toss-textStrong';
  export const tossHeroNumber = 'text-4xl sm:text-5xl font-bold tracking-tight tabular-nums text-toss-textStrong';
  export const tossCardNumber = 'text-2xl sm:text-3xl font-bold tracking-tight tabular-nums text-toss-textStrong';
  ```

### 포매터 (1단계)
- [ ] `frontend/src/lib/format.ts` — 변경:
  - `formatCurrency(amount, currency, options?)` 의 옵션 인자 추가:
    - `compact?: boolean` (default false) — true 면 `notation:"compact"`.
    - `trimTrailingZeros?: boolean` (default **true** — 새 기본값. 기존 호출 회귀 점검).
  - 통화 카테고리 헬퍼 내부 추가: `INTEGER_CURRENCIES = new Set(["KRW","JPY"])`, `STABLE_LIKE = new Set(["USDT","USDC","DAI","BUSD"])`.
  - `formatPercent(pct, digits=2)` — trailing zero 제거 (`Number(pct.toFixed(digits))` 후 출력) + 부호 옵션 `withSign?: boolean`.
  - `formatQuantity(qty, assetType)` — trailing zero 제거 (이미 `toLocaleString` + `maximumFractionDigits` 만 있는 상태이므로 trailing zero 가 자연 제거됨 — 테스트로만 확인).
  - 신규: `formatCompactCurrency(amount, currency)` — 모바일 카드용. ko-KR locale + `notation:"compact"`.
  - 신규: `pnlColor(value: string | number): string` — `+` / `−` / `0` 분기 후 Tailwind class 문자열 반환. **토스 컬러 적용** — `text-toss-up` / `text-toss-down` / `text-toss-textWeak`. (한국 금융 관습: 상승=빨강 toss-up, 하락=파랑 toss-down. 다크모드 자동 — CSS 변수 기반.)
  - 신규: `formatSignedCurrency(amount, currency, options?)` — 부호 자동 부착(`+`/`−`).

- [ ] `frontend/src/__tests__/lib/format.test.ts` — 케이스 추가:
  - KRW `1500000.00` → `₩1,500,000`
  - USD `1234.50` → `$1,234.5` (trim) / `$1,234` for `1234.00`
  - USDT `1234.5000` → `1,234.5 USDT`
  - `formatPercent(13.6400)` → `13.64%`, `formatPercent(13.0)` → `13%`, `formatPercent(0)` → `0%`
  - `formatQuantity("10.0000","stock")` → `10`, `("0.12345678","crypto")` → `0.12345678`
  - `formatCompactCurrency(120000000, "KRW")` → `₩1.2억` (ko-KR compact)
  - `pnlColor("0")` → muted, `("100")` → emerald, `("-1")` → rose
  - `formatSignedCurrency("1234","USD")` → `+$1,234`, `("-1234","USD")` → `-$1,234`, `("0","USD")` → `$0`

### 글로벌 layout (3단계)
- [ ] `frontend/src/app/(app)/layout.tsx` — 헤더 sticky (`sticky top-0 z-40 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b`), nav 를 `hidden sm:flex`, 모바일은 햄버거 IconButton + 모바일 메뉴 시트 또는 단순 inline 축약 (PRD §14 Open Issue 1 에 따라 1차는 inline 유지 + sticky).
  - `aria-current="page"` — Next.js `usePathname()` 사용.
  - 메뉴 토글은 `useState` 클라이언트.
- [ ] `frontend/src/app/globals.css` — `body` `font-family` 를 `var(--font-sans)` 로 정정. iOS auto-zoom 방지 CSS rule 추가:
  ```css
  @layer base {
    input, select, textarea {
      font-size: 16px; /* iOS Safari zoom 방지 */
    }
    @media (min-width: 640px) {
      input, select, textarea { font-size: 0.875rem; }
    }
  }
  ```

### UI primitives (4단계 — 토스 토큰 일괄 적용)
- [ ] `frontend/src/components/ui/button.tsx`
  - `size` variants 에 `"icon-touch": "h-11 w-11"` 추가.
  - **토스 variants 추가** — `tossPrimary`, `tossSecondary`, `tossDestructive`. 기존 `default` / `secondary` / `destructive` 의 클래스 정의도 토스 토큰을 참조하도록 매핑(파괴 변경 X, 색만 토스화):
    - `default`: `bg-toss-blue text-white font-bold rounded-xl active:scale-[0.98] hover:brightness-95`
    - `secondary`: `bg-toss-card text-toss-text border border-toss-border rounded-xl active:scale-[0.98]`
    - `destructive`: `bg-toss-up/10 text-toss-up font-bold rounded-xl active:scale-[0.98]`
    - `outline`: `border border-toss-border bg-transparent rounded-xl`
    - `ghost`: `text-toss-text hover:bg-toss-card rounded-xl`
  - 라운드는 모두 `rounded-xl` (12px). `rounded-md` 사용처 제거.
- [ ] `frontend/src/components/ui/input.tsx`
  - 토스 토큰 적용 — `h-12 rounded-xl border-toss-border bg-toss-card text-toss-textStrong placeholder:text-toss-textDisabled focus:border-toss-blue focus:ring-2 focus:ring-toss-blue/20 text-base`. 기존 `text-sm` → `text-base` (모바일 zoom 방지 겸).
- [ ] `frontend/src/components/ui/card.tsx`
  - `Card` 기본 클래스를 `rounded-2xl border-toss-border bg-toss-card text-toss-text` 로 변경. **`shadow-sm` 등 그림자 클래스 제거**.
  - `CardHeader` `p-5 sm:p-6 pb-3`, `CardContent` `p-5 sm:p-6 pt-0`, `CardFooter` `p-5 sm:p-6 pt-0` 로 토스 패딩.
- [ ] `frontend/src/components/ui/badge.tsx`
  - 손익 pill 용 `tossUp` / `tossDown` variant 추가 — `bg-toss-up/10 text-toss-up rounded-full text-sm font-bold px-2.5 py-0.5` (down 동일 패턴).
- [ ] **신규** `frontend/src/components/ui/bottom-sheet.tsx`
  - 모바일에서 `Dialog` 대체 컴포넌트. Radix Dialog 위에 `DialogContent` 를 모바일 미디어쿼리로 하단 슬라이드 시트로 변환:
    - `sm` 미만: `fixed inset-x-0 bottom-0 rounded-t-3xl bg-toss-bg p-5 max-h-[90vh] overflow-y-auto pb-[env(safe-area-inset-bottom)]` + `data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-full duration-200`
    - `sm` 이상: 기존 중앙 다이얼로그 유지(`rounded-2xl`).
  - 시트 상단 핸들 바 자동 렌더(`<div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-toss-border sm:hidden" />`).
  - export: `BottomSheet`, `BottomSheetTrigger`, `BottomSheetContent`, `BottomSheetHeader`, `BottomSheetTitle`, `BottomSheetFooter`.
- [ ] **선택**: 기존 `dialog.tsx` 가 있다면 그것 위에서 변형하고, 없으면 `BottomSheet` 가 `Dialog` 의 super set 으로 동작하도록.

### 대시보드 (5단계 — 토스 시그니처 화면)
- [ ] `frontend/src/components/features/portfolio/summary-cards.tsx`
  - **첫 카드(총자산)는 hero 카드** — 별도 영역으로 빼서 큰 숫자 한 개를 압도적으로 표시:
    - 라벨 `"총 자산"` → `text-sm font-medium text-toss-textWeak`
    - 숫자 → `tossHeroNumber` (`text-4xl sm:text-5xl font-bold tabular-nums`)
    - 보조 한 줄에 `오늘 +12,345 (+0.34%)` 형태 — `pnlColor` 적용.
    - 카드 자체는 `tossCard` 사용, 그림자 없음, rounded-2xl.
  - 나머지 카드(현금, 투자, 손익): grid `grid-cols-2 lg:grid-cols-3`, 각 카드는 `tossCard` + `tossCardNumber`.
  - `formatCompactCurrency` 사용 (`hasConversion` 일 때 + 큰 값 한정 — 1e8 KRW / 1e6 USD 이상 휴리스틱).
  - `pnlColor` 헬퍼로 색상 분기 통일.
  - 기존 `text-emerald` / `text-rose` / `text-green` / `text-red` 클래스 흔적 모두 제거.
- [ ] `frontend/src/components/features/portfolio/holdings-table.tsx`
  - 최상위 `<div>` 에 `hidden sm:block` 추가.
- [ ] **신규** `frontend/src/components/features/portfolio/holdings-list.tsx`
  - `block sm:hidden`. 정렬 메뉴는 dropdown 으로 압축.
  - **토스 리스트 패턴** — 카드 한 개 안에 행을 나열, 행 사이 구분선 없이 `py-4` 패딩으로만 분리:
    - 좌측: 원형 아이콘(`h-10 w-10 rounded-full bg-toss-blueBg text-toss-blue grid place-items-center font-bold text-sm`) + 종목명·심볼 (`font-bold text-base text-toss-textStrong` / `text-sm text-toss-textWeak`)
    - 우측: 평가액(`tabular-nums font-bold text-base`) + 손익 한 줄(`text-sm` 토스컬러, 화살표 아이콘 동반 `▲▼`)
  - 행 자체에 `active:scale-[0.99] transition-transform` (탭 피드백).
  - 빈 상태(`empty state`): 토스 스타일 일러스트 대신 큰 텍스트 + 보조 (`text-toss-textWeak`).
- [ ] `frontend/src/components/features/portfolio/dashboard-view.tsx`
  - `<HoldingsTable />` 와 `<HoldingsList />` 를 함께 렌더 (한쪽이 미디어 쿼리로 숨김).
  - `space-y-6` → `space-y-6 sm:space-y-8` 검토.
- [ ] `frontend/src/components/features/portfolio/portfolio-history-chart.tsx` — 컨테이너 height 모바일 240 / sm 320.
- [ ] `frontend/src/components/features/portfolio/tag-breakdown-table.tsx` — 모바일 가로 스크롤 + 첫 컬럼 sticky (가벼운 fallback).

### 자산 (6단계)
- [ ] `frontend/src/components/features/assets/asset-list.tsx`
  - 모바일 카드에 평가액 / 손익(±%) 추가 노출 (현재는 `hidden md:flex` 라 숨김). 모바일에 별도 영역.
  - 액션 버튼 `size="icon-touch"`.
- [ ] `frontend/src/components/features/assets/asset-detail.tsx`
  - 카드 padding `p-4 sm:p-6`, `dl` grid 유지.
  - 거래 내역 헤더의 `<div className="flex items-center justify-between">` 가 모바일에서 줄바꿈 가능하도록 `flex-wrap`.
- [ ] `frontend/src/components/features/assets/transaction-list.tsx`
  - 인라인 SVG 삭제 → `Trash2` from lucide.
  - 액션 버튼 `min-h-11 min-w-11` 또는 `Button size="icon-touch"`.
  - 메모 / 태그 표시: 모바일에서 메모는 새 줄로 wrap, 태그는 카드 하단 한 줄.
- [ ] `frontend/src/components/features/assets/transaction-form.tsx`
  - 입력 그리드 모바일 1열, sm 2열.
- [ ] `frontend/src/components/features/assets/transaction-import.tsx` — 모바일 padding 정리.

### 현금 (6단계)
- [ ] `frontend/src/components/features/cash/cash-account-list.tsx`
  - `formatCurrencySafe` 제거 → `lib/format.ts` 통합 포매터 사용 (이미 `formatCurrency` 가 fallback 처리하므로 단일화 가능).
  - 잔액 표시는 카테고리 룰에 따라 trailing zero 제거.
- [ ] `frontend/src/components/features/cash/cash-account-add-dialog.tsx`, `cash-account-edit-dialog.tsx`, `cash-account-delete-dialog.tsx`
  - dialog `mx-4 max-w-md`, 입력 16px, 버튼 행 `flex-col-reverse sm:flex-row sm:justify-end` (모바일 primary 액션이 위로).

### 거래 일괄 (6단계)
- [ ] `frontend/src/components/features/transactions/bulk-import-dialog.tsx`
  - dialog body `pb-[env(safe-area-inset-bottom)]`.
  - 탭 버튼 `min-h-11`.
- [ ] `frontend/src/components/features/transactions/bulk-grid-tab.tsx`
  - 그리드 셀 input `text-base`, 가로 스크롤 컨테이너 right-edge gradient hint.
- [ ] `frontend/src/components/features/transactions/bulk-csv-tab.tsx`
  - drop zone `h-32 sm:h-40`.

### 설정 / 인증 (6단계)
- [ ] `frontend/src/app/(app)/settings/page.tsx` — 다운로드 버튼 `w-full sm:w-auto`.
- [ ] `frontend/src/app/(auth)/login/page.tsx` & `frontend/src/components/features/auth/login-form.tsx` — 카드 `mx-4 max-w-sm`, 입력 16px.

### 차트 / 기타
- [ ] `frontend/src/lib/chart-format.ts` — `formatCurrencyValue` 가 새 통화 카테고리 룰을 따르도록 위임 (내부에서 `formatCurrency` 호출 또는 분기 통합).

### 테스트 (7단계)
- [ ] `frontend/src/__tests__/lib/format.test.ts` — 위 매트릭스.
- [ ] `frontend/src/__tests__/components/holdings-list.test.tsx` — 신규.
- [ ] `frontend/src/__tests__/components/summary-cards.test.tsx` — 컴팩트 표기 분기.
- [ ] 기존 테스트(`format.test.ts`, `chart-format.test.ts`) 가 새 trailing-zero 정책과 호환되도록 expect 갱신.

## 구현 제약 (frontend/CLAUDE.md 와 충돌 금지)

- **TypeScript strict, no `any`** — 새 옵션 인자도 명시 타입.
- **named export 만**. `default` 는 `page.tsx` / `layout.tsx` 에서만 허용.
- **TanStack Query 만**. `useEffect + fetch` 금지.
- **Tailwind 만**. 인라인 `style` 금지.
- **`<img>`** 직접 사용 금지 — `next/image`.
- **`loading.tsx` / `error.tsx`** 변경 안 함 (이미 존재).
- **`console.log` 프로덕션 금지**.
- **테스트 없이 신규 컴포넌트 추가 금지** (HoldingsList, BottomSheet 에는 반드시 테스트).
- **기본 시그니처 호환** — `formatCurrency(amount, currency)` 두 인자 호출이 그대로 동작해야 한다. 새 옵션은 세 번째 선택 인자.
- **토스 컬러 일관성** — `text-emerald-*`, `text-rose-*`, `text-green-*`, `text-red-*` 흔적을 손익 표시에서 **모두 제거**. `pnlColor` / `text-toss-up` / `text-toss-down` 으로만 표현.
- **다크 모드 parity** — CSS 변수 기반(`--toss-*`)이라 다크모드 자동 대응. 단 일부 그림자·border 강도 시각 회귀 확인 필수.
- **그림자 사용 최소화** — 카드에 `shadow*` 클래스 신규 추가 금지. 기존 `shadow-sm` 등은 토스 작업하며 제거. 떠야 할 다이얼로그/시트만 예외(`shadow-2xl`).
- **라운드 일관성** — 카드 `rounded-2xl`, 버튼/입력 `rounded-xl`, pill `rounded-full`. 그 외(`rounded-md`, `rounded-lg`, `rounded` 단독) 흔적 정리.

## 다른 역할과의 계약

- **← backend 가 제공**: 모든 Decimal 필드는 string. 변경 없음. 응답 스키마 동일.
- **frontend → backend 호출**: 변경 없음. 표시 전용 작업.

## 실행 지시 (agent 가 수행)

1. `frontend/CLAUDE.md` 와 `.claude/skills/ui-design-impl.md` 를 읽는다.
2. PRD §10 의 changeset 을 위 순서대로 처리.
3. 각 컴포넌트 변경 시 다크/라이트 양쪽 시각 회귀 검토용 메모를 PR 설명에 남긴다.
4. `npx tsc --noEmit` → `npm run lint` → `npx jest --coverage` 통과 확인.
5. 라인 커버리지 < 90% 면 테스트 보강.
6. 완료 리포트:
   - 생성된 파일 목록
   - 변경된 기존 파일 목록
   - 새로 추가한 utility (예: `pnlColor`, `formatCompactCurrency`)
   - 모바일 viewport 수동 회귀 결과 (375 / 414 / 768, dark/light)
   - 알려진 trade-off (예: 컴팩트 표기 정밀도 손실 — tooltip 미적용 시 후속 이슈)

## 성공 기준

- PRD §2 의 측정 가능 수락 기준 모두 충족.
- 체크리스트 항목 전부 체크.
- `npx jest --coverage` 라인 ≥ 90%.
- `npx tsc --noEmit` / `npm run lint` 0 error.
- 다크/라이트 양쪽 5개 핵심 페이지 시각 회귀 없음.
- 가로 스크롤이 발생하는 페이지가 없음 (375px 기준).

---

> 이 프롬프트는 `/planner` 가 자동 생성. 작업 시작 전 PRD §14 의 Open Issue 1~4 에 대한 사용자 결정을 확인할 것.
