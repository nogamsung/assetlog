"""Symbol router — AssetSymbol master table search and registration."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, SymbolServiceDep
from app.domain.asset_type import AssetType
from app.schemas.asset import AssetSymbolCreate, AssetSymbolResponse
from app.schemas.auth import ErrorResponse

router = APIRouter(prefix="/api/symbols", tags=["symbols"])


@router.get(
    "",
    response_model=list[AssetSymbolResponse],
    status_code=status.HTTP_200_OK,
    summary="Search asset symbols",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def search_symbols(
    _current_user: CurrentUser,
    symbol_service: SymbolServiceDep,
    q: str | None = Query(
        default=None,
        max_length=100,
        description="Partial text search on symbol or name",
        examples=["BTC"],
    ),
    asset_type: AssetType | None = Query(
        default=None,
        description="Filter by asset category",
    ),
    exchange: str | None = Query(
        default=None,
        max_length=50,
        description="Filter by exchange identifier",
        examples=["upbit"],
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> list[AssetSymbolResponse]:
    """Search the asset symbol master table.

    Requires authentication. Results are filtered by optional text query,
    asset type, and exchange.
    """
    symbols = await symbol_service.search(
        q=q,
        asset_type=asset_type,
        exchange=exchange,
        limit=limit,
        offset=offset,
    )
    return [AssetSymbolResponse.model_validate(s) for s in symbols]


@router.post(
    "",
    response_model=AssetSymbolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new asset symbol",
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        409: {"model": ErrorResponse, "description": "Symbol already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register_symbol(
    data: AssetSymbolCreate,
    _current_user: CurrentUser,
    symbol_service: SymbolServiceDep,
) -> AssetSymbolResponse:
    """Register a new entry in the asset symbol master table.

    Requires authentication. Returns 409 if the
    (asset_type, symbol, exchange) triple already exists.
    """
    asset = await symbol_service.register(data)
    return AssetSymbolResponse.model_validate(asset)
