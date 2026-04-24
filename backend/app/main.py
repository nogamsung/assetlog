import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,  # noqa: F401  # apscheduler has no stubs
)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters import build_default_adapter_registry
from app.core.config import settings
from app.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.routers.auth import router as auth_router
from app.routers.portfolio import router as portfolio_router
from app.routers.symbol import router as symbol_router
from app.routers.transaction import router as transaction_router
from app.routers.user_asset import router as user_asset_router
from app.scheduler import build_scheduler

logger = logging.getLogger(__name__)


def _make_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker for the given database URL."""
    eng = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    return async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — DB connectivity check + scheduler startup."""
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

    scheduler: AsyncIOScheduler | None = None
    if settings.enable_scheduler:
        adapters = build_default_adapter_registry()
        scheduler = build_scheduler(session_factory, adapters)
        scheduler.start()
        logger.info(
            "price_refresh scheduler started (Asia/Seoul, every hour :00)",
            extra={"event": "scheduler_start"},
        )

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
            logger.info(
                "price_refresh scheduler stopped",
                extra={"event": "scheduler_stop"},
            )
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


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Map NotFoundError → 404."""
    logger.debug("NotFoundError: %s", exc.detail)
    return JSONResponse(status_code=404, content={"detail": exc.detail})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Map ConflictError → 409."""
    logger.debug("ConflictError: %s", exc.detail)
    return JSONResponse(status_code=409, content={"detail": exc.detail})


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Map UnauthorizedError → 401."""
    logger.debug("UnauthorizedError: %s", exc.detail)
    return JSONResponse(status_code=401, content={"detail": exc.detail})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Map ValidationError → 422."""
    logger.debug("ValidationError: %s", exc.detail)
    return JSONResponse(status_code=422, content={"detail": exc.detail})


app.include_router(auth_router)
app.include_router(symbol_router)
app.include_router(user_asset_router)
app.include_router(transaction_router)
app.include_router(portfolio_router)


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
