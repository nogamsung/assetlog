---
feature: price-refresh
title: 가격 자동 갱신 스케줄러 + 3대 자산 어댑터
author: planner-agent
created_at: 2026-04-24
status: Draft
priority: P0
stack_scope: [backend]
parent_prd: docs/specs/asset-tracking.md
owners:
  backend: backend (FastAPI / Python)
related_docs:
  - docs/specs/price-refresh/backend.md
---

# PRD — 가격 자동 갱신 스케줄러 + 3대 자산 어댑터

> **상위 PRD**: [`asset-tracking.md`](./asset-tracking.md) — 특히 **6.3 가격 자동 갱신 플로우**, **9. 외부 의존성**, **4.2 범위 경계 원칙**, **11. 리스크 R-1 ~ R-5** 를 인용하며 범위를 좁힙니다.
>
> 이 슬라이스는 **backend 전용** (FastAPI / Python). frontend 변경 없음.

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-24 |
| 상태 | Draft |
| 스택 범위 | backend only (python / FastAPI) |
| 우선순위 | P0 |
| 상위 PRD | `docs/specs/asset-tracking.md` |
| 브랜치 | `feature/price-refresh` (worktree `.worktrees/feature-price-refresh/`) |

---

## 1. 배경

`asset-tracking.md` §6.3 의 **가격 자동 갱신 플로우**를 실제로 구동할 스케줄러·어댑터 구현이 현재 비어 있다. 직전 슬라이스(`portfolio-dashboard`) 에서 `AssetSymbol.last_price`, `last_price_refreshed_at` 캐시 필드와 이를 읽는 포트폴리오 집계 API 만 완성된 상태로, **캐시를 채우는 주체가 없어 모든 종목이 `pending` 상태**다.

본 슬라이스는 상위 PRD **US-6 (시간 단위 현재가 갱신)** 과 **US-10 (stale 경고)** 을 실제로 만족시키기 위해 (1) in-process `AsyncIOScheduler` 를 FastAPI lifespan 에 연동하고 (2) 3대 자산 클래스 (국내주식·미국주식·암호화폐) 의 외부 시세 어댑터를 추상화된 인터페이스로 구현한다.

## 2. 목표 (Goals)

- **Goal 1 — 시간 단위 자동 갱신**: apscheduler `AsyncIOScheduler` 가 매시 정각(0분, `Asia/Seoul`) 에 `refresh_all_prices` job 을 실행. 단일 uvicorn 워커(`--workers 1`) 가정.
- **Goal 2 — 어댑터 추상화**: `PriceAdapter` Protocol 을 기반으로 `kr_stock` / `us_stock` / `crypto` 3개 어댑터를 독립 모듈로 구현. 라이브러리 교체·테스트 모킹 용이성 확보.
- **Goal 3 — 실패 격리**: 한 심볼 실패가 다른 심볼 또는 다른 어댑터의 갱신을 차단하지 않음. 실패 종목은 `last_price` 유지 + structured warning 로그.
- **Goal 4 — 시계열 적재**: 성공 조회마다 `PricePoint` 1 행 append + `AssetSymbol.{last_price,last_price_refreshed_at}` 캐시 upsert.
- **Goal 5 — 장외시간 우아한 대응**: 휴장일/장 마감 시에도 어댑터가 **최근 거래일 종가** 를 반환하여 `stale` 오판을 줄인다.

**측정 지표** (상위 PRD §5 재확인):
- 가격 갱신 성공률 ≥ 99% / 1 시간 윈도우 (대상 종목 중 `success_count / total`).
- 1 사이클 소요 < 5분 (500 심볼 기준, 상위 PRD §10 비기능 요구사항).
- 커버리지 ≥ 80% (이 PRD 에서는 새 모듈 100% 를 내부 목표).

## 3. 비목표 (Non-goals)

이번 슬라이스에서 **하지 않는 것**:

