---
feature: symbol-search
title: 심볼 검색 어댑터 확장 (외부 fallback + upsert)
author: planner-agent
created_at: 2026-04-24
status: Draft
priority: P0
stack_scope: [backend]
owners:
  backend: backend (FastAPI / Python)
parent_prd: docs/specs/asset-tracking.md
related_docs:
  - docs/specs/symbol-search/backend.md
  - docs/api/asset-tracking.yaml
branch: feature/symbol-search
---

# PRD — 심볼 검색 어댑터 확장

| 항목 | 값 |
|------|-----|
| 작성일 | 2026-04-24 |
| 상태 | Draft |
| 스택 범위 | backend (Python/FastAPI) |
| 우선순위 | P0 |
| 상위 PRD | [`asset-tracking.md`](./asset-tracking.md) — US-2/3/4 수락 기준 상속 |

---

## 1. 배경

현재 `GET /api/symbols?q=...` 는 **로컬 `asset_symbols` 테이블 LIKE 검색만** 수행한다. 외부 심볼 마스터를 사전 동기화하는 배치가 없으므로 수동 `POST /api/symbols` 로 등록하지 않은 종목은 자동완성에 표시되지 않는다. 결과적으로 US-2(AAPL→Apple Inc.), US-3(005930→삼성전자), US-4(BTC/USDT) 수락 기준이 **최초 등록 전에는 만족되지 않는다**.

어댑터는 이미 `fetch_batch`(가격 조회)만 구현되어 있으므로, **검색 책임(`search_symbols`)을 동일 어댑터 계층에 확장** 하고 엔드포인트를 "DB 우선 + 부족 시 외부 fallback + upsert" 파이프라인으로 개선한다.

## 2. 목표 (Goals)

- US-2/3/4 수락 기준을 **최초 검색 1회 만에** 만족 (수동 등록 사전 작업 없이)
- `GET /api/symbols` p95 응답 < 1.5초 (외부 fallback 경로 포함, 캐시 hit 시 < 200ms)
- 심볼 리스트 메모리 캐시 hit rate ≥ 90% (TTL 24h 기준)
- 외부 라이브러리 장애 시 기존 DB 결과는 **항상 반환** (외부 실패가 응답 실패로 전파되지 않음)
- 테스트 커버리지 ≥ 80% (pre-push gate)

## 3. 비목표 (Non-goals)

- **On-demand 가격 즉시 fetch** — upsert 후 가격은 비워두고 다음 스케줄 사이클에서 채움 (상위 PRD 오픈 이슈로 이관)
- **전체 심볼 마스터 사전 동기화 배치** — KRX 전 종목/NASDAQ 전 티커 등 대량 프리페치는 v1.1 로 연기
- **검색 랭킹 개선** — 단순 LIKE + 외부 순서 유지. 유사도/인기도 정렬은 후속
- **매도/거래소별 옵션 변경** — 기본 거래소(binance/nasdaq 등) 고정값 유지
- **프론트엔드 UI 대규모 변경** — 기존 `use-assets.ts` 자동완성 훅 재사용. 표시 필드(`name`) 유무 처리 정도만 미세 조정

## 4. 대상 사용자

- **Persona A (상위 PRD)** — 미국 주식·한국 주식·코인 혼합 보유. 검색창에 `AAPL` / `005930` / `BTC/USDT` 입력 시 즉시 후보가 떠야 함.

## 5. 유저 스토리

