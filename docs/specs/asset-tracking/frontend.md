---
feature: asset-tracking
role: frontend
stack_type: nextjs
stack_path: frontend
created_at: 2026-04-23
status: Draft
related_prd: ../asset-tracking.md
related_api_contract: ../../api/asset-tracking.yaml
---

# asset-tracking — frontend 구현 프롬프트

> 이 파일은 `/planner` 가 생성한 **frontend 역할 구현 지시서**입니다.
> 대응 PRD: [`../asset-tracking.md`](../asset-tracking.md)
> 대응 스택: **nextjs** (경로: `frontend`)
> 전제된 Agent: `nextjs-generator` · `nextjs-modifier` · `nextjs-tester`

---

## 0. 맥락 (반드시 먼저 읽기)

| 파일 | 목적 |
|------|------|
| `../asset-tracking.md` | PRD 본문 — 유저 스토리 · API 계약 · 비기능 요구 |
| `frontend/CLAUDE.md` | 스택 규칙 (MUST / NEVER) — 이 규칙을 통과해야 함 |
| `.claude/stacks.json` | monorepo 매니페스트 (`role: frontend, path: frontend`) |
| `.claude/skills/nextjs-patterns.md` | 패턴 스킬 |
| `.claude/skills/ui-design-impl.md` | 디자인 토큰 |
| `memory/MEMORY.md` | **Node ≥ 20.9.0 필요** (현재 18.20.8 — nvm 업그레이드 필수) |

---

## 1. 목표

AssetLog MVP 의 **사용자 인터페이스 전부** 구현.

- 이메일·비밀번호 **회원가입 / 로그인**
- **대시보드** — 총 평가액, 총 손익, 자산 클래스별 비중, 보유 자산 테이블
- **자산 추가 플로우** — 심볼 검색 → 수량·단가·매수일 입력 → 저장
- **자산 목록 / 삭제**
- **거래 기록 추가** (기보유 자산에 매수 내역 append)
- 한국어 UI (`ko-KR`)

---

## 2. 스택 전제 (frontend/CLAUDE.md 와 일치)

| 영역 | 선정 |
|------|------|
| 프레임워크 | Next.js 16 (App Router) — 현재 `package.json` 16.2.4 |
| 언어 | TypeScript **strict**, `any` 금지 |
| 스타일 | Tailwind CSS 4 + shadcn/ui (신규 도입) |
| 서버 상태 | TanStack Query v5 (신규 도입) |
| 클라이언트 UI 상태 | Zustand (필요 시) |
| 폼 | React Hook Form + Zod |
| HTTP | Axios (`lib/api-client.ts`) + JWT interceptor |
| 테스트 | Jest + React Testing Library (커버리지 ≥ 90%) |
| 런타임 | Node ≥ 20.9.0 (빌드 전 `nvm use` 필수) |

### 환경 제약 (MEMORY 반영)
- 로컬 Node 18.20.8 — Next.js 16 은 20.9+ 필요. `.nvmrc` 에 `20.11.0` (LTS) 고정하고 README 에 안내.
- 작업 시 `nvm use` 를 상단에 적용.

### 현 스캐폴드 상태
`frontend/src/` 에는 App Router 기본 (`app/layout.tsx`, `app/page.tsx`, `app/globals.css`) + `lib/api.ts` 한 줄짜리만 존재. **대부분 신규 작성**.

---

## 3. 신규 패키지 (frontend/package.json 에 추가)

```
# dependencies
@tanstack/react-query
axios
react-hook-form
zod
@hookform/resolvers
zustand
clsx
tailwind-merge
class-variance-authority
lucide-react                 # 아이콘
date-fns                     # 날짜 포맷 (Asia/Seoul 변환 포함)

# devDependencies
jest
jest-environment-jsdom
@testing-library/react
@testing-library/jest-dom
@testing-library/user-event
@types/jest
ts-jest
msw                          # API mock (TanStack Query 훅 테스트용)
```

- [ ] shadcn/ui 초기화 (`npx shadcn@latest init`) — Button, Input, Dialog, Table, Select, Badge, Card, Toast 추가
- [ ] `jest.config.ts` 에 `coverageThreshold.global.lines: 90`, `coverageReporters: ['json-summary','text','lcov']`

---

## 4. 라우트 구조 (App Router)

