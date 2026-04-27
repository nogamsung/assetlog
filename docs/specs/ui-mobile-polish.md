# PRD — UI / Mobile Polish & 숫자 포맷 정리 (토스 스타일)

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-27 (rev 2026-04-28: 토스 디자인 언어 적용) |
| 상태 | draft |
| 스택 범위 | frontend (단독) — backend 변경 없음 |
| 우선순위 | P1 |
| 브랜치 | `feature/ui-mobile-polish` |
| 디자인 레퍼런스 | **토스(Toss) 앱 / 토스증권 / 토스뱅크** |

---

## 1. 배경

현재 AssetLog 의 UI 는 데스크톱 기준으로 자라났다. 헤더(`(app)/layout.tsx`)는 항상 가로 정렬, 대시보드와 자산 목록은 wide table 위주이며, 모바일(≤640px) 에서는 가로 스크롤·작은 탭 영역·짧은 정보 잘림이 두드러진다. 또한 통화·수량·손익률 표시가 컴포넌트마다 제각각이라 KRW 에 `.00` 이 붙거나 `pnlPct` 가 `13.6400%` 처럼 불필요한 정밀도로 노출되는 케이스가 있다.

이번 작업은 **재설계가 아닌 polish 패스**다. 정보 밀도(데스크톱)는 보존하고, 모바일 가독성과 숫자 표시 일관성을 끌어올린다.

## 2. 목표 (Goals)

- **모바일 가독성**: 핵심 페이지(대시보드, 자산 목록, 자산 상세, 설정, 로그인)가 375px 폭에서 가로 스크롤 없이 사용 가능. 모든 인터랙티브 요소의 최소 탭 영역 **44×44px**.
- **시각적 일관성**: 카드 spacing, 헤더 hierarchy, badge / pill 사용처를 토큰화. 다크/라이트 양 테마에서 동일 외관 보장.
- **숫자 포맷 표준화**: 단일 포매터(`lib/format.ts`)에서 모든 통화·수량·퍼센트·환율을 일관된 규칙으로 출력. KRW 기본 정수, USD 기본 2자리, 트레일링 zero 제거. 큰 금액은 모바일 카드에서 컴팩트(`1.2M`) 표기를 옵션으로 제공.
- **회귀 없음**: LCP, CLS 지표가 현재 대비 악화 ≤5%. 기존 hooks·API 계약 변경 없음.

측정 가능한 수락 기준:
- Chrome DevTools Mobile 375px 프리셋에서 가로 스크롤 발생 페이지 0개.
- `formatCurrency("1500000.00", "KRW")` 결과가 `₩1,500,000` 이고 소수점 없음.
- `formatPercent(13.64)` 결과가 `13.64%`, `formatPercent(13)` 결과가 `13%` (트레일링 zero 제거).
- Jest 라인 커버리지 90% 이상 유지 (pre-push 게이트 통과).

## 3. 비목표 (Non-goals)

- 새 페이지·새 라우트 추가 없음
- 새 백엔드 엔드포인트·DB 스키마·OpenAPI 변경 없음
- 디자인 시스템 토큰 재정의 (HSL 변수) — 기존 토큰 재활용
- PWA / 오프라인 / 푸시 — 후속 PRD
- i18n (영어 전환) — 후속 PRD
- 차트(`recharts`) 내부 폰트·레이아웃 재작업 — 모바일에서 컨테이너 높이만 조정하는 수준까지

## 4. 대상 사용자

