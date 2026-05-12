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

---

## 2026-04-23: bcrypt 직접 사용 (passlib 드롭)

**카테고리:** 결정

비밀번호 해싱 라이브러리 결정:

- **결정**: `passlib[bcrypt]` 제거 → `bcrypt>=4.0.0` **직접 사용**.
- **이유**: bcrypt 5.0 + passlib 조합에서 `AttributeError: module 'bcrypt' has no attribute '__about__'` 호환성 버그. passlib 는 `bcrypt.__about__.__version__` 를 런타임 탐지하는데 bcrypt 5.0 에서 해당 속성 제거됨. passlib 가 정체 상태라 upstream 픽스 지연.
- **구현**: `app/core/security.py` 에서 `bcrypt.hashpw(plain.encode(), bcrypt.gensalt())` / `bcrypt.checkpw(...)` 직접 호출.
- **영향**: 미래에 argon2 등으로 바꾸려면 해싱 헬퍼 2개 함수만 교체하면 됨 (인터페이스 `hash_password(str) -> str`, `verify_password(str, str) -> bool` 유지).

**관련 파일:** `backend/app/core/security.py`, `backend/pyproject.toml` (`passlib` 삭제, `bcrypt>=4.0.0` + `pydantic[email]` 추가).

---

## 2026-04-24: AssetType — `native_enum=False` (String 컬럼 저장)

**카테고리:** 결정

`AssetSymbol.asset_type` (`crypto` / `kr_stock` / `us_stock`) 의 DB 저장 방식:

- **결정**: SQLAlchemy `Enum(AssetType, native_enum=False, length=16)` — MySQL 네이티브 ENUM 대신 **VARCHAR 컬럼**으로 저장. Python 레벨에서는 `enum.StrEnum` (Python 3.11+) 으로 유지.
- **이유**: MySQL 네이티브 ENUM 은 값 추가 시 `ALTER TABLE ... MODIFY COLUMN` 필요 → 대용량 테이블 락·오프라인 마이그레이션 위험. 문자열 컬럼은 마이그레이션 없이 새 값 추가(앱 배포만으로 충분). 조회 비용 차이는 무시 수준.
- **패턴**: 모든 미래 enum 필드(예: `TransactionType(buy/sell)`, 후속 `price_source` 등) 에 동일 원칙 적용.
- **주의**: 문자열이라 DB 레벨 제약은 없음 — 유효성은 Pydantic/Service 계층에서 검증. 잘못된 값이 들어가면 `AssetType(value)` 호출 시 `ValueError` → 도메인 레이어에서 처리.

**관련 파일:** `backend/app/domain/asset_type.py` (StrEnum), `backend/app/models/asset_symbol.py` (`SqlEnum(..., native_enum=False)`).

---

## 2026-04-24: API 인증 범위 — 전 엔드포인트 인증 필수 (MVP)

**카테고리:** 결정

공개 엔드포인트 정책:

- **결정**: MVP 에서는 `/api/auth/signup`·`/api/auth/login` 외 **모든** `/api/**` 엔드포인트에 `Depends(get_current_user)` 강제. 심볼 마스터 검색(`GET /api/symbols`) 도 인증 필수.
- **이유**: (1) 포트폴리오 트래커라 사용자 컨텍스트 없이 가치 있는 기능 없음 (2) 미인증 공개 노출은 남용/추적 복잡도 증가 (3) CORS `allow_credentials=True` + httpOnly cookie 정책과 일관
- **예외 허용 기준** (후속 PR 에서 도입 시): 랜딩 페이지용 심볼 자동완성처럼 "로그인 전 UX" 가 명확히 필요한 엔드포인트만 **명시적으로** public. 기본값은 protected.
- **frontend**: `middleware.ts` 가 `access_token` 쿠키 없으면 `/login?from=<path>` 로 리다이렉트. 공개 허용 경로는 `/login`·`/signup`·정적 리소스뿐.

**관련 파일:** `backend/app/routers/*.py` (모든 라우터 `Depends(get_current_user)`), `frontend/middleware.ts`, `docs/specs/asset-tracking.md` §3 (보안).