```
src/
├── app/
│   ├── layout.tsx                        # 루트 (QueryClientProvider, ToastProvider)
│   ├── page.tsx                          # 랜딩 (비로그인 시 CTA, 로그인 시 /dashboard 리다이렉트)
│   ├── (auth)/
│   │   ├── layout.tsx                    # 인증 레이아웃 (비로그인 전용)
│   │   ├── signup/page.tsx               # 회원가입
│   │   └── login/page.tsx                # 로그인
│   ├── (app)/
│   │   ├── layout.tsx                    # 인증 필요 (AuthGuard). 헤더 + 사이드바
│   │   ├── dashboard/
│   │   │   ├── page.tsx                  # /dashboard
│   │   │   └── loading.tsx
│   │   ├── assets/
│   │   │   ├── page.tsx                  # /assets 목록
│   │   │   ├── loading.tsx
│   │   │   ├── error.tsx
│   │   │   └── new/
│   │   │       └── page.tsx              # /assets/new 플로우
│   │   └── settings/
│   │       └── page.tsx
│   └── globals.css
├── components/
│   ├── ui/                               # shadcn 프리미티브 (button, input, dialog, …)
│   └── features/
│       ├── auth/
│       │   ├── signup-form.tsx
│       │   ├── login-form.tsx
│       │   └── auth-guard.tsx            # Client, 토큰 없으면 /login redirect
│       ├── portfolio/
│       │   ├── portfolio-summary.tsx     # 총 평가액·손익 카드
│       │   ├── allocation-chart.tsx      # 클래스별 비중 (간단 progress bar)
│       │   └── holdings-table.tsx        # 보유 자산 테이블
│       ├── asset/
│       │   ├── asset-add-form.tsx        # 메인 폼 (RHF+Zod)
│       │   ├── symbol-search.tsx         # debounced 자동완성
│       │   ├── asset-list.tsx
│       │   └── asset-delete-dialog.tsx
│       └── transaction/
│           └── transaction-form.tsx
├── hooks/
│   ├── use-auth.ts                       # 로그인/로그아웃/상태
│   ├── use-signup.ts
│   ├── use-login.ts
│   ├── use-symbols-search.ts             # TanStack Query (debounce)
│   ├── use-user-assets.ts
│   ├── use-create-user-asset.ts
│   ├── use-delete-user-asset.ts
│   ├── use-transactions.ts
│   ├── use-create-transaction.ts
│   ├── use-portfolio-summary.ts
│   └── use-portfolio-holdings.ts
├── lib/
│   ├── api-client.ts                     # Axios 인스턴스 + JWT interceptor + 401 → /login
│   ├── query-client.ts                   # TanStack QueryClient factory
│   ├── format.ts                         # 통화·퍼센트·날짜(KST) 포맷터
│   ├── schemas/                          # Zod 스키마 (백엔드 응답과 동형)
│   │   ├── auth.ts
│   │   ├── symbol.ts
│   │   ├── user-asset.ts
│   │   ├── transaction.ts
│   │   └── portfolio.ts
│   └── env.ts                            # NEXT_PUBLIC_API_BASE_URL 검증
├── stores/
│   └── auth-store.ts                     # Zustand — token, user (persist middleware)
├── types/
│   └── api.ts                            # Zod 로부터 유추 or 수동 정의 — SSOT 는 Zod
└── providers/
    ├── query-provider.tsx                # QueryClientProvider 래퍼 (Client)
    └── toast-provider.tsx
```

> **Named export 만** — `default` 는 `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx` 등 라우팅 전용 파일에만.

---

## 5. 컴포넌트 & 화면 요구사항

### 5.1 인증
- [ ] **Signup form** (`signup-form.tsx`) — 이메일(Zod email), 비밀번호(min 8, 영문+숫자), 비번 확인
  - 제출 → `useSignup` 훅 → 성공 시 토큰 저장 + `/dashboard` 리다이렉트
  - 이메일 중복(409) → 인라인 에러
- [ ] **Login form** — 이메일/비밀번호
  - 실패(401) → "이메일 또는 비밀번호가 올바르지 않습니다" (계정 존재 여부 노출 금지)
- [ ] **AuthGuard** (Client Component) — Zustand 토큰 없으면 `/login` 으로 redirect
  - `/dashboard`, `/assets/**`, `/settings` 에 감싸기 (`(app)/layout.tsx`)

### 5.2 대시보드 (`/dashboard`)
- [ ] **PortfolioSummary 카드** (통화별 합계 — KRW·USD 각각)
  - 총 평가액 · 총 매수금액 · 총 손익(절대 + %)
  - 마지막 가격 갱신 시각 (Asia/Seoul 변환, "10분 전" 상대 표시 + 툴팁에 절대 시각)
