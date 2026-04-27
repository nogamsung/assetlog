"""FxRateService — fetch, persist, and convert exchange rates."""

from __future__ import annotations

import itertools
import logging
from datetime import UTC, datetime
from decimal import Decimal

from app.adapters.fx import FxRateAdapter
from app.exceptions import FxRateNotAvailableError
from app.models.fx_rate import FxRate
from app.repositories.fx_rate import FxRateRepository

logger = logging.getLogger("app.services.fx_rate")

# Fixed set of currencies we always want to keep up to date.
# Covers KRW (crypto / KR stock), USD (US stock), EUR (European assets).
_SUPPORTED_CURRENCIES: list[str] = ["USD", "KRW", "EUR"]


class FxRateService:
    """Business logic for exchange rate management.

    Responsibilities:
    - Refresh all needed rate pairs via the injected FX adapter chain.
    - Persist rates using the FxRateRepository (upsert).
    - Convert monetary amounts between currencies using cached rates.

    Dependencies are injected — no module-level state.
    """

    def __init__(
        self,
        repo: FxRateRepository,
        adapter: FxRateAdapter,
    ) -> None:
        self._repo = repo
        self._adapter = adapter

    async def refresh_all(self) -> int:
        """Fetch all N×(N-1) rate pairs for supported currencies and persist them.

        For each currency treated as the base, we fetch rates for all other
        currencies in one API call (the adapter chain supports multi-quote).

        Returns:
            Total number of rate pairs successfully upserted.
        """
        currencies = _SUPPORTED_CURRENCIES
        fetched_at = datetime.now(tz=UTC)
        total_upserted = 0

        for base in currencies:
            quotes = [c for c in currencies if c != base]
            if not quotes:
                continue

            try:
                rates = await self._adapter.fetch_rates(base, quotes)
            except Exception as exc:  # noqa: BLE001
                # Log and continue — partial failure is acceptable.
                logger.error(
                    "fx_rate fetch failed for base=%s: %s",
                    base,
                    exc,
                    extra={"event": "fx_refresh_fetch_fail", "base": base, "error": str(exc)},
                )
                continue

            for quote, rate in rates.items():
                try:
                    await self._repo.upsert(base, quote, rate, fetched_at)
                    total_upserted += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "fx_rate upsert failed base=%s quote=%s: %s",
                        base,
                        quote,
                        exc,
                        extra={
                            "event": "fx_refresh_upsert_fail",
                            "base": base,
                            "quote": quote,
                            "error": str(exc),
                        },
                    )

        logger.info(
            "fx_rate refresh_all done: %d pairs upserted",
            total_upserted,
            extra={"event": "fx_refresh_done", "upserted": total_upserted},
        )
        return total_upserted

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Convert *amount* from *from_currency* to *to_currency*.

        Uses the latest cached rate from the repository.  No external API call
        is made — the scheduler must have run at least once for rates to exist.

        Args:
            amount: Monetary amount to convert.
            from_currency: Source currency code (e.g. "USD").
            to_currency: Target currency code (e.g. "KRW").

        Returns:
            Converted amount as Decimal.

        Raises:
            FxRateNotAvailableError: If no cached rate exists for the pair.
        """
        if from_currency == to_currency:
            return amount

        rate_row = await self._repo.get_latest(from_currency, to_currency)
        if rate_row is None:
            raise FxRateNotAvailableError(
                f"No cached rate for {from_currency}/{to_currency}. "
                "Retry after the hourly fx_refresh job runs."
            )

        return amount * rate_row.rate

    async def get_all_rates_for_conversion(
        self,
        from_currencies: list[str],
        to_currency: str,
    ) -> dict[str, Decimal] | None:
        """Return a mapping of {from_currency: rate_to_to_currency} for all given currencies.

        Returns None if ANY of the required rates is missing (partial conversion
        is disallowed to prevent misleading totals).

        Args:
            from_currencies: List of source currency codes.
            to_currency: Single target currency code.

        Returns:
            Dict mapping each from_currency to its conversion rate, or None if
            any rate is unavailable.
        """
        rates: dict[str, Decimal] = {}
        for currency in from_currencies:
            if currency == to_currency:
                rates[currency] = Decimal("1")
                continue
            rate_row = await self._repo.get_latest(currency, to_currency)
            if rate_row is None:
                logger.debug(
                    "fx_rate missing for conversion: %s → %s",
                    currency,
                    to_currency,
                    extra={
                        "event": "fx_rate_missing",
                        "from": currency,
                        "to": to_currency,
                    },
                )
                return None  # partial conversion forbidden
            rates[currency] = rate_row.rate
        return rates

    async def list_all_rates(self) -> list[FxRate]:
        """Return all cached FX rate rows for display purposes.

        Returns:
            List of FxRate ORM rows — empty if no rates have been fetched yet.
        """
        return await self._repo.list_all()

    def _all_currency_pairs(self, currencies: list[str]) -> list[tuple[str, str]]:
        """Return all ordered pairs (base, quote) from a list of currency codes."""
        return list(itertools.permutations(currencies, 2))
