# AssetLog Backend

FastAPI + SQLAlchemy 2.0 (async) + MySQL 8 portfolio tracker API.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for MySQL)

## Local Setup

### 1. Start MySQL with Docker

```bash
# From the repository root
docker compose up -d mysql
```

Wait for the healthcheck to pass (about 30 s):

```bash
docker compose ps
```

### 2. Install dependencies

```bash
cd backend
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if your DB credentials differ
```

### 4. Run database migrations

```bash
uv run alembic upgrade head
# Step 1: no models yet — this is a no-op
```

### 5. Start the development server

```bash
uv run uvicorn app.main:app --reload
```

API docs: <http://localhost:8000/docs>

Health check: <http://localhost:8000/health>

## Running Tests

```bash
uv run pytest --cov
```

Coverage report is written to `coverage.xml`.

## Code Quality

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

## Project Structure

```
app/
├── main.py           # FastAPI app + exception handlers
├── core/             # config, security helpers
├── db/               # async engine, sessionmaker, Base
├── adapters/         # external data sources (price, exchange, file parsers)
│   └── parsers/      # broker statement parsers (Toss Securities, ...)
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic v2 request/response schemas
├── repositories/     # async DB queries
├── services/         # business logic
├── routers/          # APIRouter endpoints
├── tools/            # CLI utilities (parse_preview, ...)
└── exceptions.py     # domain exceptions
alembic/versions/     # Alembic migration revisions
tests/                # pytest-asyncio test suite
```

## External Transaction Import

Two paths for importing transactions from external sources:

### 1. Upbit read-only API (online sync)

```bash
# .env
UPBIT_ACCESS_KEY=...
UPBIT_SECRET_KEY=...
```

```bash
# Manual trigger
curl -X POST http://localhost:8000/api/integrations/upbit/sync \
  -H "Cookie: <session-cookie>"
```

Daily auto-sync runs via `app/scheduler`. Dedupe is by Upbit's order ID — no synthetic key needed.

### 2. Toss Securities PDF (file upload)

Export "거래내역서" PDF from the Toss app, then either upload via the settings UI or via API:

```bash
curl -X POST "http://localhost:8000/api/integrations/import-file?source=toss_securities&dry_run=true" \
  -H "Cookie: <session-cookie>" \
  -F "file=@거래내역서.pdf"
# Optional: -F "password=..."  for encrypted PDFs
```

`dry_run=true` returns counts + up to 20 preview records without writing to the DB. Drop `dry_run` (or set `false`) to persist.

**Dedupe policy**: synthetic `external_id = sha256("{date}|{side}|{symbol}|{qty}|{price}")[:32]` — re-uploading the same statement is safe; rebalances/trades on the same day at the same price are merged.

**CLI preview** (no DB access):

```bash
uv run python -m app.tools.parse_preview \
  --source toss_securities \
  --file ~/Downloads/거래내역서.pdf \
  --format table
```

Supported sources: `toss_securities` (Phase 1). Shinhan / KBank / KakaoBank parsers planned (Phase 2).
