"""SampleSeedService — deterministic portfolio seed for the single owner.

Creates 5 sample assets (BTC, ETH, AAPL, 삼성전자, 현대차) with 2-4 BUY
transactions each, spread across the past 12 months. Uses a fixed seed so
the same data pattern is generated every time.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.asset_type import AssetType
from app.domain.transaction_type import TransactionType
from app.models.asset_symbol import AssetSymbol
from app.repositories.asset_symbol import AssetSymbolRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_asset import UserAssetRepository
from app.schemas.sample_seed import SampleSeedResponse
from app.schemas.transaction import TransactionCreate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SampleSpec:
    """Immutable descriptor for a single seed symbol."""

    asset_type: AssetType
    symbol: str
    exchange: str
    name: str
    currency: str
    base_price: Decimal


# fmt: off
_SAMPLE_SYMBOLS: tuple[_SampleSpec, ...] = (
    _SampleSpec(AssetType.CRYPTO,   "BTC",    "BINANCE", "Bitcoin",    "USD", Decimal("65000.00")),
    _SampleSpec(AssetType.CRYPTO,   "ETH",    "BINANCE", "Ethereum",   "USD", Decimal("3200.00")),
    _SampleSpec(AssetType.US_STOCK, "AAPL",   "NASDAQ",  "Apple Inc.", "USD", Decimal("175.50")),
    _SampleSpec(AssetType.KR_STOCK, "005930", "KRX",     "삼성전자",   "KRW", Decimal("72000.00")),
    _SampleSpec(AssetType.KR_STOCK, "005380", "KRX",     "현대차",     "KRW", Decimal("250000.00")),
)
# fmt: on


class SampleSeedService:
    """Business logic for one-click sample portfolio seeding.

    Idempotent: if the user already has any UserAsset rows the seed is
    skipped and ``SampleSeedResponse(seeded=False, …)`` is returned.
    No FastAPI / HTTP imports — all exceptions are domain-level.
    """

    def __init__(
        self,
        asset_symbol_repo: AssetSymbolRepository,
        user_asset_repo: UserAssetRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self._symbol_repo = asset_symbol_repo
        self._ua_repo = user_asset_repo
        self._tx_repo = transaction_repo

    async def seed(self) -> SampleSeedResponse:
        """Create sample portfolio data for the single owner.

        Returns:
            SampleSeedResponse with counts of created rows, or
            ``seeded=False`` when assets already exist.
        """
        existing = await self._ua_repo.list_all()
        if existing:
            logger.info(
                "sample seed skipped: %s user_assets already exist",
                len(existing),
            )
            return SampleSeedResponse(seeded=False, reason="user_already_has_assets")

        now_utc = datetime.now(tz=UTC)

        # Deterministic RNG — same data pattern every run.
        rng = random.Random(38)  # noqa: S311  # non-security use

        symbols_created = 0
        symbols_reused = 0
        user_assets_created = 0
        transactions_created = 0

        for spec in _SAMPLE_SYMBOLS:
            # 3a. Find-or-create the global AssetSymbol master row.
            asset_symbol: AssetSymbol | None = await self._symbol_repo.get_by_triple(
                asset_type=spec.asset_type,
                symbol=spec.symbol,
                exchange=spec.exchange,
            )

            if asset_symbol is None:
                asset_symbol = await self._symbol_repo.create(
                    asset_type=spec.asset_type,
                    symbol=spec.symbol,
                    exchange=spec.exchange,
                    name=spec.name,
                    currency=spec.currency,
                )
                # Populate last_price immediately so dashboard shows value at once.
                asset_symbol.last_price = spec.base_price
                asset_symbol.last_price_refreshed_at = now_utc
                symbols_created += 1
                logger.debug(
                    "seed: created AssetSymbol symbol=%s exchange=%s",
                    spec.symbol,
                    spec.exchange,
                )
            else:
                symbols_reused += 1
                logger.debug(
                    "seed: reused AssetSymbol id=%s symbol=%s",
                    asset_symbol.id,
                    spec.symbol,
                )

            user_asset = await self._ua_repo.create(asset_symbol_id=asset_symbol.id)
            user_assets_created += 1

            # 3c. Generate 2-4 deterministic BUY transactions per asset.
            n_tx = rng.randint(2, 4)
            for _ in range(n_tx):
                days_ago = rng.randint(30, 360)
                traded_at = now_utc - timedelta(days=days_ago)
                price_factor = Decimal(str(round(1 + rng.uniform(-0.20, 0.20), 6)))
                price = (spec.base_price * price_factor).quantize(Decimal("0.000001"))

                if spec.asset_type == AssetType.CRYPTO:
                    # Fractional quantities for crypto.
                    quantity = Decimal(str(round(rng.uniform(0.1, 10.0), 10)))
                else:
                    quantity = Decimal(rng.randint(1, 50))

                tx_data = TransactionCreate(
                    type=TransactionType.BUY,
                    quantity=quantity,
                    price=price,
                    traded_at=traded_at,
                    memo="sample",
                    tag="seed",
                )
                await self._tx_repo.create(
                    user_asset_id=user_asset.id,
                    data=tx_data,
                )
                transactions_created += 1

        logger.info(
            "sample seed complete: user_assets=%s transactions=%s "
            "symbols_created=%s symbols_reused=%s",
            user_assets_created,
            transactions_created,
            symbols_created,
            symbols_reused,
        )

        return SampleSeedResponse(
            seeded=True,
            user_assets_created=user_assets_created,
            transactions_created=transactions_created,
            symbols_created=symbols_created,
            symbols_reused=symbols_reused,
        )
