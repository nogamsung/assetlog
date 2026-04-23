import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.exceptions import AppError

logger = logging.getLogger(__name__)


def _make_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker for the given database URL."""
    eng = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    return async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — lightweight DB connectivity check on startup."""
    logger.info("Starting up AssetLog API...")
    # Use the configured database_url at startup time.
    session_factory = _make_session_factory(settings.database_url)
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as exc:  # noqa: BLE001
        # Log the error but do NOT crash — allows the app to start even when
        # the DB is temporarily unavailable (e.g., during container cold start).
        logger.warning("Database health check failed at startup: %s", exc)
    yield
    logger.info("Shutting down AssetLog API.")


app = FastAPI(
    title="AssetLog API",
    version="0.1.0",
    description="Portfolio asset tracker with hourly price refresh.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert domain exceptions to HTTP responses."""
    logger.debug("Domain exception %s: %s", type(exc).__name__, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get(
    "/health",
    summary="Health check",
    tags=["health"],
    responses={200: {"description": "Service is healthy"}},
)
async def health() -> dict[str, str]:
    """Ping the database and return service status."""
    from app.db.base import AsyncSessionLocal  # imported here to allow DI override

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
