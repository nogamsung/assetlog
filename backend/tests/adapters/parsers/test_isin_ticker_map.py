"""Static-map shim tests.

The static `US_ISIN_TO_TICKER` table is deliberately empty — all ISIN→ticker
resolution flows through ``IsinResolver`` (DB cache + OpenFIGI). The shim
remains so the resolver's three-tier interface still has a "static" tier
that can be re-populated locally for tests or temporary overrides.
"""

from __future__ import annotations

from app.adapters.parsers import isin_ticker_map
from app.adapters.parsers.isin_ticker_map import lookup_us_ticker


def test_static_map_is_empty_in_production() -> None:
    assert isin_ticker_map.US_ISIN_TO_TICKER == {}


def test_lookup_always_returns_none_when_static_map_empty() -> None:
    for isin in (
        "US0079031078",
        "US30303M1027",
        "KYG651631007",
        "US9999999999",
    ):
        assert lookup_us_ticker(isin) is None


def test_lookup_respects_runtime_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """If a test or temporary override populates the map, lookup should hit it."""
    monkeypatch.setitem(isin_ticker_map.US_ISIN_TO_TICKER, "US0079031078", "AMD")
    assert lookup_us_ticker("US0079031078") == "AMD"