- ❌ **환율 통합 환산 (KRW↔USD)** — v2.0 (상위 PRD §14)
- ❌ **분산 스케줄러 / leader election** — MVP 는 `uvicorn --workers 1` 고정. 상위 PRD R-5 의 v2 항목.
- ❌ **가격 알림 / 웹훅 / 임계치 알람** — v1.3 (상위 PRD §14)
- ❌ **관리자용 수동 트리거 엔드포인트** (`POST /admin/refresh-prices` 등) — 필요 시 후속 이슈
- ❌ **자산 등록 직후 on-demand 최초 시세 fetch** — 별도 이슈로 기록 (오픈 이슈 참조)
- ❌ **`holidays` 패키지 필수 도입** — 선택사항. 어댑터 내부에서 "최근 거래일 종가" fallback 으로 1차 대응
- ❌ **프론트엔드 UI 변경** — `last_price_refreshed_at` 은 이미 `/portfolio/summary` 응답에 포함됨. stale 배지 UI 는 이미 `portfolio-dashboard` 슬라이스에서 처리됨 (보강은 별도 이슈)

## 4. 대상 사용자

- **시스템 자체** (내부 job) — 외부 actor 없음
- 간접 수혜자: 상위 PRD 의 Persona A / B (대시보드에서 현재가·수익률을 보는 일반 사용자)

## 5. 유저 스토리 (상위 PRD 재확인)

| # | 스토리 (상위 PRD 인용) | 이 슬라이스에서의 수락 기준 |
|---|-----------------------|---------------------------|
| **US-6** | 사용자로서 시간 단위로 자동 갱신된 현재가로 평가액·수익률을 확인할 수 있어야 한다 | 1) `AsyncIOScheduler` 가 앱 기동 시 자동 start, 매시 0분에 trigger 됨 (로그로 검증) / 2) job 1회 실행 후 distinct `(asset_type, symbol)` 모두에 대해 adapter 호출 시도 / 3) 성공 건마다 `AssetSymbol.last_price`, `last_price_refreshed_at`(UTC) 갱신 + `PricePoint` append |
| **US-10** | 사용자로서 가격이 장시간 갱신되지 않으면 경고를 받아야 한다 | 1) 개별 심볼 실패 시 `last_price` **미갱신 (기존값 유지)** / 2) 실패는 구조화 warning 로그 (`symbol`, `asset_type`, `exchange`, `error_class`, `error_msg`) / 3) 상위 대시보드 API 가 이미 stale 판정 수행 (`portfolio-dashboard` 완료) — 본 슬라이스는 **원인 측(갱신 실패)** 만 담당 |
| **R-1 ~ R-4** (리스크 재확인) | 외부 API 구조 변경·rate limit·거래소별 심볼 불일치 대응 | 1) adapter Protocol 추상화 / 2) kr_stock 은 pykrx 1차 + finance-datareader fallback / 3) crypto 는 ccxt 기본 binance + upbit fallback / 4) 거래소별 심볼 정규화 규칙 문서화 및 단위 테스트 |

## 6. 핵심 플로우 (상위 PRD §6.3 상세화)

```
[앱 기동]
1. FastAPI lifespan 진입
2. AsyncIOScheduler 인스턴스 생성 (timezone="Asia/Seoul")
3. refresh_all_prices 를 CronTrigger(minute=0) 로 등록
4. scheduler.start()
5. yield (앱 실행)
...
[매시 0분]
6. job 진입 — structured log "price_refresh.start" (job_id, planned_symbols)
7. Repository 에서 distinct (asset_type, exchange, symbol) 로드
8. asset_type 별 그룹핑 → 해당 PriceAdapter 주입
9. 각 adapter.fetch_batch(symbols) 호출
   - 성공: (symbol, price, currency, fetched_at) 반환
   - 실패: 개별 symbol 단위로 예외 격리 → fallback adapter 시도
10. 성공 결과 → PricePointRepository.bulk_insert + AssetSymbolRepository.bulk_update_cache
11. 실패 결과 → warning 로그 (PII 제외)
12. 사이클 종료 log "price_refresh.done" (success, failed, elapsed_ms)
[앱 종료]
13. lifespan 종료 시 scheduler.shutdown(wait=False)
```

### 예외 경로
- **전체 DB 장애** → job 은 fail-fast, 다음 사이클에서 재시도. 스케줄러는 죽지 않음.
- **어댑터 라이브러리 rate limit** → 개별 symbol 실패로 격리. 다음 사이클에서 재시도. 재시도 백오프는 MVP 범위 외.
- **휴장일 / 장외시간** → 어댑터가 최근 거래일 종가 반환. `fetched_at` 은 조회 시점 UTC, `PricePoint.price` 는 종가. `stale` 여부는 대시보드가 `last_price_refreshed_at` 기준으로 판정하므로 여기서는 영향 없음.
- **알 수 없는 거래소 / 심볼 정규화 실패** → 해당 심볼만 warning 로그 후 skip. 전체 사이클 계속.

