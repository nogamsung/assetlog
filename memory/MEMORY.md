# Second Brain — assetlog

> 이 파일은 프로젝트의 기관 기억(institutional memory)입니다.
> 기술 결정, 교훈, 반복되는 패턴을 여기에 누적하세요.
> 규칙은 `CLAUDE.md`, 맥락과 히스토리는 이 파일에 기록합니다.

---

## 2026-04-23: 프로젝트 시작

**카테고리:** 결정

- **프로젝트명:** assetlog
- **모드:** 모노레포 (backend + frontend)
- **스택:** backend (python / FastAPI) + frontend (nextjs / Next.js 16)
- **목적:** 개인 자산 포트폴리오 트래커 — 보유 자산을 등록하고 시간 단위로 가격을 새로고침하여 평가액·수익률을 집계
- **핵심 기능:**
  - 다중 자산 클래스 지원 — 미국 주식 (`yfinance`), 한국 주식 (`pykrx`, `finance-datareader`), 암호화폐 (`ccxt`)
  - `apscheduler` 기반 주기적 가격 갱신 (시간 단위)
  - 자산별 매수 기록 + 현재가 기반 손익 계산
  - FastAPI REST + Next.js 대시보드
- **제약사항:**
  - Node 18.20.8 환경 — Next.js 15+ 는 Node ≥20.9.0 필요. 로컬 실행 전 `nvm use 20` 또는 업그레이드 필요
  - Python 가상환경은 `backend/.venv` (uv 전환 검토)
- **외부 연동:** yfinance · pykrx · finance-datareader · ccxt (requirements.txt 기준)

---

## 2026-04-23: Claude Code 하네스 구성

**카테고리:** 참고

`/init monorepo` 로 하네스를 구성했습니다.
- `CLAUDE.md` — 루트 인덱스 + `backend/CLAUDE.md` (python) + `frontend/CLAUDE.md` (nextjs)
- `.claude/settings.json` — 권한 및 훅 설정 (python/nextjs 관련 bash 권한만)
- `.claude/stacks.json` — 스택 매니페스트
- `memory/MEMORY.md` — Second Brain 초기화
- Git 전략: **main only** (B), 원격 `git@github.com:nogamsung/assetlog.git`
- `frontend/.git` 제거 → 루트 단일 git repo 로 통합

앞으로 중요한 결정·교훈은 `/memory add` 로 기록하세요.

---

## 2026-04-23: JWT 저장소 결정 — httpOnly cookie

**카테고리:** 결정

PRD 오픈 이슈 #4 (JWT storage) 해소. 사용자 요청("JWT 는 backend, frontend 둘다 구현해줘") 에 대해 선택:

- **결정**: access token 을 `httpOnly` + `Secure` + `SameSite=Strict` **쿠키**로 발급. localStorage 저장 금지.
- **Backend**: `/auth/login`·`/auth/signup` 응답에서 `Set-Cookie`. `/auth/logout` 은 쿠키 삭제. 인증 의존성은 `request.cookies["access_token"]` 파싱 (Authorization 헤더 fallback 유지해 MCP/CLI 테스트도 허용).
- **Frontend**: axios 전역 `withCredentials: true`. 로그인 응답 바디에는 token 을 넣지 않고, 이후 요청은 쿠키 자동 첨부. CSRF 방어는 `SameSite=Strict` + 필요 시 double-submit cookie 후속.
- **CORS**: backend `allow_credentials=True` + `allow_origins=[FRONTEND_ORIGIN]` 명시. 와일드카드(`*`) 금지.
- **만료**: access 60분, refresh 는 MVP 제외(후속). 만료 시 frontend 는 401 인터셉터 → 로그인 페이지 리다이렉트.

**이유:** localStorage 는 XSS 발생 시 JavaScript 로 직접 탈취 가능. httpOnly cookie 는 JS 접근 차단으로 XSS 내성 훨씬 높음. CSRF 는 SameSite 로 1차 차단.

**관련 파일:** `docs/specs/asset-tracking.md` (§12 오픈 이슈 #4 해소됨 표시), `docs/specs/asset-tracking/backend.md` (§8 인증), `docs/specs/asset-tracking/frontend.md` (§7 인증 플로우), `docs/api/asset-tracking.yaml` (`securitySchemes`).

---

## 2026-04-23: Auto-memory 훅 시스템 구축

**카테고리:** 결정

장시간 세션에서 `SessionStart` 만으로는 `memory/MEMORY.md` 가 모델 컨텍스트에서 휘발되고, "중요한 결정 잊지 말고 기록" 이 누락되는 문제. 2개 훅 추가:

- **UserPromptSubmit** → `.claude/hooks/memory-context.sh`: 매 프롬프트마다 MEMORY.md 최근 60줄 + `[Auto-memory directive]` 를 `hookSpecificOutput.additionalContext` 로 주입. Claude 는 매 턴 시작 시 직전 턴에 기록할 가치가 있는지 판단해 먼저 MEMORY 에 추가한 뒤 새 요청 처리.
- **Stop** → `.claude/hooks/memory-reminder.sh` (확장): 기존 stack-tests 유지 + stderr 로 기록 리마인더 echo (UI 표시).

**설계 포인트:** stderr 는 모델 컨텍스트에 주입되지 **않는다** — "자동 기록" 을 실제로 동작시키려면 `hookSpecificOutput.additionalContext` JSON 출력이 필수. 사용자는 stderr 를 요청했으나 Stop 은 user-visible nudge, UserPromptSubmit 은 모델 주입으로 역할 분리.

**관련 파일:** `.claude/settings.json` (hooks.UserPromptSubmit, hooks.Stop), `.claude/hooks/memory-context.sh`, `.claude/hooks/memory-reminder.sh`.