| # | 스토리 | 수락 기준 |
|---|--------|----------|
| US-S1 | 미국 주식을 `AAPL` 로 검색하면 수동 등록 없이도 `Apple Inc.` 후보가 반환되어야 한다 | 1) `GET /api/symbols?q=AAPL&asset_type=us_stock` 가 `symbol=AAPL, name="Apple Inc."` 를 포함 / 2) 동일 트리플이 `asset_symbols` 에 upsert 되어 `last_synced_at` 갱신 / 3) 2번째 호출 시 외부 API 호출 없이 DB hit 만으로 응답 |
| US-S2 | 한국 주식을 `005930` 또는 `5930` 으로 검색하면 `삼성전자` 가 반환되어야 한다 | 1) 6자리 zero-pad 정규화 후 조회 / 2) `currency=KRW`, `exchange=KRX` 로 upsert / 3) `samsung` / `삼성` 같은 name 부분 매칭도 동작 |
| US-S3 | 암호화폐를 `BTC` 또는 `BTC/USDT` 로 검색하면 후보 리스트가 반환되어야 한다 | 1) `BTC` → `BTC/USDT`, `BTC/BUSD` 등 N개 pair / 2) `exchange=binance` 로 upsert / 3) `BTC/USDT` 정확 입력 시 exact match 우선 |
| US-S4 | `asset_type` 파라미터가 없으면 외부 fallback 은 발동하지 않고 DB만 조회해야 한다 | 1) `GET /api/symbols?q=BTC` 는 DB hit 만 반환 / 2) 외부 라이브러리 호출 0회 (로그로 검증) |
| US-S5 | 외부 라이브러리(예: yfinance)가 예외를 던져도 엔드포인트는 500 이 아닌 DB 결과를 반환해야 한다 | 1) adapter.search_symbols 내 예외 → warning 로그 + 빈 리스트 반환 / 2) DB hits 는 정상 응답에 포함 / 3) 엔드포인트는 200 |
| US-S6 | 빈 쿼리(`q=""` 또는 생략)는 기존 거동대로 DB 전체 목록(페이지네이션) 을 반환해야 한다 | 1) 외부 fallback 발동 안 함 / 2) 기존 `limit`/`offset` 동작 유지 |

## 6. 핵심 플로우

### 행복 경로 — 캐시 hit (US-S1)
```
1. 클라이언트: GET /api/symbols?q=AAPL&asset_type=us_stock&limit=10
2. Router → SymbolService.search(...)
3. Service: AssetSymbolRepository.search() → DB hits (count=H)
4. H >= limit 이면 바로 반환
5. H < limit 이고 q 와 asset_type 이 있으면:
   a. AdapterRegistry.get(asset_type).search_symbols(q, limit=limit - H)
   b. 어댑터 내부 메모리 캐시 확인 (TTL 24h) → hit 시 즉시 필터링 반환
6. 외부 결과를 (asset_type, symbol, exchange) 기준 중복 제거
7. Repository.upsert_many(외부 결과) — last_synced_at = now
8. DB hits + 신규 upsert 결과를 순서 병합하여 반환 (최대 `limit` 개)
```

### 예외 경로
- **외부 라이브러리 예외** — adapter 가 `BLE001`-style 로 포획, `warning` 로그 + 빈 리스트 반환. 엔드포인트는 200 + DB hits.
- **`asset_type` 누락** — 외부 fallback skip. DB 조회 결과만 반환.
- **`q` 빈 값** — 외부 fallback skip (DB 전체 목록 페이지네이션).
- **upsert 충돌** — `(asset_type, symbol, exchange)` unique 이므로 select-then-insert 대신 `INSERT ... ON DUPLICATE KEY UPDATE` 스타일. SQLAlchemy Core `insert().on_duplicate_key_update(...)` (MySQL) / `on_conflict_do_update(...)` (SQLite 테스트).

## 7. 데이터 모델

기존 `AssetSymbol` 스키마 **변경 없음**. 필드 재사용:
- `last_synced_at` — 외부 fallback 결과 upsert 시 갱신 (현재는 가격 스케줄러가 `last_price_refreshed_at` 을 쓰므로 충돌 없음). 해당 컬럼이 없을 경우 Alembic revision 으로 추가 — **오픈 이슈 참고**.

> 확인 완료: `models/asset_symbol.py` 에 `last_synced_at` 컬럼 존재 여부에 따라 Alembic revision 필요 여부가 갈림. backend 프롬프트에서 먼저 확인하도록 지시.

## 8. API 계약

엔드포인트 **경로·쿼리 파라미터 변경 없음**. 응답 스키마(`AssetSymbolResponse`) 변경 없음. 달라지는 것은 **내부 파이프라인**.

```
GET /api/symbols?q=<str>&asset_type=<kr_stock|us_stock|crypto>&exchange=<str>&limit=<int>&offset=<int>
  → 200 OK  list[AssetSymbolResponse]
```

파이프라인 변경 사항 (이 PRD 가 spec 하는 부분):
1. DB hits < limit 이고 `q` 와 `asset_type` 이 모두 있으면 adapter fallback.
2. 외부 결과는 upsert → 차기 호출부터 DB hit.
3. 외부 예외는 graceful degrade.

## 9. 비기능 요구사항