## 7. 데이터 모델 (이미 존재 / 확인)

이 슬라이스는 **신규 테이블 없음** — 기존 모델만 활용:

| 엔티티 | 상태 | 역할 |
|--------|------|------|
| `AssetSymbol` | **존재** (이미 `last_price`, `last_price_refreshed_at` 컬럼 보유 — `portfolio-dashboard` 슬라이스에서 추가됨) | 어댑터 대상 목록, 캐시 갱신 대상 |
| `PricePoint` | **확인 필요** — 없으면 이 슬라이스에서 **신규 추가** (대응 migration 1개) | 시계열 스냅샷 (`asset_symbol_id`, `price`, `currency`, `fetched_at` timezone-aware) |

> ⚠️ `PricePoint` 존재 여부는 backend 프롬프트에서 먼저 확인하고, 없으면 migration 을 생성한다.

## 8. API 계약 (요약)

이 슬라이스는 **신규 외부 API 엔드포인트 없음**. 기존 `/portfolio/*` 응답의 `last_price_refreshed_at` 이 자동으로 채워지게 되는 **행위 변화** 만 있음 (계약 동일).

### 내부 인터페이스 (모듈 간)

```python
# app/adapters/base.py
class PriceAdapter(Protocol):
    asset_type: AssetType
    async def fetch_batch(
        self, symbols: Sequence[SymbolRef]
    ) -> FetchBatchResult: ...

# SymbolRef = (symbol: str, exchange: str)
# FetchBatchResult = {successes: list[PriceQuote], failures: list[FetchFailure]}
# PriceQuote = (symbol_ref, price: Decimal, currency: str, fetched_at: datetime UTC)
```

## 9. 심볼 정규화 규칙 (R-3 대응)

상위 PRD 오픈 이슈 — "심볼 정규화" 를 이 슬라이스에서 **결정**:

- **DB 저장 형태** = `AssetSymbol.(asset_type, symbol, exchange)` 유니크 키. 심볼은 **사용자 입력 원형 보존**.
- **adapter 내부 변환** = 각 adapter 가 라이브러리 기대 포맷으로 변환. 공개 API 에는 영향 없음.

| asset_type | exchange 예 | DB `symbol` 예 | adapter 호출 포맷 |
|-----------|-----------|-----------------|--------------------|
| `kr_stock` | `KRX` | `005930` | pykrx: `005930` (그대로), FDR: `005930` (그대로) |
| `us_stock` | `NASDAQ` / `NYSE` | `AAPL`, `VOO` | yfinance: `AAPL` (대문자) |
| `crypto` | `binance` | `BTC/USDT` | ccxt binance: `BTC/USDT` (그대로) |
| `crypto` | `upbit` | `BTC/KRW` *(또는 `KRW-BTC`)* | ccxt upbit: `BTC/KRW` (ccxt 표준화 사용) |

**규칙**:
1. DB 에는 **ccxt 표준 포맷 (`BASE/QUOTE`)** 로 저장. upbit 의 레거시 `KRW-BTC` 가 들어오면 adapter 가 `BTC/KRW` 로 일방 변환.
2. 미국 주식은 **대문자 고정**. lowercase 입력은 adapter 에서 upper() 적용.
3. 한국 주식은 **6자리 숫자 그대로**. 선행 0 누락 금지 (`'005930'` != `'5930'`).

## 10. 비기능 요구사항

| 항목 | 요구 (본 슬라이스) |
|------|--------------------|
| 성능 | 1 사이클 < 5분 @ 500 심볼 (상위 PRD §10 재확인). adapter 병렬화는 `asyncio.gather` 기반 — DB bulk 작성은 단일 트랜잭션. |
| 로깅 | 구조화 JSON — `logger` `app.scheduler.price_refresh`. 이벤트: `start` / `adapter.success` / `adapter.failure` / `done`. 필드 예: `symbol, asset_type, exchange, error_class, elapsed_ms`. PII 금지. |
| 타임존 | 스케줄러: `Asia/Seoul` cron. 저장: **UTC** (DB 는 `DateTime(timezone=True)`). 변환 경계는 job 진입/종료 로그에서만. |
| 격리 | 한 adapter 예외 ↛ 다른 adapter. 한 symbol 실패 ↛ 다른 symbol. 단일 asyncio task 내부에서 `asyncio.gather(..., return_exceptions=True)` 권장. |
| 재시도 | MVP 는 **재시도 없음** — 다음 사이클에서 재시도. 지수 백오프는 v2. |
| 관찰 가능성 | `RefreshResult { total, success, failed, elapsed_ms, failures: list[FailureRow] }` 반환 후 info 로그. 테스트 단언 포인트. |
| 의존성 | `apscheduler`, `yfinance`, `pykrx`, `finance-datareader`, `ccxt` — 이미 `pyproject.toml` 에 선언됨 (확인 완료). 추가 필요 없음. |

