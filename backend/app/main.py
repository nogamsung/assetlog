import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,  # noqa: F401  # apscheduler has no stubs
)
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware  # ADDED

from app.adapters import build_default_adapter_registry
from app.core.config import settings
from app.exceptions import (
    AppError,
    ConflictError,
    CsvImportValidationError,
    FxRateNotAvailableError,
    InsufficientHoldingError,  # ADDED
    NotFoundError,
    OwnerPasswordNotConfiguredError,  # ADDED
    TooManyAttemptsError,  # ADDED
    UnauthorizedError,
    ValidationError,
)
from app.routers.auth import router as auth_router
from app.routers.bulk_transaction import router as bulk_transaction_router
from app.routers.export import router as export_router
from app.routers.fx import router as fx_router
from app.routers.portfolio import router as portfolio_router
from app.routers.sample import router as sample_router
from app.routers.symbol import router as symbol_router
from app.routers.transaction import router as transaction_router
from app.routers.user_asset import router as user_asset_router
from app.scheduler import build_scheduler

logger = logging.getLogger(__name__)


def _make_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker for the given database URL."""
    eng = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    return async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)


def _validate_password_hash_cost(hash_str: str) -> None:
    """Warn if the bcrypt cost factor stored in APP_PASSWORD_HASH is below 12.

    bcrypt hash format: ``$2b$<cost>$<22-char salt><31-char hash>``
    """
    if not hash_str:
        return
    try:
        parts = hash_str.split("$")
        cost = int(parts[2])
        if cost < 12:
            logger.warning(
                "APP_PASSWORD_HASH cost factor is %d (recommended >= 12). "
                "Rebuild with bcrypt.gensalt(rounds=12) or higher.",
                cost,
            )
    except (IndexError, ValueError):
        logger.warning("APP_PASSWORD_HASH format unexpected — verify it's a valid bcrypt hash.")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — DB connectivity check + scheduler startup."""
    logger.info("Starting up AssetLog API...")
    if settings.app_password_hash:
        _validate_password_hash_cost(settings.app_password_hash)
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
        scheduler = build_scheduler(  # MODIFIED — pass retention_days
            session_factory,
            adapters,
            login_attempt_retention_days=settings.login_attempt_retention_days,
        )
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):  # ADDED
    """Inject security headers on every response.

    HSTS is only added when ``cookie_secure=True`` (i.e., HTTPS environments)
    to avoid breaking HTTP-only local development setups.
    CSP is excluded from this PR — to be aligned with frontend in a follow-up.
    """

    async def dispatch(  # ADDED
        self,
        request: Request,
        call_next: object,
    ) -> Response:
        """Forward the request and attach security headers to the response."""
        from collections.abc import Callable as _Callable  # noqa: PLC0415

        _call: _Callable[..., object] = call_next  # type: ignore[assignment]
        response: Response = await _call(request)  # type: ignore[misc]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)  # ADDED


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


@app.exception_handler(InsufficientHoldingError)  # ADDED
async def insufficient_holding_handler(
    request: Request, exc: InsufficientHoldingError
) -> JSONResponse:
    """Map InsufficientHoldingError → 409."""
    logger.debug("InsufficientHoldingError: %s", exc.detail)
    return JSONResponse(status_code=409, content={"detail": exc.detail})


@app.exception_handler(CsvImportValidationError)
async def csv_import_validation_handler(
    request: Request, exc: CsvImportValidationError
) -> JSONResponse:
    """Map CsvImportValidationError → 422 with per-row error details."""
    logger.debug("CsvImportValidationError: %s errors", len(exc.errors))
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "errors": exc.errors},
    )


@app.exception_handler(FxRateNotAvailableError)
async def fx_rate_not_available_handler(
    request: Request, exc: FxRateNotAvailableError
) -> JSONResponse:
    """Map FxRateNotAvailableError → 503 Service Unavailable (temporary)."""
    logger.debug("FxRateNotAvailableError: %s", exc.detail)
    return JSONResponse(status_code=503, content={"detail": exc.detail})


@app.exception_handler(TooManyAttemptsError)  # ADDED
async def too_many_attempts_handler(request: Request, exc: TooManyAttemptsError) -> JSONResponse:
    """Map TooManyAttemptsError → 429 with Retry-After header."""
    logger.debug("TooManyAttemptsError: retry_after=%s", exc.retry_after_seconds)
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@app.exception_handler(OwnerPasswordNotConfiguredError)  # ADDED
async def owner_password_not_configured_handler(
    request: Request, exc: OwnerPasswordNotConfiguredError
) -> JSONResponse:
    """Map OwnerPasswordNotConfiguredError → 503."""
    logger.error("APP_PASSWORD_HASH is not configured")
    return JSONResponse(
        status_code=503,
        content={"detail": "Owner password not configured"},
    )


app.include_router(auth_router)
app.include_router(symbol_router)
app.include_router(user_asset_router)
app.include_router(transaction_router)
app.include_router(bulk_transaction_router)
app.include_router(portfolio_router)
app.include_router(fx_router)
app.include_router(sample_router)
app.include_router(export_router)


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