- 단일 계정 자가 사용자 (single-user 모드)
- 1차 디바이스: iOS Safari, Android Chrome (모바일 웹). 2차: 데스크톱 Chrome/Safari.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-1 | 사용자로서 모바일에서 대시보드 요약 카드를 한눈에 볼 수 있어야 한다 | 1) 375px 폭에서 카드 1열, 768px 이상에서 2~4열 / 2) 카드 내부 텍스트 잘림(`overflow`) 없음 / 3) 큰 금액은 모바일에서만 컴팩트 표기(`₩1.2억` 또는 `₩1.2M`) 옵션 적용 |
| US-2 | 사용자로서 모바일에서 보유 자산 표를 가로 스크롤 없이 볼 수 있어야 한다 | 1) 데스크톱은 기존 8열 테이블 유지 / 2) `sm` 미만에서는 카드형 리스트로 자동 전환 / 3) 카드에 심볼·평가액·손익(±%) 우선 노출, 평단·현재가·비중은 보조 표시 |
| US-3 | 사용자로서 통화 표시에서 불필요한 소수점이 보이지 않아야 한다 | 1) KRW 정수 표시 / 2) USD/EUR 등은 2자리, 단 `.00` 처럼 의미 없는 0 은 생략 가능 옵션 / 3) USDT/USDC 등 Intl 미지원 통화도 4자리 한도에서 트레일링 zero 제거 |
| US-4 | 사용자로서 손익률(%)이 적절한 자리수로 표시되어야 한다 | 1) `formatPercent` 기본 2자리 유지하되 트레일링 zero 제거 / 2) `+` 부호는 양수만, 0 은 부호 없이 / 3) 색상은 **토스 컬러** — `text-toss-up`(+, 빨강 #F04452) / `text-toss-down`(−, 파랑 #1B64DA) / `text-toss-text-weak`(0) 통일 |
| US-5 | 사용자로서 거래 추가/CSV 가져오기 다이얼로그를 모바일에서 편하게 쓸 수 있어야 한다 | 1) 다이얼로그 폭 `mx-4` 보장 / 2) 입력 필드 폰트 ≥ 16px (iOS auto-zoom 방지) / 3) sticky header/footer 가 safe-area inset 을 고려 |
| US-6 | 사용자로서 모바일 헤더에서 주요 페이지를 빠르게 이동할 수 있어야 한다 | 1) 모바일에서 햄버거 또는 하단 탭바 중 하나 채택 / 2) 현재 경로 active 상태 시각화 / 3) 키보드 / 스크린리더 접근 가능 |
| US-7 | 사용자로서 다크/라이트 테마 어느 쪽이든 동일한 정보 hierarchy 를 본다 | 1) 모든 변경 컴포넌트가 두 테마에서 시각 회귀 없음 / 2) 손익 색상은 `dark:text-emerald-400` / `dark:text-rose-400` 등 다크 변형 명시 |

## 6. 핵심 플로우

### 6.1 모바일 대시보드 진입
```
1. 모바일 사용자가 "/" → "/dashboard" 진입
2. 헤더가 단일 행(로고 + 메뉴 트리거 + 설정/로그아웃)으로 축약 렌더
3. SummaryCards 가 1열 그리드로 표시. 큰 금액 컴팩트 토글 ON 시 1.2M / 1.2억 표기
4. AllocationDonut 와 PortfolioHistoryChart 는 컨테이너 width 100%, height 적응
5. HoldingsTable 은 sm 미만에서 카드 리스트로 fallback (HoldingsList)
```

### 6.2 자산 목록 모바일 사용
```
1. /assets 진입 → CashAccountList + AssetList
2. AssetList 카드는 모바일에서 심볼 / 자산명 / 평가액 / 손익(±%) 만 한 줄에 표시
3. 우상단 액션(삭제)은 44×44 탭 영역 보장. swipe-to-delete 는 미도입
4. 카드 탭 → 자산 상세로 이동
```

### 6.3 숫자 포맷 적용 흐름
```
1. 컴포넌트는 backend 의 Decimal-string 값을 그대로 받음 (계약 동일)
2. 표시 직전 lib/format.ts 의 단일 함수로 변환
3. 통화 카테고리(KRW vs USD vs CRYPTO_STABLE) 별 자릿수 룰 적용
4. trim trailing zeros — `useGrouping` 유지, `minimumFractionDigits: 0`, `maximumFractionDigits` 만 카테고리별 차등
```

### 예외 경로
- 컴팩트 표기 시 정밀도 손실 가능 — 카드 hover/long-press 시 full value tooltip
- Intl 미지원 통화(USDT/USDC) — 기존 fallback `${number} ${code}` 형식 유지하되 trailing zero 제거 적용
- 모바일에서 dialog 열렸을 때 background scroll lock 유지

## 7. 데이터 모델

변경 없음. 기존 타입(`HoldingResponse`, `PortfolioSummary`, `CashAccount`, `TransactionResponse`) 그대로 사용. Decimal 은 string 으로 도착, 표시 직전 Number 변환 후 포매터에 위임.

## 8. API 계약