---

## 2026-04-24: Money/수량 `Decimal` 정밀도 원칙

**카테고리:** 규칙

금액(`price`, `total_invested`, `avg_buy_price`) 과 수량(`quantity`) 처리 규칙:

- **결정**: Python `Decimal` 만 사용. `float` 절대 금지.
- **DB 타입**: `Numeric(20, 6)` (가격) / `Numeric(28, 10)` (수량 — 암호화폐 정밀도 고려).
- **SQLite 테스트 환경 주의**: SQLite 는 `NUMERIC` 를 REAL 로 저장할 수 있어 SQL AGG (`SUM`, `AVG`) 결과가 `float` 로 Python 에 전달될 수 있음. 이 경우 **`Decimal(str(row.xxx))`** 로 문자열 경유 변환 필수 — `Decimal(float)` 은 이진 부동소수 표현을 그대로 가져와 `0.1` 이 `Decimal('0.1000000000000000055511151231257827021181583404541015625')` 가 됨.
- **MySQL 프로덕션**: `DECIMAL` 을 Python `Decimal` 로 받아오므로 `str(...)` 경유 불필요. 하지만 SQLite 호환성을 위해 문자열 경유 패턴을 **항상** 사용 — 코드 분기 단순화.
- **API 응답**: Pydantic 이 `Decimal` 을 자동으로 JSON string 으로 직렬화 (`"1.5000000000"`). 프론트엔드는 문자열로 받아 BigDecimal 라이브러리 없이 표시만 할 때는 `parseFloat` OK, 계산 개입 시 `decimal.js` 도입 검토.

**관련 파일:** `backend/app/models/transaction.py` (`Numeric`), `backend/app/repositories/transaction.py` (`get_summary` 에서 `Decimal(str(...))`), `backend/app/schemas/transaction.py` (`Decimal` 타입 + Pydantic 자동 직렬화).

---

## 2026-04-24: 로컬 개발 환경 — 네이티브 MySQL + Node 20 + .env.local

**카테고리:** 참고

로컬 실행 구성 확정:

- **MySQL**: 네이티브 설치본(`/usr/local/mysql/bin/mysql`, 8.0.29)을 그대로 사용 — Docker 안 씀. 포트 3306 이미 네이티브가 점유 중이라 `docker-compose.yml` 은 **템플릿으로만** 남김.
- **DB 이름**: `assetlog_local` (로컬), 접속 유저는 `root`. 비밀번호는 `backend/.env.local` 에만 보관, **절대 커밋 금지**.
- **Node**: Next.js 16 은 Node ≥20.9.0 필수. 시스템 기본이 18.20.8 이면 `source ~/.nvm/nvm.sh && nvm use 20` 후 `npm install` → `npm run dev`. darwin-arm64 환경에서 Node 18 로 설치한 `node_modules` 는 `@tailwindcss/oxide` native binding 에러 발생 — 반드시 `rm -rf node_modules package-lock.json && nvm use 20 && npm install` 로 재설치.
- **환경 파일**: `.env.example` / `.env.local.example` 만 추적. `.env`, `.env.*` (`.env.local`, `.env.dev`, `.env.prd` 포함) 는 root + backend `.gitignore` 로 차단. `backend/app/core/config.py` 는 `env_file=(".env", ".env.local")` — 둘 다 있으면 `.env.local` 이 override.
- **Alembic**: 병렬 슬라이스 두 개가 같은 부모에서 분기해 heads 두 개가 되면 `uv run alembic merge -m "..." HEAD1 HEAD2` 로 merge revision 생성 후 `upgrade head`.
- **포트**: backend `8000`, frontend `3000`. `frontend/.env.local` 의 `NEXT_PUBLIC_API_URL` 은 `http://localhost:8000` (과거 8080 오타 수정됨).

**기동 순서:** MySQL 기동 확인 → `cd backend && uv run alembic upgrade head` → `uv run uvicorn app.main:app --port 8000 --reload` → 다른 터미널에서 `cd frontend && nvm use 20 && npm run dev`.

---

## 2026-05-12: 외부 거래내역 import — 합성 external_id 정책 (#93)