| 항목 | 요구 |
|------|------|
| 성능 (cache hit) | p95 < 200ms |
| 성능 (cache miss, 외부 호출) | p95 < 1.5s (yfinance 단건 info 조회 포함) |
| 캐시 | in-memory, TTL 24h, 재기동 시 초기화 OK |
| 가용성 | 외부 라이브러리 타임아웃 8s 초과 시 실패 처리 + DB fallback |
| 동시성 | 캐시 초기 로드는 `asyncio.Lock` 으로 single-flight 보장 |
| 로깅 | fallback 발동 / 외부 실패 / upsert 건수 구조화 로그 |
| 보안 | 외부 응답을 그대로 echo 금지 — whitelist 필드(`symbol`, `name`, `exchange`, `currency`)만 저장 |
| 테스트 | 외부 라이브러리 전부 모킹 (pykrx / yfinance / ccxt), 캐시 TTL 로직 / fallback 순서 / upsert 동작 검증, 커버리지 ≥ 80% |

## 10. 의존성 / 리스크

**의존성**
- `backend/app/adapters/{base,kr_stock,us_stock,crypto,normalize}.py` — 기존 어댑터 시그니처 확장
- `backend/app/repositories/asset_symbol.py` — upsert 메서드 추가
- `backend/app/services/symbol.py` — fallback 파이프라인 로직
- 외부: pykrx(기존), yfinance(기존), ccxt(기존). 신규 의존성 없음. `finance-datareader` 는 이미 kr_stock fallback 으로 설치됨.

**리스크**
| # | 리스크 | 완화 |
|---|--------|------|
| R-1 | yfinance 자체 `search` API 가 약해 후보 N개 반환 어려움 | exact-match info 조회 + 미매칭 시 빈 결과. 후속에 `Lookup` 또는 FDR `StockListing` 프리패치 도입 |
| R-2 | pykrx 종목 리스트(~2800개) 최초 로딩 지연 | 최초 호출 시 `asyncio.to_thread` + lock + warning 로그. TTL 24h 이후 재로딩. |
| R-3 | ccxt `load_markets()` 네트워크 실패 | 캐시 유지 재시도. 실패 시 빈 결과. |
| R-4 | upsert 동시성 — 같은 심볼 병렬 upsert | DB unique constraint + ON DUPLICATE KEY UPDATE 로 idempotent |
| R-5 | 외부 결과 품질 (예: delisted 티커가 info 에 남음) | MVP 는 외부 결과 그대로 upsert. v1.1 에서 품질 필터 |

## 11. 오픈 이슈

- [ ] **`last_synced_at` 컬럼 존재 여부** — `models/asset_symbol.py` 확인 후, 없으면 Alembic revision 추가 필요 (`backend.md` 1단계에서 확인)
- [ ] **yfinance 후보 N개 확장 전략** — MVP 는 exact-match 만. v1.1 에서 `finance-datareader StockListing('NASDAQ')` 프리페치 캐시 도입 여부 결정
- [ ] **암호화폐 기본 거래소 사용자 설정** — 상위 PRD 오픈 이슈와 동일. MVP 는 `binance` 고정
- [ ] **캐시 무효화 트리거** — 수동 재로딩 엔드포인트(예: `POST /api/symbols/_reload`) 필요 여부. MVP 는 TTL 만으로 충분하다는 가정
- [ ] **응답 순서 보장** — DB hits 먼저 vs relevance 기반 재정렬. MVP 는 DB → 외부 fifo 로 충분

## 12. 성공 지표 (이 슬라이스)

| 지표 | 목표 | 측정 |
|------|------|------|
| 최초 검색 시 후보 반환률 (US-2/3/4 대상 쿼리) | 100% | e2e 테스트 3종 (`AAPL`, `005930`, `BTC/USDT`) |
| 엔드포인트 에러율 (외부 실패 주입 하) | 0% | pytest 예외 주입 시나리오 |
| 2회차 호출 외부 호출 수 | 0 | 캐시 hit 추적 로그 |

---

## 13. 역할별 책임

| 역할 | 담당 | 상세 프롬프트 |
|------|------|---------------|
| backend | 어댑터 확장, 서비스 파이프라인, 리포지토리 upsert, 엔드포인트 파이프라인, 테스트 | [`./symbol-search/backend.md`](./symbol-search/backend.md) |
| frontend | **변경 없음** (표시 로직 미세 조정은 기존 `use-assets.ts` 에서 자연스럽게 흡수) | — |
