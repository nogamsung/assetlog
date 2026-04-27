"""FastAPI dependency providers — DI wiring for repositories, services, and auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import AdapterRegistry, build_default_adapter_registry
from app.adapters.base import SymbolSearchAdapter
from app.core.config import settings
from app.core.principal import OwnerPrincipal
from app.db.base import get_db_session
from app.domain.asset_type import AssetType
from app.exceptions import UnauthorizedError
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.cash_account import CashAccountRepository
from app.repositories.fx_rate import FxRateRepository
from app.repositories.login_attempt import LoginAttemptRepository
from app.repositories.portfolio import PortfolioRepository
from app.repositories.portfolio_history import PortfolioHistoryRepository
from app.repositories.price_point import PricePointRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.services.auth import AuthService
from app.services.bulk_transaction import BulkTransactionService
from app.services.cash_account import CashAccountService
from app.services.data_export import DataExportService
from app.services.fx_rate import FxRateService
from app.services.login_rate_limiter import LoginRateLimiter
from app.services.portfolio import PortfolioService
from app.services.portfolio_history import PortfolioHistoryService
from app.services.price_refresh import PriceRefreshService
from app.services.sample_seed import SampleSeedService
from app.services.symbol import SymbolService
from app.services.tag_breakdown import TagBreakdownService
from app.services.transaction import TransactionService
from app.services.user_asset import UserAssetService

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# ---------------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------------


def get_asset_symbol_repository(session: DbSession) -> AssetSymbolRepository:
    """Inject an AssetSymbolRepository bound to the current request session."""
    return AssetSymbolRepository(session)


AssetSymbolRepositoryDep = Annotated[AssetSymbolRepository, Depends(get_asset_symbol_repository)]


def get_user_asset_repository(session: DbSession) -> UserAssetRepository:
    """Inject a UserAssetRepository bound to the current request session."""
    return UserAssetRepository(session)


UserAssetRepositoryDep = Annotated[UserAssetRepository, Depends(get_user_asset_repository)]

# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------


def get_login_attempt_repository(session: DbSession) -> LoginAttemptRepository:
    """Inject a LoginAttemptRepository bound to the current request session."""
    return LoginAttemptRepository(session)


LoginAttemptRepositoryDep = Annotated[LoginAttemptRepository, Depends(get_login_attempt_repository)]


def get_login_rate_limiter(
    repo: LoginAttemptRepositoryDep,
) -> LoginRateLimiter:
    """Return a DB-backed LoginRateLimiter configured from settings."""
    return LoginRateLimiter(
        repo=repo,
        per_ip_max=settings.login_max_attempts,
        global_max=settings.login_global_max_attempts,
        per_ip_window_seconds=settings.login_lockout_seconds,
        global_window_seconds=settings.login_global_window_seconds,
    )


LoginRateLimiterDep = Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)]


def get_auth_service(rate_limiter: LoginRateLimiterDep) -> AuthService:
    """Inject an AuthService with LoginRateLimiter."""
    return AuthService(rate_limiter=rate_limiter, settings=settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_symbol_service(
    repo: AssetSymbolRepositoryDep,
    adapter_registry: AdapterRegistryDep,
) -> SymbolService:
    """Inject a SymbolService bound to the current request session and adapter registry."""
    search_adapters: dict[AssetType, SymbolSearchAdapter] = {}
    for at in adapter_registry.all_types():
        adapter = adapter_registry.get(at)
        if isinstance(adapter, SymbolSearchAdapter):
            search_adapters[at] = adapter
    return SymbolService(repo, adapters=search_adapters)


SymbolServiceDep = Annotated[SymbolService, Depends(get_symbol_service)]


def get_user_asset_service(repo: UserAssetRepositoryDep) -> UserAssetService:
    """Inject a UserAssetService bound to the current request session."""
    return UserAssetService(repo)


UserAssetServiceDep = Annotated[UserAssetService, Depends(get_user_asset_service)]


def get_transaction_repository(session: DbSession) -> TransactionRepository:
    """Inject a TransactionRepository bound to the current request session."""
    return TransactionRepository(session)


TransactionRepositoryDep = Annotated[TransactionRepository, Depends(get_transaction_repository)]


def get_transaction_service(
    tx_repo: TransactionRepositoryDep,
    ua_repo: UserAssetRepositoryDep,
) -> TransactionService:
    """Inject a TransactionService bound to the current request session."""
    return TransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]


def get_bulk_transaction_service(
    tx_repo: TransactionRepositoryDep,
    ua_repo: UserAssetRepositoryDep,
) -> BulkTransactionService:
    """Inject a BulkTransactionService bound to the current request session."""
    return BulkTransactionService(transaction_repo=tx_repo, user_asset_repo=ua_repo)


BulkTransactionServiceDep = Annotated[BulkTransactionService, Depends(get_bulk_transaction_service)]


def get_portfolio_repository(session: DbSession) -> PortfolioRepository:
    """Inject a PortfolioRepository bound to the current request session."""
    return PortfolioRepository(session)


PortfolioRepositoryDep = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]


def get_fx_rate_repository(session: DbSession) -> FxRateRepository:
    """Inject a FxRateRepository bound to the current request session."""
    return FxRateRepository(session)


FxRateRepositoryDep = Annotated[FxRateRepository, Depends(get_fx_rate_repository)]


def get_fx_rate_service(repo: FxRateRepositoryDep) -> FxRateService:
    """Inject a FxRateService bound to the current request session."""
    from app.adapters.fx import (  # noqa: PLC0415  # lazy to avoid circular import
        ChainedFxAdapter,
        FawazCurrencyApiAdapter,
        FrankfurterAdapter,
    )

    adapter = ChainedFxAdapter([FrankfurterAdapter(), FawazCurrencyApiAdapter()])
    return FxRateService(repo=repo, adapter=adapter)


FxRateServiceDep = Annotated[FxRateService, Depends(get_fx_rate_service)]


def get_cash_account_repository(session: DbSession) -> CashAccountRepository:
    """Inject a CashAccountRepository bound to the current request session."""
    return CashAccountRepository(session)


CashAccountRepositoryDep = Annotated[CashAccountRepository, Depends(get_cash_account_repository)]


async def get_cash_account_service(
    session: DbSession,
) -> CashAccountService:
    """Inject a CashAccountService bound to the current request session."""
    return CashAccountService(CashAccountRepository(session))


CashAccountServiceDep = Annotated[CashAccountService, Depends(get_cash_account_service)]


def get_portfolio_service(
    repo: PortfolioRepositoryDep,
    fx_service: FxRateServiceDep,
    cash_repo: CashAccountRepositoryDep,
) -> PortfolioService:
    """Inject a PortfolioService with FxRateService and CashAccountRepository."""
    return PortfolioService(repo, fx_service=fx_service, cash_repository=cash_repo)


PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]


def get_portfolio_history_repository(session: DbSession) -> PortfolioHistoryRepository:
    """Inject a PortfolioHistoryRepository bound to the current request session."""
    return PortfolioHistoryRepository(session)


PortfolioHistoryRepositoryDep = Annotated[
    PortfolioHistoryRepository, Depends(get_portfolio_history_repository)
]


def get_portfolio_history_service(
    repo: PortfolioHistoryRepositoryDep,
) -> PortfolioHistoryService:
    """Inject a PortfolioHistoryService bound to the current request session."""
    return PortfolioHistoryService(repo)


PortfolioHistoryServiceDep = Annotated[
    PortfolioHistoryService, Depends(get_portfolio_history_service)
]

# ---------------------------------------------------------------------------
# Price refresh DI
# ---------------------------------------------------------------------------

_default_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    """Return a singleton AdapterRegistry for use outside the lifespan context.

    In production the lifespan creates the registry; this factory is provided
    as a fallback for test overrides via ``app.dependency_overrides``.
    """
    global _default_adapter_registry  # noqa: PLW0603  # intentional module-level singleton
    if _default_adapter_registry is None:
        _default_adapter_registry = build_default_adapter_registry()
    return _default_adapter_registry


AdapterRegistryDep = Annotated[AdapterRegistry, Depends(get_adapter_registry)]


def get_price_point_repository(session: DbSession) -> PricePointRepository:
    """Inject a PricePointRepository bound to the current request session."""
    return PricePointRepository(session)


PricePointRepositoryDep = Annotated[PricePointRepository, Depends(get_price_point_repository)]


def get_price_refresh_service(
    asset_symbol_repo: AssetSymbolRepositoryDep,
    price_point_repo: PricePointRepositoryDep,
    adapters: AdapterRegistryDep,
) -> PriceRefreshService:
    """Inject a PriceRefreshService wired to current-request repositories."""
    return PriceRefreshService(
        asset_symbol_repo=asset_symbol_repo,
        price_point_repo=price_point_repo,
        adapters=adapters,
    )


PriceRefreshServiceDep = Annotated[PriceRefreshService, Depends(get_price_refresh_service)]

# ---------------------------------------------------------------------------
# Tag breakdown DI
# ---------------------------------------------------------------------------


def get_tag_breakdown_service(
    portfolio_repo: PortfolioRepositoryDep,
) -> TagBreakdownService:
    """Inject a TagBreakdownService bound to the current request session."""
    return TagBreakdownService(repo=portfolio_repo)


TagBreakdownServiceDep = Annotated[TagBreakdownService, Depends(get_tag_breakdown_service)]

# ---------------------------------------------------------------------------
# Sample seed DI
# ---------------------------------------------------------------------------


def get_sample_seed_service(
    asset_symbol_repo: AssetSymbolRepositoryDep,
    user_asset_repo: UserAssetRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> SampleSeedService:
    """Inject a SampleSeedService wired to the current-request repositories."""
    return SampleSeedService(
        asset_symbol_repo=asset_symbol_repo,
        user_asset_repo=user_asset_repo,
        transaction_repo=transaction_repo,
    )


SampleSeedServiceDep = Annotated[SampleSeedService, Depends(get_sample_seed_service)]

# ---------------------------------------------------------------------------
# Data export DI
# ---------------------------------------------------------------------------


def get_data_export_service(
    user_asset_repo: UserAssetRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> DataExportService:
    """Inject a DataExportService wired to the current-request repositories."""
    return DataExportService(
        user_asset_repo=user_asset_repo,
        transaction_repo=transaction_repo,
    )


DataExportServiceDep = Annotated[DataExportService, Depends(get_data_export_service)]

# ---------------------------------------------------------------------------
# Current-user guard
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    auth_service: AuthServiceDep,
) -> OwnerPrincipal:
    """Resolve the owner principal from cookie or Bearer header.

    Priority:
    1. ``access_token`` httpOnly cookie
    2. ``Authorization: Bearer <token>`` header

    Raises:
        UnauthorizedError: If no token is present or the token is invalid.
    """
    token: str | None = request.cookies.get("access_token")

    if token is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]

    if token is None:
        raise UnauthorizedError("No authentication token provided.")

    return await auth_service.get_principal_from_token(token)


CurrentUser = Annotated[OwnerPrincipal, Depends(get_current_user)]