변경 없음. 모든 엔드포인트의 응답 스키마·필드명·정밀도(string 직렬화) 그대로 유지. 만약 표시 단계에서 round-half-even 등 추가 보정이 필요하면 frontend 의 `lib/format.ts` 안에서만 처리.

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 | 대시보드 LCP/ CLS 회귀 ≤5% (Lighthouse Mobile 기준) |
| 접근성 | WCAG 2.1 AA — 색상 대비 4.5:1, 인터랙티브 44×44, `aria-label`/`aria-pressed` 명시, 키보드 포커스 가시 |
| 반응형 breakpoint | Tailwind 기본: `sm:640` `md:768` `lg:1024` `xl:1280`. 모바일-퍼스트 표기 — base 가 모바일 |
| 다크 모드 | 모든 손익 색·badge·pill 에 `dark:` 변형 검증 |
| safe-area | `env(safe-area-inset-bottom)` 고려한 sticky footer / dialog footer |
| 폰트 | iOS 자동 줌 방지 — 모든 `<input>`, `<select>`, `<textarea>` 최소 `text-base` (16px) |
| 테스트 | `lib/format.ts` unit test 100% 분기 커버. 1~2개 컴포넌트 viewport smoke (jsdom 한계 인정 — 시각 회귀는 수동) |
| 라인 커버리지 | 전체 ≥ 90% (pre-push 게이트) |

### 모바일 최적화 가이드라인 (요약)

- **breakpoint**: 모바일 base, `sm:` 부터 desktop 표시. 기존 코드의 `hidden sm:flex` / `sm:grid-cols-2` 패턴 유지·확장.
- **탭 영역**: 아이콘 버튼은 `size="icon"` 의 9×9 (36px) 대신 모바일에서 `h-11 w-11` (44px) 적용 — Button variants 에 `icon-touch` 사이즈 추가 검토.
- **테이블 → 카드 전환**: `HoldingsTable` 옆에 `HoldingsList` 신설 — `sm:hidden` 에서 노출, `hidden sm:block` 으로 기존 테이블 노출.
- **sticky header**: `(app)/layout.tsx` 헤더에 `sticky top-0 z-40 bg-background/80 backdrop-blur` 추가, safe-area 미고려 (top inset 은 OS 가 처리).
- **dialog**: `BulkImportDialog`, cash add/edit/delete 다이얼로그는 모바일에서 `max-h-[90vh]` + `overflow-y-auto` + sticky footer 유지. 입력 폰트 16px.
- **하단 네비**: 1차 결정 — **추가하지 않음**. 헤더 sticky 로 충분. 하단 네비는 후속(Open Issue 1).

### 숫자 포맷 표준 (frontend-only)

| 카테고리 | 자릿수 (max) | 트레일링 0 | 그룹화 | 비고 |
|----------|-------------|-----------|--------|------|
| 통화 — KRW, JPY (정수 통화) | 0 | n/a | ✓ | `₩1,500,000` |
| 통화 — USD, EUR, GBP (소수 통화) | 2 | 제거 | ✓ | `$1,234.5` (not `1,234.50`), `$1,234` (not `1,234.00`) |
| 통화 — Intl 미지원 (USDT, USDC) | 4 | 제거 | ✓ | `1,234.5 USDT` |
| 수량 — 주식 | 4 | 제거 | ✓ | `10` (not `10.0000`) |
| 수량 — crypto | 8 | 제거 | ✓ | `0.12345678` |
| 퍼센트 (수익률) | 2 | 제거 | n/a | `13.64%`, `13%` |
| FX 환율 | 4 | 제거 | n/a | `1,355.4` |
| 컴팩트 (모바일 카드) | 1 | 제거 | ko-KR notation:"compact" | `1.2억`, `12.3M` (locale 기반) |

부호 규칙: 양수는 `+` 명시, 0 은 부호 없음, 음수는 `-`. 색상은 emerald(+) / rose(−) / muted(0).

통화 기호 위치: 한국 사용자 기준 — `Intl.NumberFormat("ko-KR", {style:"currency"})` 결과 그대로 (`₩` 좌측, `$` 좌측, `EUR` 좌측, USDT/USDC 는 우측 코드).

## 9.5 토스(Toss) 디자인 언어 (이번 작업의 시각 기조)

**전체 UI 의 룩앤필을 토스 앱 스타일로 통일한다.** 기존 shadcn 토큰 위에 *토스 레이어*를 덧씌우는 방식 — 토큰 추가는 허용, 색상 변수만 일부 신설(파괴 없음).