## 11. 의존성 / 리스크

### 의존성
- **완료**: `AssetSymbol.last_price`, `last_price_refreshed_at` 컬럼 (portfolio-dashboard 에서 추가됨).
- **확인 필요**: `PricePoint` 모델 — 없으면 이 슬라이스에서 추가.
- **이미 설치**: `apscheduler`, `yfinance`, `pykrx`, `finance-datareader`, `ccxt` (pyproject.toml 확인됨).

### 리스크 (상위 PRD 재확인 + 본 슬라이스 대응)
| # | 리스크 | 본 슬라이스 완화 |
|---|--------|-------------------|
| R-1 | yfinance rate limit / 구조 변경 | `UsStockAdapter` 내 try/except 전면 격리. 실패 시 `last_price` 유지 (DB = SSOT). |
| R-2 | pykrx KRX 사이트 변경 | `KrStockAdapter` 가 pykrx → FDR 순으로 fallback. |
| R-3 | ccxt 거래소별 심볼 불일치 | 9절 정규화 규칙 + adapter 단위 테스트 (`test_normalize_*`). |
| R-4 | 휴장일 / 장외시간 | adapter 가 최근 거래일 종가 반환. `stale` 판정은 대시보드 소관. |
| R-5 | 스케줄러 중복 실행 (다중 워커) | uvicorn `--workers 1` 고정 + README / `docker-compose.yml` 주석으로 고지. 다중 워커는 v2 (Celery/arq + DB lock). |

## 12. 범위 외 (Out of Scope)

- 환율 통합 환산 (v2.0)
- 분산 스케줄러 / leader election (v2)
- 관리자 수동 트리거 엔드포인트
- on-demand 최초 시세 fetch (자산 등록 직후)
- 알림 / 웹훅
- 재시도 백오프 전략

## 13. 오픈 이슈

- [ ] **on-demand 최초 가격 fetch** — 자산 등록 직후 다음 정각까지 `pending` 상태 유지 UX 가 허용 범위인가? 별도 이슈로 기록 후 사용자 피드백 수집 필요.
- [ ] **암호화폐 기본 거래소** — 상위 PRD §12 재확인. 본 슬라이스는 **binance 를 기본, upbit 를 fallback** 으로 고정. 사용자별 설정화는 v1.2.
- [ ] **`holidays` 패키지 도입 여부** — 어댑터 내부 fallback 으로 우선 대응. 갱신 실패율 > 1% 가 3주 연속 관측되면 도입 검토.
- [ ] **PricePoint 보존 기간** — 시계열 누적 시 테이블 성장. 파티셔닝 또는 보존 정책은 v1.2 에서 결정 (초기에는 무제한 누적).

---

## 14. 역할별 책임 (이 슬라이스)

| 역할 | 담당 범위 | 상세 프롬프트 |
|------|-----------|---------------|
| backend | adapter 구현 · 스케줄러 lifespan 통합 · PricePoint migration (필요 시) · Repository / Service · 단위·통합 테스트 · 심볼 정규화 규칙 구현 | [`./price-refresh/backend.md`](./price-refresh/backend.md) |
| frontend | **변경 없음** (N/A) | — |

---

## 참고 문서
- 상위 PRD: `docs/specs/asset-tracking.md` (§6.3, §9, §11 R-1~R-5)
- 포트폴리오 슬라이스 PRD: `docs/specs/portfolio-dashboard.md` (`last_price`, `last_price_refreshed_at` 추가 이력)
- 루트 규칙: `CLAUDE.md`
- backend 규칙: `backend/CLAUDE.md`
- 프로젝트 기록: `memory/MEMORY.md` (hourly price refresh 결정)
