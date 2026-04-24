"""Adapter registry — maps AssetType to its PriceAdapter implementation."""

from __future__ import annotations

from app.adapters.base import PriceAdapter
from app.adapters.crypto import CryptoAdapter
from app.adapters.kr_stock import KrStockAdapter
from app.adapters.us_stock import UsStockAdapter
from app.domain.asset_type import AssetType


class AdapterRegistry:
    """Immutable registry mapping AssetType → PriceAdapter instance.

    Instantiated once at lifespan startup and injected via FastAPI Depends.

    Args:
        adapters: Mapping from AssetType to a PriceAdapter implementation.
    """

    def __init__(self, adapters: dict[AssetType, PriceAdapter]) -> None:
        self._adapters = adapters

    def get(self, asset_type: AssetType) -> PriceAdapter:
        """Return the adapter registered for *asset_type*.

        Args:
            asset_type: Target asset category.

        Returns:
            PriceAdapter implementation.

        Raises:
            KeyError: If no adapter is registered for *asset_type*.
        """
        try:
            return self._adapters[asset_type]
        except KeyError:
            raise KeyError(f"No adapter registered for asset_type={asset_type!r}") from None

    def all_types(self) -> list[AssetType]:
        """Return all registered asset types."""
        return list(self._adapters.keys())


def build_default_adapter_registry() -> AdapterRegistry:
    """Create the default production registry with all three adapters.

    Returns:
        AdapterRegistry pre-loaded with KrStock, UsStock, and Crypto adapters.
    """
    return AdapterRegistry(
        {
            AssetType.KR_STOCK: KrStockAdapter(),
            AssetType.US_STOCK: UsStockAdapter(),
            AssetType.CRYPTO: CryptoAdapter(),
        }
    )