### 9.5.1 핵심 원칙
1. **숫자 우선 (Numbers-first)**: 화면마다 "가장 중요한 한 개의 숫자"를 압도적으로 크게(`text-3xl`~`text-4xl` + `font-bold` + `tracking-tight` + `tabular-nums`). 보조 정보는 한 단계 작게 + 회색.
2. **여백 (Generous whitespace)**: 카드 내부 패딩 ↑(`p-5 sm:p-6`), 섹션 사이 간격 ↑(`space-y-6 sm:space-y-8`). 정보 압축이 아니라 호흡으로.
3. **부드러움 (Soft & rounded)**: 모든 카드/버튼/입력 필드를 큰 라운드(`rounded-2xl`)로. 그림자는 거의 쓰지 않고 *배경 톤 차이*로 카드 구분.
4. **단색 강조 (Single accent)**: 주요 액션은 토스 블루 단색. 그라디언트·다중 색상 강조 금지.
5. **즉각 반응 (Tactile feedback)**: 모든 탭 가능 요소에 `active:scale-[0.98] transition` — 누르는 순간 살짝 줄어듦.
6. **수직 흐름 (Vertical-first)**: 모바일은 항상 한 열, 좌측 라벨 + 우측 값. 가로 정렬은 데스크톱(`sm:`)부터.

### 9.5.2 컬러 토큰 (신규 — `globals.css` 에 CSS 변수로 추가)

| 토큰 | Light | Dark | 용도 |
|------|-------|------|------|
| `--toss-blue` | `#3182F6` | `#4593FC` | primary 액션, 링크, 활성 상태 |
| `--toss-blue-bg` | `#EAF2FE` | `#1E2A3D` | primary 액션의 보조 배경 (pill, 선택된 항목) |
| `--toss-text-strong` | `#191F28` | `#F1F3F5` | 큰 숫자, 핵심 텍스트 |
| `--toss-text` | `#333D4B` | `#D1D6DB` | 본문 |
| `--toss-text-weak` | `#8B95A1` | `#8B95A1` | 라벨, 보조 |
| `--toss-text-disabled` | `#B0B8C1` | `#4E5968` | placeholder, 비활성 |
| `--toss-up` | `#F04452` | `#F76A77` | 손익 + (한국 관습: 빨강) |
| `--toss-down` | `#1B64DA` | `#5187E5` | 손익 − (한국 관습: 파랑) |
| `--toss-bg` | `#FFFFFF` | `#17171C` | 페이지 배경 |
| `--toss-card` | `#F9FAFB` | `#1E1F24` | 카드 배경 (페이지보다 살짝) |
| `--toss-border` | `#F2F4F6` | `#2A2D32` | 미세 구분선 |

> **손익 색상 규칙 갱신**: 기존 PRD §5 의 `emerald(+) / rose(−)` 는 **삭제**. 한국 금융 관습(상승=빨강, 하락=파랑)을 따라 `--toss-up` / `--toss-down` 사용. Tailwind 클래스는 `text-[var(--toss-up)] dark:text-[var(--toss-up)]` 형태로 직접 변수 참조 또는 `tailwind.config.ts` 의 `theme.extend.colors.toss` 로 등록.

### 9.5.3 타이포그래피

