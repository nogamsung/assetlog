"""ISIN → exchange ticker map for US-listed symbols.

Toss Securities statements print the security name + ISIN but never the listing
ticker (AMD, META, …) we need for price refresh APIs (yfinance, etc.). This
table maps known ISINs to their NYSE/NASDAQ ticker. Unknown ISINs fall back to
the ISIN itself.
"""

from __future__ import annotations

US_ISIN_TO_TICKER: dict[str, str] = {
    # Single-name US equities
    "US0079031078": "AMD",
    "US02079K3059": "GOOGL",
    "US08862E1091": "BYND",
    "US30303M1027": "META",
    # Direxion 2x daily bull leveraged single-stock ETFs
    "US25461A5285": "MUU",   # Direxion Daily MU Bull 2X
    "US25461A8099": "METU",  # Direxion Daily META Bull 2X
    "US25461A8412": "GGLL",  # Direxion Daily GOOGL Bull 2X
    "US25461A8743": "AAPU",  # Direxion Daily AAPL Bull 1.5X / 2X
    # GraniteShares leveraged single-stock ETFs
    "US38747R6291": "NVD",   # GraniteShares 2X Short NVDA Daily
    "US38747R7513": "AMDL",  # GraniteShares 2X Long AMD Daily
    # ProShares leveraged ETFs
    "US74347X8314": "TQQQ",  # ProShares UltraPro QQQ
    "US74347Y8883": "UCO",   # ProShares Ultra Bloomberg Crude Oil
}


def lookup_us_ticker(isin: str) -> str | None:
    """Return mapped ticker for a known US ISIN, else None."""
    return US_ISIN_TO_TICKER.get(isin)