- [ ] **AllocationChart** — 자산 클래스별 비중 (kr_stock / us_stock / crypto) — 심플 horizontal progress bar 3 개 + 퍼센트 라벨
- [ ] **HoldingsTable** — 열: 심볼 · 이름 · 수량 · 평균단가 · 현재가 · 평가액 · 손익(금액) · 손익(%) · 비중
  - 비중 내림차순 기본 정렬
  - `last_price_refreshed_at` 이 3시간 초과 시 해당 행에 `지연됨` 배지
  - 빈 상태: "첫 자산을 등록해보세요" CTA → `/assets/new`

### 5.3 자산 추가 (`/assets/new`)
- [ ] 스텝 1: **자산 클래스 선택** (라디오 그룹 — 국내주식/해외주식/암호화폐)
- [ ] 스텝 2: **SymbolSearch** — 입력 debounce 300ms → `useSymbolsSearch(q, type)` 자동완성 드롭다운
- [ ] 스텝 3: **수량 · 매수 단가 · 매수일** 입력 (React Hook Form + Zod)
  - 수량: `z.number().positive()` + 암호화폐만 소수점 8자리 허용
  - 매수일: `date-fns` + input[type=date] (Asia/Seoul)
- [ ] 제출 → `useCreateUserAsset` → 성공 토스트 + `/assets` 로 이동
- [ ] 중복 자산 경고: 기존 UserAsset 존재 시 "기존 자산에 매수 기록을 추가할까요?" 분기

### 5.4 자산 목록 (`/assets`)
- [ ] 테이블 + "자산 추가" 버튼 → `/assets/new`
- [ ] 행 액션: 상세 보기(펼치기로 거래 이력 표시) / 매수 기록 추가 / 삭제
- [ ] 삭제: `AssetDeleteDialog` (shadcn Dialog) 로 확인 후 진행

### 5.5 설정 (`/settings`)
- [ ] MVP 는 최소 — 로그아웃 버튼 + 사용자 이메일 표시만

---

## 6. 상태 / 데이터

### 6.1 API 클라이언트 (`lib/api-client.ts`)
- [ ] Axios 인스턴스 생성 — `baseURL = env.NEXT_PUBLIC_API_BASE_URL`
- [ ] 요청 인터셉터: Zustand auth-store 에서 토큰 읽어 `Authorization: Bearer` 부여
- [ ] 응답 인터셉터: 401 → auth-store 초기화 + `window.location = '/login'`
- [ ] 모든 훅은 이 인스턴스를 통해서만 호출. `fetch` 직접 사용 금지

### 6.2 TanStack Query 규칙
- [ ] `QueryClient` 는 `providers/query-provider.tsx` 에서 생성, `app/layout.tsx` 에 래핑
- [ ] Query key 상수: `queryKeys.userAssets()`, `queryKeys.portfolio.summary()` 등 (`lib/query-keys.ts`) — 문자열 하드코딩 금지
- [ ] Mutation 성공 시 `invalidateQueries` 로 관련 query 갱신
- [ ] `staleTime` 기본 60s (가격 갱신 주기 대비 과도한 재요청 방지)

### 6.3 Zustand auth-store
- [ ] 필드: `accessToken`, `user`, `setAuth`, `clear`
- [ ] `persist` middleware — **localStorage** (MVP. PRD 오픈 이슈 — backend 와 httpOnly cookie 전환 합의 여지)
- [ ] SSR 시 undefined 안전 가드 (`typeof window !== 'undefined'`)

### 6.4 Zod 스키마 = SSOT
- [ ] `lib/schemas/*.ts` 에 응답 스키마 정의 → `z.infer<typeof UserAssetResponseSchema>` 로 타입 추출
- [ ] API 클라이언트 응답 파싱 시 `Schema.parse(data)` — 런타임 검증
- [ ] 이 스키마와 backend 응답 (`docs/api/asset-tracking.yaml`) 은 **항상 동기화**

---

## 7. 인증 플로우 (상세)

```
1. /signup 또는 /login 제출
2. POST /api/v1/auth/signup | /login → { access_token, user }
3. auth-store.setAuth({ accessToken, user })  ← localStorage 저장
4. router.push('/dashboard')
5. 이후 모든 API 요청은 Axios interceptor 가 헤더 자동 주입
6. 401 응답 → auth-store.clear() + /login 리다이렉트
7. 로그아웃: Settings 페이지 버튼 → clear() + /login
```

