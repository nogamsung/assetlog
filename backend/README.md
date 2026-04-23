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
├── models/           # SQLAlchemy ORM models (Step 2+)
├── schemas/          # Pydantic v2 request/response schemas (Step 2+)
├── repositories/     # async DB queries (Step 2+)
├── services/         # business logic (Step 2+)
├── routers/          # APIRouter endpoints (Step 3+)
└── exceptions.py     # domain exceptions
alembic/versions/     # Alembic migration revisions
tests/                # pytest-asyncio test suite
```