- **폰트**: 한글 우선 — `Pretendard` (CDN: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css`) 를 `next/font` 또는 globals.css 에 추가. fallback `-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", system-ui, sans-serif`.
- **숫자**: 모든 금액·% 에 `font-variant-numeric: tabular-nums;` (Tailwind `tabular-nums`).
- **위계 5단계**:
  | 용도 | 모바일 | 데스크톱 | weight |
  |------|--------|---------|--------|
  | Hero 숫자 (대시보드 총자산) | `text-4xl` | `text-5xl` | `font-bold` (700) |
  | 카드 메인 숫자 | `text-2xl` | `text-3xl` | `font-bold` |
  | 섹션 제목 | `text-lg` | `text-xl` | `font-bold` |
  | 본문 | `text-base` | `text-base` | `font-medium` (500) |
  | 라벨 / 캡션 | `text-sm` | `text-sm` | `font-medium`, `text-[var(--toss-text-weak)]` |

### 9.5.4 레이아웃 / 간격 / 라운드

| 항목 | 값 |
|------|-----|
| 페이지 좌우 패딩 | `px-4 sm:px-6 lg:px-8` |
| 카드 패딩 | `p-5 sm:p-6` |
| 카드 라운드 | `rounded-2xl` (16px) — 일관 적용 |
| 버튼 라운드 | `rounded-xl` (12px) |
| 입력 라운드 | `rounded-xl` |
| 작은 pill / badge | `rounded-full` |
| 카드-카드 간격 | `space-y-3 sm:space-y-4` (밀집) / `space-y-6 sm:space-y-8` (섹션) |
| 보더 두께 | `border` 1px, 색은 `--toss-border` (다크/라이트 모두 매우 옅음) |
| 그림자 | **거의 사용 안 함**. 떠야 할 다이얼로그/시트만 `shadow-2xl`. 카드는 그림자 0. |

### 9.5.5 컴포넌트별 토스 스타일 패턴

#### 9.5.5.1 버튼
- Primary: `bg-[var(--toss-blue)] text-white font-bold rounded-xl h-12 sm:h-11 active:scale-[0.98] hover:brightness-95`
- Secondary: `bg-[var(--toss-card)] text-[var(--toss-text)] font-medium rounded-xl h-12 sm:h-11`
- Destructive: `bg-[var(--toss-up)]/10 text-[var(--toss-up)] font-bold rounded-xl`
- 모바일 주요 액션은 **항상 full-width** (`w-full`).
- 데스크톱은 `sm:w-auto` 로 자연 폭.

#### 9.5.5.2 카드
- 기본: `bg-[var(--toss-card)] rounded-2xl p-5 sm:p-6 border border-[var(--toss-border)]`
- 카드 내부 hierarchy: `라벨(text-sm, weak)` → `숫자(text-2xl/3xl, bold, strong)` → `보조(text-sm, weak, with up/down color)`
- 카드 자체가 탭 가능하면 `active:scale-[0.99] transition-transform`.

#### 9.5.5.3 리스트 아이템 (HoldingsList, CashAccountList 등)
- 좌: 아이콘(원형 배경 `rounded-full bg-[var(--toss-blue-bg)]` 또는 심볼) + 메인 텍스트 + 보조 텍스트(작게)
- 우: 큰 숫자(평가액, `font-bold tabular-nums`) + 보조(±%, `text-sm` toss-up/down 색)
- 행 간 구분선 사용 안 함, 패딩으로만 분리 (`py-4` + 미세 hover bg).

#### 9.5.5.4 다이얼로그 → **모바일은 Bottom Sheet 로 변환**
- `sm` 미만: `bottom-0 left-0 right-0 rounded-t-3xl translate-y-0` (위로 슬라이드 인). 백드롭 `bg-black/40`.
- `sm` 이상: 기존 중앙 다이얼로그 유지(`rounded-2xl`).
- 시트 상단에 작은 핸들 바(`w-12 h-1.5 bg-[var(--toss-border)] rounded-full mx-auto mt-2`).
- 시트 내부: 큰 제목(`text-2xl font-bold`) → 본문 → 하단 sticky `w-full` Primary 버튼.
- 구현: `dialog` element 또는 Radix Dialog 의 `DialogContent` 에 모바일 variant 클래스 추가. (별도 라이브러리 도입 X — 1차는 Tailwind 만으로.)

#### 9.5.5.5 입력 필드
- `rounded-xl border border-[var(--toss-border)] bg-[var(--toss-card)] h-12 px-4 text-base focus:border-[var(--toss-blue)] focus:ring-2 focus:ring-[var(--toss-blue)]/20`
- 라벨은 입력 위 `text-sm font-medium text-[var(--toss-text-weak)] mb-2`
- 에러는 `text-sm text-[var(--toss-up)] mt-1.5`

#### 9.5.5.6 헤더 / 네비
- 모바일 sticky: `h-14 px-4 flex items-center justify-between bg-[var(--toss-bg)]/90 backdrop-blur border-b border-[var(--toss-border)]`
- 좌: 로고/뒤로가기, 중앙 빈공간 또는 페이지명, 우: 액션 아이콘(2개 이내)
- 데스크톱: 가로 nav 유지, 활성 링크는 `text-[var(--toss-blue)] font-bold` + 하단 2px 라인 또는 단순 색상.
- 모바일 네비 1차 결정: **inline 메뉴 유지 + sticky** (Open Issue 1 그대로).

#### 9.5.5.7 손익 표시 (특별 강조)
- 색상: `text-[var(--toss-up)]` (양수, 상승) / `text-[var(--toss-down)]` (음수, 하락) / `text-[var(--toss-text-weak)]` (0)
- 부호: 양수 `+`, 음수 `−` (en-dash, U+2212), 0 부호 없음
- 형식: `+12,345 (+3.45%)` 한 줄. 수치는 `tabular-nums font-bold`.
- 작은 화살표 아이콘 동반(`▲` 상승 / `▼` 하락) — 색은 동일.

### 9.5.6 마이크로 인터랙션

| 동작 | 효과 |
|------|------|
| 모든 탭 가능 카드/버튼 | `active:scale-[0.98] transition-transform duration-100` |
| 다이얼로그 / 바텀시트 진입 | `data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-full` |
| 페이지 진입 큰 숫자 | (옵션) 0 → 실제값 카운트업 — 1차 미도입(후속) |
| 토스트 / 알림 | 모바일은 화면 하단 띠, 데스크톱은 우상단. 1차는 기존 유지 |

### 9.5.7 globals.css 에 추가될 토큰 (요약)

```css
@layer base {
  :root {
    --toss-blue: #3182F6;
    --toss-blue-bg: #EAF2FE;
    --toss-text-strong: #191F28;
    --toss-text: #333D4B;
    --toss-text-weak: #8B95A1;
    --toss-text-disabled: #B0B8C1;
    --toss-up: #F04452;
    --toss-down: #1B64DA;
    --toss-bg: #FFFFFF;
    --toss-card: #F9FAFB;
    --toss-border: #F2F4F6;
  }
  .dark {
    --toss-blue: #4593FC;
    --toss-blue-bg: #1E2A3D;
    --toss-text-strong: #F1F3F5;
    --toss-text: #D1D6DB;
    --toss-text-weak: #8B95A1;
    --toss-text-disabled: #4E5968;
    --toss-up: #F76A77;
    --toss-down: #5187E5;
    --toss-bg: #17171C;
    --toss-card: #1E1F24;
    --toss-border: #2A2D32;
  }
  body {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont,
                 'Apple SD Gothic Neo', system-ui, sans-serif;
    background: var(--toss-bg);
    color: var(--toss-text);
    font-feature-settings: 'tnum' 1; /* tabular nums 기본 */
  }
}
```

`tailwind.config.ts` 의 `theme.extend.colors` 에 `toss: { blue, up, down, ... }` 매핑 추가 → `text-toss-blue`, `bg-toss-card` 형태로도 호출 가능.

### 9.5.8 마이그레이션 영향

- 기존 `text-emerald-600 / text-rose-600` 손익 색상은 **모두** `text-[var(--toss-up)] / text-[var(--toss-down)]` 로 교체. (수익률·손익액 표시 일괄.)
- `Card` 의 기본 그림자(`shadow`) 사용처는 카드 변형 시 **제거**.
- `Button` variant 에 `toss-primary`, `toss-secondary`, `toss-destructive` 추가. 기존 `default`, `secondary`, `destructive` 도 토스 스타일 토큰을 참조하도록 매핑(파괴적 변경 아님 — 색만 토스 토큰).

## 10. 컴포넌트별 변경 항목 (changeset)

### 10.0 디자인 토큰 (선행 작업, 0단계)
- `frontend/src/app/globals.css` — §9.5.7 의 CSS 변수 블록(라이트/다크) 추가, Pretendard 폰트 import (또는 `next/font/google` 의 `Inter` + `next/font/local` 로 Pretendard 자체 호스팅 — Pretendard 는 Google Fonts 미제공이므로 CDN 또는 self-host).
- `frontend/tailwind.config.ts` — `theme.extend.colors.toss` 추가 (`blue`, `blueBg`, `up`, `down`, `card`, `border`, `textStrong`, `textWeak`).
- `frontend/src/lib/cn.ts` 또는 신규 `frontend/src/lib/toss-tokens.ts` — class 상수 export (`tossCard`, `tossButtonPrimary`, `tossInput` 등) 으로 재사용성 확보. 컴포넌트는 이 상수를 주로 import.

### 10.1 포매터 (1단계)
- `frontend/src/lib/format.ts` — 트레일링 zero 제거 옵션, 통화 카테고리 분기, USDT/USDC 통합. 함수 시그니처 호환 유지(기본 동작 유지, 옵션으로 신규 동작 enable).
- `frontend/src/lib/format.ts` 신규 export: `formatCompactCurrency(value, currency)` — 모바일 카드 전용.
- `frontend/src/__tests__/lib/format.test.ts` — 케이스 추가: trailing zero, KRW 정수, USDT, 큰 음수.

### 10.2 글로벌 / 레이아웃
- `frontend/src/app/(app)/layout.tsx` — 헤더 sticky, 모바일 메뉴 토글(또는 축약), 좌측 nav 를 `hidden sm:flex` 처리, 모바일 햄버거 또는 단순 아이콘 메뉴 도입. `aria-current="page"` 추가.
- `frontend/src/app/globals.css` — `body` 의 `font-family` 를 `var(--font-sans)` 로 정정 (현재 Arial fallback 만 적용됨), iOS auto-zoom 방지를 위한 input min font-size CSS rule.

### 10.3 대시보드
- `frontend/src/components/features/portfolio/dashboard-view.tsx` — 모바일에서 spacing `space-y-6 sm:space-y-8` 차등.
- `frontend/src/components/features/portfolio/summary-cards.tsx` — 그리드 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` 유지하되 카드 내부 `text-2xl` 을 모바일에서 `text-xl sm:text-2xl` 로 축소. 컴팩트 표기 도입(`formatCompactCurrency`).
- `frontend/src/components/features/portfolio/holdings-table.tsx` — `hidden sm:block` 처리.
- 신규: `frontend/src/components/features/portfolio/holdings-list.tsx` — 모바일 카드형. `block sm:hidden`. 정렬 메뉴는 dropdown 으로 압축.
- `frontend/src/components/features/portfolio/portfolio-history-chart.tsx` — 컨테이너 height 모바일 240px / sm 320px.
- `frontend/src/components/features/portfolio/tag-breakdown-table.tsx` — 모바일 카드/리스트 fallback (간단 버전: 가로 스크롤 허용 + sticky 첫 컬럼).

### 10.4 자산
- `frontend/src/components/features/assets/asset-list.tsx` — 카드 내부의 `hidden md:flex` 데스크톱 메트릭 4열을 유지. 모바일 카드는 평가액/손익(±%) pill 노출 추가.
- `frontend/src/components/features/assets/asset-detail.tsx` — `dl grid-cols-2 sm:grid-cols-4` 유지, 카드 padding 모바일 축소 (`p-4 sm:p-6`).
- `frontend/src/components/features/assets/transaction-list.tsx` — 인라인 SVG 삭제 버튼을 `Trash2` 아이콘으로 교체, tap 영역 44×44, 모바일에서 메모/태그 우선순위 정리(`hidden xs:` → `hidden sm:` 통일).
- `frontend/src/components/features/assets/transaction-form.tsx` — 입력 폰트 16px, 라벨 `text-sm`, 모바일 가로 grid → 세로 stack.

### 10.5 현금
- `frontend/src/components/features/cash/cash-account-list.tsx` — 모바일에서 row 내부 `min-w-0` 보강, 잔액 / 라벨 줄바꿈 정책 명확화.
- `frontend/src/components/features/cash/cash-account-add-dialog.tsx`, `*-edit-dialog.tsx`, `*-delete-dialog.tsx` — dialog 폭 `mx-4 max-w-md`, 입력 16px, sticky footer.
- `frontend/src/components/features/cash/cash-account-list.tsx` 의 `formatCurrencySafe` → `lib/format.ts` 의 통합 포매터로 이관 후 import 단순화.

### 10.6 거래 일괄
- `frontend/src/components/features/transactions/bulk-import-dialog.tsx` — 모바일 sticky header/footer safe-area, 탭 버튼 `min-h-11`, scroll body `overscroll-contain`.
- `frontend/src/components/features/transactions/bulk-grid-tab.tsx` — 그리드의 셀 폰트 16px (input zoom 방지), 가로 스크롤 컨테이너에 그림자 hint.
- `frontend/src/components/features/transactions/bulk-csv-tab.tsx` — drop zone 모바일에서 height 축소(`h-32 sm:h-40`).

### 10.7 설정 / 인증
- `frontend/src/app/(app)/settings/page.tsx` — `max-w-2xl` 유지, 카드 spacing 축소, 다운로드 버튼 모바일 `w-full sm:w-auto`.
- `frontend/src/app/(auth)/login/page.tsx` & `frontend/src/components/features/auth/login-form.tsx` — 입력 16px, 폼 카드 모바일 `mx-4 max-w-sm`.

### 10.8 UI primitives
- `frontend/src/components/ui/button.tsx` — `size` 에 `icon-touch` (`h-11 w-11`) 추가. 기존 `icon` 은 데스크톱 행에서 유지.
- `frontend/src/components/ui/input.tsx` — 기본 폰트 `text-base` (16px) 유지 / 추가 검증.
- `frontend/src/components/ui/card.tsx` — padding 토큰 `p-4 sm:p-6` 적용 검토.

### 10.9 차트 / 기타
- `frontend/src/lib/chart-format.ts` — `formatCurrencyValue` 의 `maximumFractionDigits: 0` 을 카테고리 룰로 위임(통화별 분기), 컴팩트 케이스 통합.

## 11. 의존성 / 리스크

- **의존성**: `lib/format.ts` 는 거의 모든 표시 컴포넌트의 입구 — 시그니처 변경 시 회귀 큼. **기본 시그니처는 호환 유지**, 신규 옵션을 추가하는 방식으로 진행.
- **리스크 1 — 손익 색상 mis-zero**: 기존 코드 일부가 `Number(val) > 0` 와 `> 0` `< 0` 만 비교 → 0 이 muted 로 빠짐. 표준 헬퍼(`pnlColor(val)`)로 통일.
- **리스크 2 — 컴팩트 표기 오해**: 사용자가 `1.2M` 을 정확한 값으로 착각. 모바일 카드 한정 사용 + tooltip 또는 long-press 로 full value 노출.
- **리스크 3 — 표시 정밀도와 저장 정밀도 혼동**: 표시 자릿수 줄여도 backend 전달값(string)은 동일 정밀도. 폼 제출 경로에서 표시값을 다시 backend 로 보내지 않도록 코드 점검(현재는 react-hook-form 이 raw 입력 사용 — OK).
- **리스크 4 — 헤더 변경**: 기존 `useLogout` 의 `mutate` 호출은 그대로. 모바일 메뉴 추가 시 `useState` 토글, 라우트 변경 시 자동 닫힘 처리 필요.

## 12. 테스트 전략

- **단위**: `__tests__/lib/format.test.ts` 케이스 매트릭스 — { 통화: KRW/USD/USDT, 값: 0/양수/음수/큰값/소수, 옵션: trim trailing zeros }. 분기 ≥ 95%.
- **컴포넌트 smoke**: `summary-cards`, `holdings-list`(신규), `asset-list` 에 대한 jest+RTL 테스트 — 모바일 viewport 가정 시 데스크톱 전용 영역이 비표시되는지 확인 (`window.matchMedia` mock).
- **수동 회귀**: Chrome DevTools Mobile (375 / 414 / 768), Safari iOS Simulator, 다크/라이트 토글. 5개 핵심 페이지(`/dashboard`, `/assets`, `/assets/[id]`, `/settings`, `/login`).
- **커버리지 게이트**: `npx jest --coverage` 라인 ≥ 90% (`.claude/hooks/pre-push.sh`).

## 13. 범위 외 (Out of Scope)

- 새 페이지·라우트
- backend 변경 (Decimal → string 계약 그대로)
- shadcn 디자인 시스템 토큰 색상값 변경
- 차트 라이브러리 교체 / `recharts` 옵션 대규모 변경
- 하단 탭바 (Open Issue 1)
- 풀-스크린 네이티브 앱 시뮬레이션 (`apple-mobile-web-app-capable` 등) — 후속 PWA PRD

## 14. 오픈 이슈

- [ ] **Open Issue 1**: 모바일 헤더 — 햄버거 vs 하단 탭바 vs 현재 inline 유지. 1차 권장: inline 유지 + sticky. 사용자 결정 필요.
- [ ] **Open Issue 2**: 컴팩트 통화 표기 — `1.2억`(ko-KR compact) vs `1.2M`(en-US compact). 일관된 한 가지 규칙 결정 필요. 1차 권장: ko-KR (현재 locale 과 일치).
- [ ] **Open Issue 3**: 손익률 0 표시 — `0%` vs `±0%` vs `—`. 1차 권장: `0%` 부호 없음.
- [ ] **Open Issue 4**: 자산 카드 모바일에서 swipe-to-delete 추가 여부 — 1차 권장: 미도입(스크롤 충돌 위험).

---

## 역할별 책임 (모노레포)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| frontend | 모든 컴포넌트 / 레이아웃 / 포매터 / 테스트 | [`./ui-mobile-polish/frontend.md`](./ui-mobile-polish/frontend.md) |
| backend  | 변경 없음 — skip | [`./ui-mobile-polish/backend.md`](./ui-mobile-polish/backend.md) |