---

## 8. 대시보드 위젯 (필드 매핑)

| UI 요소 | 데이터 소스 | 경로 |
|---------|-------------|------|
| 총 평가액 (KRW) | `summary.total_value_by_currency.KRW` | `/portfolio/summary` |
| 총 평가액 (USD) | `summary.total_value_by_currency.USD` | 동일 |
| 총 손익 절대 | `summary.pnl_by_currency.{ccy}.abs` | 동일 |
| 총 손익 % | `summary.pnl_by_currency.{ccy}.pct` | 동일 |
| 클래스별 비중 | `summary.allocation[].{asset_type, pct}` | 동일 |
| 마지막 갱신 시각 | `summary.last_price_refreshed_at` | 동일, `date-fns` 로 상대 표시 |
| 보유 종목 행 | `holdings[].{ symbol, name, quantity, avg_cost, latest_price, latest_value, pnl_abs, pnl_pct }` | `/portfolio/holdings` |

포맷터 (`lib/format.ts`):
- `formatCurrency(n, ccy)` — `new Intl.NumberFormat('ko-KR', { style:'currency', currency: ccy })`
- `formatPct(n)` — 소수 2자리
- `formatRelative(iso)` — Asia/Seoul 변환 후 "N분 전"

---

## 9. 테스트 요구

### 9.1 커버리지
- 라인 커버리지 **≥ 90%** (pre-push gate)
- `test` 대상: 모든 `hooks/`, `components/features/**`, `lib/api-client.ts`, `lib/format.ts`, `stores/auth-store.ts`

### 9.2 테스트 전략
- 훅 테스트는 **MSW** 로 백엔드 API mock (실제 네트워크 금지)
- `QueryClient` 는 테스트마다 새 인스턴스 (캐시 오염 방지)
- RHF+Zod 폼은 `@testing-library/user-event` 로 사용자 입력 시뮬레이션
- AuthGuard 는 Zustand store 직접 조작해 redirect 여부 검증

### 9.3 핵심 테스트 케이스
- [ ] signup 실패 (409 이메일 중복) → 인라인 에러
- [ ] login 성공 → `/dashboard` push 호출
- [ ] 토큰 없이 `/dashboard` 접근 → `/login` redirect
- [ ] Axios 401 응답 → store clear + redirect
- [ ] SymbolSearch debounce — 빠른 타이핑 시 마지막 쿼리만 호출
- [ ] Holdings 행 `stale` 배지 — `last_price_refreshed_at` 3시간 초과 mock 시 표시
- [ ] PortfolioSummary — 다중 통화(KRW+USD) 모두 렌더

---

## 10. 작업 순서 (Step 1 → N)

> `nvm use` 로 Node 20.11+ 활성화 후 시작. 각 스텝 끝에 `npm run lint && npx tsc --noEmit && npx jest` 통과 확인.

1. **[환경]** `.nvmrc` 생성 (`20.11.0`), `package.json` 에 필수 deps 추가, shadcn 초기화, jest 설정(coverageThreshold 90)
2. **[기초]** `lib/env.ts`, `lib/api-client.ts`, `lib/query-client.ts`, `providers/query-provider.tsx` + `app/layout.tsx` 래핑
3. **[Auth]** Zod 스키마 → Zustand auth-store → signup/login 페이지 + 폼 + 훅 + AuthGuard → 테스트
4. **[App shell]** `(app)/layout.tsx` 헤더/네비 + 로그아웃 + 라우팅 가드
5. **[Symbol 검색]** Zod schema + `useSymbolsSearch` + `SymbolSearch` 컴포넌트 + 테스트
6. **[자산 추가]** `asset-add-form` 폼 (3 스텝) + `useCreateUserAsset` + `/assets/new` 페이지 + 테스트
7. **[자산 목록 & 삭제]** `AssetList` + 삭제 다이얼로그 + `/assets` 페이지 + 테스트
8. **[거래 기록 추가]** `TransactionForm` (기보유 자산에 BUY 매수 추가) + 테스트
9. **[대시보드]** `PortfolioSummary` + `AllocationChart` + `HoldingsTable` + `/dashboard` 페이지 + loading/error.tsx + 테스트
10. **[설정]** `/settings` 최소 구현 (로그아웃)
11. **[통합]** E2E 흐름 수동 확인 (signup → 자산추가 → 대시보드), 커버리지 최종 확인

