"""FX rate adapters — Frankfurter primary, fawazahmed0/currency-api fallback.

Both sources require no API key.  ``ChainedFxAdapter`` composes adapters
in priority order: each adapter is tried until one returns successfully,
otherwise ``FxFetchError`` from the last attempt is propagated.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx

from app.exceptions import FxFetchError

logger = logging.getLogger("app.adapters.fx")

_TIMEOUT_SECONDS = 10.0


class FxRateAdapter(Protocol):
    """Protocol for FX rate sources — async, returns base→quote rate map."""

    async def fetch_rates(
        self, base: str, quotes: list[str]
    ) -> dict[str, Decimal]: ...  # pragma: no cover


class FrankfurterAdapter:
    """Fetch latest exchange rates from https://api.frankfurter.app.

    The Frankfurter API proxies ECB reference rates and requires no API key.
    Rates are updated on ECB business days (Mon–Fri).

    Example response::

        {
          "amount": 1.0,
          "base": "USD",
          "date": "2026-04-24",
          "rates": {"KRW": 1380.25, "EUR": 0.92}
        }
    """

    BASE_URL: str = "https://api.frankfurter.app"

    async def fetch_rates(self, base: str, quotes: list[str]) -> dict[str, Decimal]:
        """Fetch latest rates: 1 *base* = ? *quote* for each quote in *quotes*.

        Args:
            base: Base currency code (e.g. "USD").
            quotes: List of target currency codes (e.g. ["KRW", "EUR"]).

        Returns:
            Mapping of quote_currency → rate (Decimal).

        Raises:
            FxFetchError: On HTTP error, network timeout, or malformed response.
        """
        if not quotes:
            return {}

        url = f"{self.BASE_URL}/latest"
        params = {"from": base, "to": ",".join(quotes)}

        logger.debug(
            "frankfurter fetch_rates start",
            extra={"event": "fx_fetch_start", "base": base, "quotes": quotes},
        )

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error(
                "frankfurter timeout: %s",
                exc,
                extra={"event": "fx_fetch_timeout", "base": base},
            )
            raise FxFetchError(f"Frankfurter API timed out after {_TIMEOUT_SECONDS}s.") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "frankfurter HTTP error %s: %s",
                exc.response.status_code,
                exc,
                extra={"event": "fx_fetch_http_error", "status_code": exc.response.status_code},
            )
            raise FxFetchError(
                f"Frankfurter API returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "frankfurter request error: %s",
                exc,
                extra={"event": "fx_fetch_request_error"},
            )
            raise FxFetchError(f"Frankfurter API request failed: {exc}") from exc

        try:
            payload: dict[str, object] = response.json()
            raw_rates: object = payload.get("rates", {})
            if not isinstance(raw_rates, dict):
                raise FxFetchError("Frankfurter response missing 'rates' dict.")

            rates: dict[str, Decimal] = {}
            for quote, value in raw_rates.items():
                try:
                    rates[str(quote)] = Decimal(str(value))
                except InvalidOperation as exc:
                    raise FxFetchError(
                        f"Frankfurter returned non-numeric rate for {quote}: {value!r}"
                    ) from exc

        except (ValueError, KeyError, TypeError) as exc:
            logger.error(
                "frankfurter response parse error: %s",
                exc,
                extra={"event": "fx_fetch_parse_error"},
            )
            raise FxFetchError(f"Frankfurter response could not be parsed: {exc}") from exc

        logger.debug(
            "frankfurter fetch_rates done",
            extra={"event": "fx_fetch_done", "base": base, "fetched_count": len(rates)},
        )
        return rates


class FawazCurrencyApiAdapter:
    """Fetch latest rates from the fawazahmed0/currency-api dataset.

    The dataset is published to two CDN-backed mirrors (jsDelivr primary,
    Cloudflare Pages mirror) and updated daily.  No API key is required;
    license is CC0-1.0.  Response shape::

        {"date": "YYYY-MM-DD", "usd": {"krw": 1470.31, "eur": 0.92, ...}}

    Keys inside the response are lower-cased ISO codes.  This adapter
    converts them back to upper-case to match :class:`FrankfurterAdapter`.
    """

    PRIMARY_URL: str = (
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json"
    )
    MIRROR_URL: str = "https://latest.currency-api.pages.dev/v1/currencies/{base}.json"

    async def fetch_rates(self, base: str, quotes: list[str]) -> dict[str, Decimal]:
        """Return ``{quote_upper: rate}`` for each quote present in the response.

        Quotes the source does not list are silently omitted (mirrors
        Frankfurter behaviour).  CDN failures fall back to the mirror URL
        before raising :class:`FxFetchError`.
        """
        if not quotes:
            return {}

        base_lower = base.lower()
        urls = [
            self.PRIMARY_URL.format(base=base_lower),
            self.MIRROR_URL.format(base=base_lower),
        ]

        logger.debug(
            "fawaz fetch_rates start",
            extra={"event": "fx_fetch_start", "source": "fawaz", "base": base, "quotes": quotes},
        )

        last_exc: Exception | None = None
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                payload: dict[str, object] = response.json()
            except httpx.TimeoutException as exc:
                logger.warning(
                    "fawaz timeout for %s: %s",
                    url,
                    exc,
                    extra={"event": "fx_fetch_timeout", "source": "fawaz", "url": url},
                )
                last_exc = exc
                continue
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "fawaz HTTP %s for %s",
                    exc.response.status_code,
                    url,
                    extra={
                        "event": "fx_fetch_http_error",
                        "source": "fawaz",
                        "status_code": exc.response.status_code,
                    },
                )
                last_exc = exc
                continue
            except httpx.RequestError as exc:
                logger.warning(
                    "fawaz request error for %s: %s",
                    url,
                    exc,
                    extra={"event": "fx_fetch_request_error", "source": "fawaz", "url": url},
                )
                last_exc = exc
                continue
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "fawaz response parse error for %s: %s",
                    url,
                    exc,
                    extra={"event": "fx_fetch_parse_error", "source": "fawaz", "url": url},
                )
                last_exc = exc
                continue

            raw_rates: object = payload.get(base_lower)
            if not isinstance(raw_rates, dict):
                last_exc = FxFetchError(f"fawazahmed0 response missing '{base_lower}' key")
                continue

            rates: dict[str, Decimal] = {}
            for quote in quotes:
                value = raw_rates.get(quote.lower())
                if value is None:
                    continue
                try:
                    rates[quote.upper()] = Decimal(str(value))
                except InvalidOperation as exc:
                    raise FxFetchError(
                        f"fawazahmed0 returned non-numeric rate for {quote}: {value!r}"
                    ) from exc

            logger.debug(
                "fawaz fetch_rates done",
                extra={
                    "event": "fx_fetch_done",
                    "source": "fawaz",
                    "base": base,
                    "fetched_count": len(rates),
                },
            )
            return rates

        raise FxFetchError(
            f"fawazahmed0/currency-api unavailable on all mirrors: {last_exc}"
        ) from last_exc


class ChainedFxAdapter:
    """Try each underlying adapter in order, returning the first success.

    Only :class:`FxFetchError` is treated as a recoverable failure.  All
    other exceptions are intentionally allowed to propagate so genuine
    bugs are not masked by the chain.
    """

    def __init__(self, adapters: Sequence[FxRateAdapter]) -> None:
        if not adapters:
            raise ValueError("ChainedFxAdapter requires at least one adapter")
        self._adapters: list[FxRateAdapter] = list(adapters)

    async def fetch_rates(self, base: str, quotes: list[str]) -> dict[str, Decimal]:
        last_exc: FxFetchError | None = None
        for idx, adapter in enumerate(self._adapters):
            try:
                rates = await adapter.fetch_rates(base, quotes)
            except FxFetchError as exc:
                logger.warning(
                    "fx adapter #%d (%s) failed: %s",
                    idx,
                    type(adapter).__name__,
                    exc,
                    extra={
                        "event": "fx_chain_attempt_fail",
                        "adapter_index": idx,
                        "adapter": type(adapter).__name__,
                    },
                )
                last_exc = exc
                continue

            if idx > 0:
                logger.info(
                    "fx chain fell back to adapter #%d (%s)",
                    idx,
                    type(adapter).__name__,
                    extra={
                        "event": "fx_chain_fallback_used",
                        "adapter_index": idx,
                        "adapter": type(adapter).__name__,
                    },
                )
            return rates

        assert last_exc is not None  # ChainedFxAdapter requires ≥1 adapter
        raise last_exc