**카테고리:** 규칙

토스증권/신한증권/케이뱅크/카카오뱅크 등 외부 import 의 dedupe 키 정책. Upbit OpenAPI (#87) 처럼 거래소 고유 주문 ID 가 있으면 그걸 그대로 쓰지만, **PDF/Excel 파일 import 는 거래 ID 가 없어 합성키가 필요**.

- **원칙**: 거래의 **본질적 고유성** 만 사용. PDF 출력 컨텍스트 (잔액·합산·발급번호) 는 **제외**.
  - Transaction (BUY/SELL): `sha256("{date}|{BUY|SELL}|{symbol}|{qty}|{price}")[:32]`
  - Dividend: `sha256("{date}|{symbol}|{amount}|{currency}")[:32]`
  - CashAccountTransaction (이자): `sha256("{date}|INTEREST|{amount}|{currency}")[:32]`
- **이유**: 잔액을 키에 포함하면 같은 거래라도 다른 기간 PDF 재발급 시 잔액 컬럼이 달라져 dedupe 실패. 사용자 요청.
- **부작용 (수용)**: 같은 일자·동일 가격·동일 수량 매매 N건은 1건으로 합쳐짐. 토스 PDF 는 거래 시각이 없어 어차피 구분 불가.
- **DB 보장**: `(external_source, external_id)` UNIQUE 인덱스 — Transaction (`#87`), Dividend (`b4d3bc99048f`), CashAccountTransaction (`d5e8d86ff010`).
- **시간 정책**: PDF 거래일자(YYYY.MM.DD) → KST 자정 (00:00 Asia/Seoul) → UTC 변환 후 저장.

**관련 파일**: `backend/app/adapters/parsers/{base,toss_securities}.py`, `backend/app/services/exchange_sync.py` (`import_records` 분기), `backend/app/tools/parse_preview.py` (CLI dry-run).

---

## 2026-05-12: KST + 24시간 시간 표기 통일 (#122)

**카테고리:** 규칙

프론트엔드의 모든 시간 표시는 **`frontend/src/lib/datetime.ts`** 의 헬퍼 (`formatDateTimeKST`, `formatDateKST`, `formatTimeKST`, `formatChartTickKST`) 를 통해서만 출력. **Asia/Seoul + hour12: false 강제**.

- **이유**: `toLocaleString("ko-KR", { hour: "2-digit" })` 는 hour12 미지정 시 일부 브라우저에서 "오후 3:30" (12h) 출력. 사용자 OS 시간대에 따라 시간이 달라짐.
- **백엔드는 변경 없음** — UTC tz-aware 저장 유지. 프론트에서만 변환.
- **금지**: 컴포넌트에서 `new Date(x).toLocaleString(...)` 직접 호출, date-fns `format` 의 timeZone 미지정 사용. 새 시간 표시 추가 시 반드시 datetime.ts 헬퍼 도입.

**관련 파일**: `frontend/src/lib/datetime.ts`, `frontend/src/lib/chart-format.ts`.

---

## 2026-05-12: Upbit API key — env-only 정책 (#125)

**카테고리:** 결정

업비트 read-only API 키 (`UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY`) 는 **서버 환경변수에만** 보관. **DB 저장하지 않음**.

- **전제**: 단일 사용자 self-host 환경 (CLAUDE.md "단일 사용자 계정"). 키 회전 시 `.env` 수정 → 재시작.
- **다중 사용자가 되면 재검토** — 사용자별 키 관리 (암호화 저장 + UI 등록 폼) 가 필요해짐. 현재는 YAGNI.
- **UX**: 설정 → 거래소 동기화 → "지금 동기화" 버튼만. 키 미설정 시 502 → "환경변수 안내" 토스트.
- **자동 트리거**: `app/scheduler` 에서 일 1회 자동 sync (#87 도입).

**관련 파일**: `backend/app/core/config.py` (`upbit_access_key`/`upbit_secret_key`), `backend/app/routers/integration.py` (`sync_upbit`), `frontend/src/components/features/settings/exchange-sync-section.tsx`.