---

## 11. 다른 역할과의 계약 (← backend)

frontend 가 **호출하는 요청 스키마** 와 **수신하는 응답 스키마**. backend.md §11 과 **완전 일치해야 함**.

| 호출 | 요청 바디 (Zod) | 응답 스키마 (Zod) |
|------|-----------------|-------------------|
| `POST /api/v1/auth/signup` | `{ email: string, password: string(min 8) }` | `{ access_token, token_type, user: UserResponse }` |
| `POST /api/v1/auth/login` | `{ email, password }` | 동일 |
| `GET /api/v1/auth/me` | - | `UserResponse = { id, email, created_at }` |
| `GET /api/v1/symbols?q=&type=` | query | `SymbolResponse[]` |
| `POST /api/v1/user-assets` | `{ asset_symbol_id, quantity, unit_price, purchased_at }` | `UserAssetResponse` |
| `DELETE /api/v1/user-assets/{id}` | - | `204` |
| `POST /api/v1/user-assets/{id}/transactions` | `{ type: "BUY", quantity, unit_price, executed_at, memo? }` | `TransactionResponse` |
| `GET /api/v1/portfolio/summary` | - | `PortfolioSummaryResponse` (PRD §8 참고) |
| `GET /api/v1/portfolio/holdings` | - | `UserAssetResponse[]` |

### 계약 변경 규칙
1. PRD `../asset-tracking.md` §8 **먼저 수정**
2. `docs/api/asset-tracking.yaml` 업데이트
3. `lib/schemas/*.ts` Zod 스키마 동기화
4. 구현

---

## 12. 구현 제약 (frontend/CLAUDE.md 재강조)

### MUST
- **Named export 만** — `default` 는 App Router 라우팅 파일에만
- **TypeScript**: 명시적 타입, `any` 금지 (`unknown` + narrowing 으로)
- **데이터 페칭**: TanStack Query — `useEffect + fetch` 금지
- **폼**: React Hook Form + Zod — 수동 `useState` + validation 금지
- **스타일**: Tailwind 유틸리티 — 인라인 `style={...}` 금지
- **이미지**: `next/image` — `<img>` 금지
- **라우트**: `loading.tsx`, `error.tsx` (특히 `/assets`, `/dashboard`)
- **목록 key**: 고유 id — `index` 금지
- **접근성**: 인터랙티브 요소에 `aria-label` 또는 visible text, 폼 라벨, 키보드 네비

### NEVER
- `any` 타입
- Server Component 에서 `useState` / `useEffect`
- `useEffect` 안에서 직접 fetching
- `NEXT_PUBLIC_` 아닌 env 를 클라이언트 참조
- API Route 없이 클라이언트에서 DB 직접 접근 (해당 프로젝트는 외부 FastAPI 호출만 — 이 규칙은 자연 충족)
- 프로덕션에 `console.log`
- 컴포넌트 파일 안에 비즈니스 로직 (hooks 로 분리)
- 테스트 없이 컴포넌트/훅 추가

---

## 13. 성공 기준

- [ ] PRD US-1 ~ US-10 수락 기준을 UI 관점에서 모두 충족
- [ ] `npm run lint`, `npx tsc --noEmit` 무결점
- [ ] `npx jest --coverage` 라인 커버리지 ≥ 90%
- [ ] `npm run build` 성공 (Node 20.11+)
- [ ] WCAG 2.1 AA: 키보드 네비·폼 라벨·색 대비 (shadcn 기본값 + 추가 검증)
- [ ] 모든 페이지 로딩/에러 상태 구현 (`loading.tsx`, `error.tsx`)

---

## 14. 실행 지시 (agent 가 받으면)

1. `frontend/CLAUDE.md` 먼저 정독
2. `../asset-tracking.md` PRD 정독 (특히 §3 유저 스토리 · §8 API 계약)
3. `memory/MEMORY.md` 확인 — **Node 버전 제약 즉시 해결** (`.nvmrc` + README 안내)
4. §10 작업 순서 1 번부터 진행. 스텝마다 린트·타입·테스트 통과 확인
5. 완료 시 리포트: 생성·변경 파일 / 추가한 npm 패키지 / backend 에 요청할 스키마 이슈 / 후속 수동 작업 (`npm install`, shadcn init 등)

---

> 이 프롬프트는 `/planner` 가 자동 생성했습니다. 계약 변경은 반드시 PRD → YAML → 이 문서(+backend.md) 순서로 업데이트하세요.
