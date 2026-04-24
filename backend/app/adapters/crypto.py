"""Crypto price adapter — ccxt async (Binance primary, Upbit fallback)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from app.adapters._symbol_cache import SymbolListCache  # ADDED
from app.adapters.base import _wrap_failure
from app.adapters.normalize import normalize_crypto_pair
from app.domain.asset_type import AssetType
from app.domain.price_refresh import FetchBatchResult, FetchFailure, PriceQuote, SymbolRef
from app.domain.symbol_search import SymbolCandidate  # ADDED

logger = logging.getLogger("app.adapters.crypto")


def _guess_currency(pair: str) -> str:
    """Extract the quote currency from a ccxt pair string (e.g. BTC/USDT → USDT)."""
    if "/" in pair:
        return pair.split("/", maxsplit=1)[1]
    return "USD"


async def _load_markets_async(exchange_name: str = "binance") -> list[SymbolCandidate]:  # ADDED
    """Load all markets from *exchange_name* and convert to SymbolCandidate list.

    Runs in the event loop (ccxt.async_support is natively async).

    Args:
        exchange_name: ccxt exchange id string.

    Returns:
        List of SymbolCandidate, one per active market.
    """
    import ccxt.async_support as ccxt  # noqa: PLC0415

    exchange_cls = getattr(ccxt, exchange_name)
    exchange = exchange_cls({"enableRateLimit": True})
    candidates: list[SymbolCandidate] = []
    try:
        markets_raw = await exchange.load_markets()
        markets: dict[str, object] = markets_raw if isinstance(markets_raw, dict) else {}
        for symbol, market_info in markets.items():
            if not isinstance(market_info, dict):
                continue
            if not market_info.get("active", True):
                continue
            base: str = str(market_info.get("base") or symbol.split("/")[0])
            quote: str = str(market_info.get("quote") or "USDT")
            name: str = str(market_info.get("baseName") or base)
            candidates.append(
                SymbolCandidate(
                    asset_type=AssetType.CRYPTO,
                    symbol=symbol,
                    name=name,
                    exchange=exchange_name,
                    currency=quote,
                )
            )
    finally:
        await exchange.close()

    logger.debug(
        "crypto market list loaded",
        extra={
            "event": "crypto_market_list_loaded",
            "exchange": exchange_name,
            "count": len(candidates),
        },
    )
    return candidates


class CryptoAdapter:
    """Fetch crypto prices via ccxt async_support.

    Binance is the primary exchange.  If a symbol is not found on Binance
    (or Binance raises), Upbit is tried as fallback.

    Both exchanges are created on first ``fetch_batch`` call and closed
    after each batch to respect rate limits and avoid stale connections.
    ``enableRateLimit=True`` is set on both to respect exchange limits.
    """

    asset_type: AssetType = AssetType.CRYPTO

    def __init__(  # ADDED
        self,
        exchange_name: str = "binance",
        cache: SymbolListCache | None = None,
    ) -> None:
        self._exchange_name = exchange_name
        self._symbol_cache: SymbolListCache = cache if cache is not None else SymbolListCache()

    async def _fetch_from_exchange(
        self,
        exchange_name: str,
        pairs: list[str],
    ) -> dict[str, Decimal]:
        """Fetch ticker prices for *pairs* from a single ccxt exchange.

        Args:
            exchange_name: ccxt exchange id (e.g. "binance", "upbit").
            pairs: List of ccxt-format trading pairs.

        Returns:
            Mapping from pair string to last price.
        """
        import ccxt.async_support as ccxt  # noqa: PLC0415  # lazy import for testability

        exchange_cls = getattr(ccxt, exchange_name)
        exchange = exchange_cls({"enableRateLimit": True})
        prices: dict[str, Decimal] = {}
        try:
            tickers = await exchange.fetch_tickers(pairs)
            for pair, ticker in tickers.items():
                last = ticker.get("last")
                if last is not None:
                    prices[pair] = Decimal(str(last))
        finally:
            await exchange.close()
        return prices

    async def fetch_batch(
        self,
        symbols: Sequence[SymbolRef],
    ) -> FetchBatchResult:
        """Fetch prices for all crypto symbols, with Upbit fallback.

        Each symbol is normalised to ccxt format before querying.
        If Binance cannot resolve a pair, Upbit is tried individually.

        Args:
            symbols: Sequence of SymbolRef with asset_type == CRYPTO.

        Returns:
            FetchBatchResult with successes and per-symbol failures.
        """
        successes: list[PriceQuote] = []
        failures: list[FetchFailure] = []
        fetched_at = datetime.now(tz=UTC)

        if not symbols:
            return FetchBatchResult(successes=successes, failures=failures)

        # Normalise and build lookup structures
        ref_by_pair: dict[str, SymbolRef] = {}
        for ref in symbols:
            norm_pair = normalize_crypto_pair(ref.symbol, ref.exchange)
            ref_by_pair[norm_pair] = ref

        all_pairs = list(ref_by_pair.keys())

        # --- Primary: Binance ---
        binance_prices: dict[str, Decimal] = {}
        try:
            binance_prices = await self._fetch_from_exchange("binance", all_pairs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "binance bulk fetch failed: %s",
                exc,
                extra={"event": "crypto_binance_bulk_fail", "error_class": type(exc).__name__},
            )

        unresolved: list[str] = []
        for pair, ref in ref_by_pair.items():
            if pair in binance_prices:
                price = binance_prices[pair]
                successes.append(
                    PriceQuote(
                        ref=ref,
                        price=price,
                        currency=_guess_currency(pair),
                        fetched_at=fetched_at,
                    )
                )
                logger.debug(
                    "crypto binance fetched",
                    extra={
                        "event": "crypto_fetch_ok",
                        "exchange": "binance",
                        "symbol": pair,
                        "price": str(price),
                    },
                )
            else:
                unresolved.append(pair)

        # --- Fallback: Upbit for unresolved pairs ---
        if unresolved:
            upbit_prices: dict[str, Decimal] = {}
            try:
                upbit_prices = await self._fetch_from_exchange("upbit", unresolved)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "upbit fallback bulk fetch failed: %s",
                    exc,
                    extra={"event": "crypto_upbit_bulk_fail", "error_class": type(exc).__name__},
                )

            for pair in unresolved:
                ref = ref_by_pair[pair]
                if pair in upbit_prices:
                    price = upbit_prices[pair]
                    successes.append(
                        PriceQuote(
                            ref=ref,
                            price=price,
                            currency=_guess_currency(pair),
                            fetched_at=fetched_at,
                        )
                    )
                    logger.debug(
                        "crypto upbit fetched",
                        extra={
                            "event": "crypto_fetch_ok",
                            "exchange": "upbit",
                            "symbol": pair,
                            "price": str(price),
                        },
                    )
                else:
                    exc_missing: Exception = ValueError(
                        f"No price from Binance or Upbit for pair {pair}"
                    )
                    failures.append(_wrap_failure(ref, exc_missing))
                    logger.warning(
                        "crypto no data for %s on any exchange",
                        pair,
                        extra={"event": "crypto_fetch_fail", "symbol": pair},
                    )

        return FetchBatchResult(successes=successes, failures=failures)

    async def search_symbols(self, query: str, limit: int) -> list[SymbolCandidate]:  # ADDED
        """Search crypto trading pairs matching *query*.

        Loads the full market list once (24h TTL), then filters in memory.
        If query contains '/', exact pair match is prioritised.
        Otherwise, BASE prefix matching is used (e.g. 'BTC' -> 'BTC/USDT', ...).

        Args:
            query: User query string (pre-stripped by caller).
            limit: Maximum number of results.

        Returns:
            Up to *limit* SymbolCandidate items.
        """
        exchange_name = self._exchange_name
        norm = normalize_crypto_pair(query, exchange_name)

        async def _loader() -> list[SymbolCandidate]:
            return await _load_markets_async(exchange_name)

        try:
            all_markets = await self._symbol_cache.get_or_load(_loader)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "crypto market list load failed: %s",
                exc,
                extra={"event": "crypto_market_list_fail"},
            )
            return []

        exact: list[SymbolCandidate] = []
        prefix: list[SymbolCandidate] = []

        has_slash = "/" in norm
        base = norm.split("/")[0] if has_slash else norm

        for candidate in all_markets:
            if candidate.symbol == norm:
                exact.append(candidate)
            elif not has_slash and candidate.symbol.startswith(base + "/"):
                prefix.append(candidate)

        merged = exact + prefix
        return merged[:limit]
