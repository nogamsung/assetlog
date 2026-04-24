"""FX rate adapter — Frankfurter (ECB reference rates, no API key required)."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

import httpx

from app.exceptions import FxFetchError

logger = logging.getLogger("app.adapters.fx")

_TIMEOUT_SECONDS = 10.0


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
