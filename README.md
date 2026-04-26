<div align="center">

# AssetLog

**개인 포트폴리오 트래커 — 자산 등록부터 시간별 평가액 추적, 환산, 분석까지**

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)

<br/>

![Coverage Backend](https://img.shields.io/badge/backend_coverage-94%25-brightgreen)
![Coverage Frontend](https://img.shields.io/badge/frontend_coverage-95%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-1020+-brightgreen)

</div>

---

## 개요

**개인 단일 사용자**를 위한 자산 트래커. 한국·미국 주식 + 암호화폐를 한 곳에서 등록하고 시간별 평가액 추이를 본다.

- **자산 등록·매수/매도 기록** — 거래일·수량·단가·태그·메모. 가격은 시간 단위 자동 갱신
- **시계열 차트** — 1일 / 1주 / 1개월 / 1년 / 전체. recharts crosshair · brush zoom · 현재값 reference line
- **다중 통화 환산** — Frankfurter (ECB) 환율로 USD↔KRW 동적 변환. summary / holdings 모두 지원
- **태그별 분석** — DCA / 스윙 / 장기보유 등 태그로 거래 분류 → 매수/매도 flow 집계
- **CSV import / export** — 기존 거래 일괄 등록, 전체 데이터 백업 (JSON · CSV ZIP)
- **단일 사용자 보안** — 비밀번호 해시 환경변수 저장, DB 영속화 brute-force 방어, CSP 적용
- **다크 모드** — light / dark / system, FOUC 방지 inline script
- **샘플 데이터 1-클릭 시드** — 빈 계정에서 BTC · AAPL · 삼성전자 등 5개 자산 + 거래 자동 생성

---

## 주요 기능

### 거래 관리
- BUY / SELL 거래 기록 (timezone-aware traded_at, 단가, 메모, 태그)
- 거래 수정·삭제 (수정 결과가 음수 보유로 만들면 409)
- SELL 사전 검증 (서버 왕복 전 보유 수량 초과 차단)
- CSV 일괄 import — `type,quantity,price,traded_at,memo,tag` (한글 `매수`/`매도` 도 수락)

### 분석
- **시계열**: 사용자 거래 + 시간별 가격 스냅샷으로 buckets별 평가액 계산 — N+1 없는 포인터 스캔
- **realized P&L**: 가중평균(이동평균) 기준
- **태그별 flow**: 매수/매도 횟수와 통화별 합계
- **자산 비중 (allocation)**: asset_type 별 도넛 차트

### 인프라
- **시간별 가격 갱신 스케줄러** (yfinance, pykrx, ccxt 어댑터)
- **시간별 환율 갱신** (Frankfurter ECB)
- **로그인 시도 정리 잡** (90일 cutoff)

### 보안
- 단일 사용자 password-only 로그인 (env 기반 bcrypt 해시)
- IP별 5회 → 10분 lockout + progressive backoff (최대 1시간)
- 글로벌 50회/60초 한도 (botnet 방어)
- DB 영속화 (서버 재시작 무효화 X)
- HSTS / X-Frame-Options=DENY / X-Content-Type-Options / Referrer-Policy / Permissions-Policy
- CSP (nonce 기반 script-src + strict-dynamic)

---

## 기술 스택

| 레이어 | 스택 |
|--------|------|
| Backend | **Python 3.11+** · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 · uv |
| Frontend | **Next.js 15** (App Router) · TypeScript strict · Tailwind v4 · shadcn/ui · TanStack Query v5 · Zustand · React Hook Form + Zod · recharts |
| Database | MySQL 8 |
| Auth | bcrypt cost 12 · JWT (httpOnly · Secure · SameSite=Strict 쿠키) |
| Tests | pytest + httpx (backend) · Jest + React Testing Library (frontend) |
| Lint / Format | ruff + mypy strict · ESLint + tsc |
| External | yfinance · pykrx · ccxt · Frankfurter |

---

## 빠른 시작

### 1. 의존성 설치

```bash
# Backend
cd backend
uv sync

# Frontend
cd ../frontend
npm install
```

### 2. 데이터베이스 준비

```bash
# MySQL 에 assetlog DB 생성 (예시)
mysql -uroot -e "CREATE DATABASE assetlog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -e "CREATE USER 'assetlog'@'localhost' IDENTIFIED BY 'assetlog';"
mysql -uroot -e "GRANT ALL ON assetlog.* TO 'assetlog'@'localhost';"

# 마이그레이션
cd backend
uv run alembic upgrade head
```

### 3. 환경 변수 설정

```bash
# backend/.env.local
DATABASE_URL=mysql+asyncmy://assetlog:assetlog@localhost:3306/assetlog
JWT_SECRET_KEY=$(openssl rand -hex 32)
APP_PASSWORD_HASH='$2b$12$...'   # 아래에서 생성
COOKIE_SECURE=false               # HTTPS 환경에서는 true

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**비밀번호 해시 생성**:
```bash
python -c 'import bcrypt; print(bcrypt.hashpw(b"내-비밀번호", bcrypt.gensalt(rounds=12)).decode())'
```

> ⚠️ `APP_PASSWORD_HASH` 미설정 시 로그인 시도하면 503 "Owner password not configured" 응답. 의도된 동작입니다.

### 4. 실행

```bash
# 터미널 1 — backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# 터미널 2 — frontend
cd frontend
npm run dev
```

브라우저에서 `http://localhost:3000` → 비밀번호 입력 → `/dashboard`.

### 5. 첫 사용 (샘플 데이터)

빈 화면에서 **"샘플 데이터로 시작"** 클릭 → BTC · ETH · AAPL · 삼성전자 · 현대차 + 12개월 분산 거래 자동 생성. 가격 / 환산 / 차트 / 태그 모든 기능을 즉시 확인 가능.

---

## 아키텍처

### 모노레포 구조

```
assetlog/
├── backend/           # FastAPI · Python — JSON API 만 서빙
│   └── CLAUDE.md      # backend 전용 규칙
├── frontend/          # Next.js · TypeScript — UI 호스팅
│   └── CLAUDE.md      # frontend 전용 규칙
├── .claude/
│   ├── stacks.json    # mode: "monorepo", stacks: [backend(python), frontend(nextjs)]
│   ├── agents/        # python-{generator|modifier|tester}, nextjs-{generator|modifier|tester}, ...
│   └── hooks/         # safety-guard / pre-push 커버리지 게이트 등
├── memory/
│   └── MEMORY.md      # Second Brain (세션 시작 시 자동 로드)
├── docs/              # PRD / GTM (필요 시 자동 생성)
└── README.md
```

### Backend 레이어

```
routers → services → repositories → models
                          ↓
                       schemas (Pydantic)
```

- `models/` — SQLAlchemy 2.0 ORM (`Mapped` + `mapped_column`)
- `schemas/` — Pydantic v2 Request/Response (Decimal 은 string 직렬화)
- `repositories/` — AsyncSession 기반 데이터 접근
- `services/` — 비즈니스 로직 (FastAPI/HTTPException import 금지)
- `routers/` — APIRouter (메타: `response_model`, `responses`, `summary`)
- `exceptions.py` — 도메인 커스텀 예외 → `main.py` 의 `@app.exception_handler` 에서 HTTP 변환
- `adapters/` — 외부 가격/환율 API 어댑터
- `scheduler/` — 시간별 가격·환율 refresh, 90일 login_attempts 정리

### Frontend 레이어

```
app/                  # App Router (라우팅만)
components/
  ├── features/       # 도메인 컴포넌트 (assets, portfolio, auth)
  └── ui/             # shadcn primitives
hooks/                # TanStack Query / Zustand 훅
lib/
  ├── api/            # axios 기반 API 클라이언트 (raw → camelCase 변환)
  └── schemas/        # Zod 스키마
stores/               # Zustand (theme 등)
types/                # 도메인 타입
```

---

## 워크플로

```
/planner <기능>                # 1. 요청을 PRD 로 구조화 + 역할별 프롬프트 분배
/plan backend api Order        # 2a. backend API 설계 (OpenAPI 3.0)
/plan backend db payment       # 2b. backend DB 스키마 → Alembic
                               # 3. python-generator / nextjs-generator 가 구현
/test                          # 4. 테스트 자동 생성
/review                        # 5. 양 스택 일괄 리뷰
/commit → /pr → /merge         # 6. 커밋 → PR → 머지 (각 단계 자동 제안)
```

---

## 커버리지 게이트

`git push` 시 `.claude/hooks/pre-push.sh` 가 활성 스택 전부 순차 검증. **임계값 90%** (라인 기준). 한 스택이라도 실패하면 push 차단.

| 스택 | 도구 | 게이트 |
|------|------|--------|
| Backend | `pytest --cov=app` | 90%+ |
| Frontend | `jest --coverage` | 90%+ |

현 상태: backend 94% / frontend 95.81%.

---

## 보안

| 항목 | 적용 |
|------|------|
| 비밀번호 저장 | DB ❌ → **환경변수 `APP_PASSWORD_HASH`** (bcrypt cost 12, constant-time 비교) |
| Brute-force 방어 | DB 영속화 + IP별 progressive backoff (5→10→15→20+ : 600/1200/2400/3600s cap) |
| 분산 IP 공격 방어 | 글로벌 50회/60초 한도 |
| 인증 토큰 | JWT · HttpOnly · Secure · SameSite=Strict 쿠키 |
| HTTP 헤더 | HSTS · X-Content-Type-Options · X-Frame-Options=DENY · Referrer-Policy · Permissions-Policy |
| CSP | nonce 기반 script-src + strict-dynamic, frame-ancestors 'none' |
| 회원가입 | 엔드포인트·페이지 완전 삭제 (단일 사용자 모드) |

> 자세한 위협 모델 / 알려진 한계는 [PR #35](https://github.com/nogamsung/assetlog/pull/35) 본문 참고.

---

## 개발

### 명령어

**Backend** (`backend/`)
```bash
uv sync                              # 의존성 설치
uv run uvicorn app.main:app --reload # 개발 서버 (http://localhost:8000)
uv run pytest --cov=app              # 테스트 + 커버리지
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run alembic revision --autogenerate -m "..."
uv run alembic upgrade head
```

**Frontend** (`frontend/`)
```bash
npm install
npm run dev                          # 개발 서버 (http://localhost:3000)
npx jest --coverage --watchAll=false
npx tsc --noEmit
npm run lint
```

### Git 전략

```
main  ←──── feature/{name}   (작업 브랜치)
            fix/{name}
            hotfix/{name}
            refactor/{name}
            chore/{name}
```

각 브랜치는 `.worktrees/{type}-{name}/` 에 격리된 작업공간으로 생성될 수 있습니다 (Claude Code Starter 워크플로). `main` 직접 push 금지.

### 모노레포 규칙

- **스택 경계 유지** — `backend/` ↛ `frontend/` 직접 참조 금지. API 계약(`docs/api/*.yaml`)으로만 연결
- **의존성 독립** — 각 스택 독립 manifest (`pyproject.toml`, `package.json`). 루트 공유 manifest 없음
- **CI 분리** — GitHub Actions `paths-filter` 로 변경된 스택만 실행
- **PR 스코프** — 가능하면 PR 당 1개 스택. 걸치면 커밋 분리

---

## 디렉토리 구조

```
assetlog/
├── backend/
│   ├── app/
│   │   ├── adapters/          # 외부 가격/환율 API (yfinance, pykrx, ccxt, frankfurter)
│   │   ├── core/              # config, deps, security
│   │   ├── db/                # Base, async engine, sessionmaker
│   │   ├── domain/            # 도메인 enum, dataclass (TransactionType, HistoryPeriod 등)
│   │   ├── exceptions.py      # 커스텀 예외
│   │   ├── main.py            # FastAPI 앱 + 미들웨어 + lifespan
│   │   ├── middleware/        # SecurityHeadersMiddleware
│   │   ├── models/            # SQLAlchemy ORM
│   │   ├── repositories/      # AsyncSession 기반 데이터 접근
│   │   ├── routers/           # APIRouter
│   │   ├── scheduler/         # APScheduler jobs (price/fx refresh, login cleanup)
│   │   ├── schemas/           # Pydantic v2 Request/Response
│   │   └── services/          # 비즈니스 로직
│   ├── alembic/versions/      # Alembic migrations
│   ├── tests/                 # pytest (services, routers, repositories, integration)
│   ├── pyproject.toml
│   └── CLAUDE.md
├── frontend/
│   ├── src/
│   │   ├── app/               # App Router
│   │   │   ├── (app)/         # 인증 필요 (dashboard, assets, settings)
│   │   │   ├── (auth)/login   # 비밀번호 입력
│   │   │   ├── layout.tsx     # CSP nonce 적용
│   │   │   └── globals.css    # light/dark 토큰
│   │   ├── components/
│   │   │   ├── features/      # 도메인 컴포넌트
│   │   │   ├── ui/            # shadcn primitives
│   │   │   ├── theme-provider.tsx
│   │   │   └── theme-toggle.tsx
│   │   ├── hooks/             # TanStack Query / Zustand 훅
│   │   ├── lib/
│   │   │   ├── api/           # axios 기반 API 클라이언트
│   │   │   ├── schemas/       # Zod 스키마
│   │   │   └── chart-format.ts
│   │   ├── stores/            # Zustand (theme persist)
│   │   ├── types/             # 도메인 타입
│   │   └── __tests__/         # Jest
│   ├── middleware.ts          # 인증 가드 + CSP nonce
│   ├── jest.config.ts         # coverageThreshold.global.lines: 90
│   └── package.json
├── .claude/                   # Claude Code 하네스 (agents, commands, hooks, skills, templates)
├── memory/MEMORY.md           # Second Brain
├── docs/                      # PRD / API / GTM (선택)
└── README.md
```

---

## API 개요

| 엔드포인트 | 설명 |
|----------|------|
| `POST /api/auth/login` | 비밀번호로 로그인 (httpOnly 쿠키 발급) |
| `POST /api/auth/logout` · `GET /api/auth/me` | 로그아웃 / 세션 확인 |
| `GET /api/symbols?q=` · `POST /api/symbols` | 자산 심볼 검색 / 직접 등록 |
| `GET / POST / DELETE /api/user-assets` | 보유 자산 목록 / 등록 / 삭제 |
| `POST / GET / PUT / DELETE /api/user-assets/{id}/transactions` | 거래 CRUD |
| `GET /api/user-assets/{id}/summary` | 자산별 요약 (보유/매수/매도/실현손익) |
| `GET /api/user-assets/{id}/transactions/import` | CSV 일괄 import |
| `GET /api/user-assets/transactions/tags` | 사용자 distinct 태그 목록 |
| `GET /api/portfolio/summary?convert_to=` | 통화별 + 환산 요약 |
| `GET /api/portfolio/holdings?convert_to=` | 자산별 평가액 + 환산 |
| `GET /api/portfolio/history?period=&currency=` | 시계열 평가액 |
| `GET /api/portfolio/tags/breakdown` | 태그별 거래 flow 집계 |
| `GET /api/fx/rates` | 캐시된 환율 목록 |
| `POST /api/sample/seed` | 샘플 데이터 시드 (idempotent) |
| `GET /api/export?format=json\|csv` | 전체 데이터 다운로드 |

전체 OpenAPI 문서는 dev 서버에서 `http://localhost:8000/docs` (Swagger UI).

---

## 라이선스

이 프로젝트는 개인 사용 목적으로 작성되었습니다.

---

<div align="center">

🤖 Built with [Claude Code](https://claude.ai/code) using [claude-code-starter](https://github.com/nogamsung/claude-code-starter)

</div>
