"""ISIN → exchange ticker map — DEPRECATED hand-curated table.

Resolution is now driven entirely by ``IsinResolver`` (DB cache + OpenFIGI
fallback). This shim is kept only so the resolver's three-tier interface
still has a "static map" tier that can be re-populated locally for tests
or temporary overrides without re-deploying.

In production the dict is empty — all ISIN→ticker work goes through
OpenFIGI with results cached in the ``isin_ticker_cache`` table.
"""

from __future__ import annotations

US_ISIN_TO_TICKER: dict[str, str] = {}


def lookup_us_ticker(isin: str) -> str | None:
    """Return mapped ticker for a known US ISIN, else None.

    Always returns ``None`` now that the static table is empty. Kept for
    backwards-compatibility with callers that expect the three-tier API.
    """
    return US_ISIN_TO_TICKER.get(isin)
