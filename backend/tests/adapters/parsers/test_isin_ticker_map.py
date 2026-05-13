"""Unit tests for the ISIN→ticker mapping table.

The fixture-based parser test only covers ISINs present in the bundled sample.
This file directly asserts that real-world ISINs encountered in historical
Toss statements (2022–2026) all resolve to a proper exchange ticker.
"""

from __future__ import annotations

import pytest

from app.adapters.parsers.isin_ticker_map import lookup_us_ticker


@pytest.mark.parametrize(
    ("isin", "ticker"),
    [
        # Single-name US equities
        ("US0079031078", "AMD"),
        ("US02079K3059", "GOOGL"),
        ("US0378331005", "AAPL"),
        ("US08862E1091", "BYND"),
        ("US25400Q1058", "DJT"),
        ("US30303M1027", "META"),
        ("US69608A1088", "PLTR"),
        # Cayman-domiciled US-listed
        ("KYG651631007", "JOBY"),
        # Direxion 2X leveraged single-stock ETFs
        ("US25461A4452", "PLTU"),
        ("US25461A5285", "MUU"),
        ("US25461A8099", "METU"),
        ("US25461A8412", "GGLL"),
        ("US25461A8743", "AAPU"),
        ("US25461H8126", "LINT"),
        # GraniteShares leveraged ETFs
        ("US38747R6291", "NVD"),
        ("US38747R7513", "AMDL"),
        # ProShares leveraged ETFs
        ("US74347X8314", "TQQQ"),
        ("US74347Y8883", "UCO"),
        # T-REX & Tradr & Defiance
        ("US26923Q5642", "BMNU"),
        ("US46092D3843", "TSLQ"),
        ("US46152A4866", "JOBX"),
        ("US88636W2474", "IONZ"),
        ("US88636W2540", "PLTZ"),
        ("US88636W5519", "BMNZ"),
    ],
)
def test_known_isin_maps_to_ticker(isin: str, ticker: str) -> None:
    assert lookup_us_ticker(isin) == ticker


def test_unknown_isin_returns_none() -> None:
    assert lookup_us_ticker("US0000000000") is None
