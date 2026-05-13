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
    "US0378331005": "AAPL",
    "US08862E1091": "BYND",
    "US25400Q1058": "DJT",   # Trump Media & Technology Group
    "US30303M1027": "META",
    "US69608A1088": "PLTR",  # Palantir Technologies
    # Cayman / non-US-domiciled but US-listed
    "KYG651631007": "JOBY",  # Joby Aviation
    # Direxion 2x daily leveraged single-stock ETFs
    "US25461A4452": "PLTU",  # Direxion Daily PLTR Bull 2X
    "US25461A5285": "MUU",   # Direxion Daily MU Bull 2X
    "US25461A8099": "METU",  # Direxion Daily META Bull 2X
    "US25461A8412": "GGLL",  # Direxion Daily GOOGL Bull 2X
    "US25461A8743": "AAPU",  # Direxion Daily AAPL Bull 1.5X / 2X
    "US25461H8126": "LINT",  # Direxion Daily INTC Bull 2X
    # GraniteShares leveraged single-stock ETFs
    "US38747R6291": "NVD",   # GraniteShares 2X Short NVDA Daily
    "US38747R7513": "AMDL",  # GraniteShares 2X Long AMD Daily
    # ProShares leveraged ETFs
    "US74347X8314": "TQQQ",  # ProShares UltraPro QQQ
    "US74347Y8883": "UCO",   # ProShares Ultra Bloomberg Crude Oil
    # T-REX 2x daily leveraged single-stock ETFs (Tuttle / REX Shares)
    "US26923Q5642": "BMNU",  # T-REX 2X Long BMNR Daily Target ETF
    # Tradr 2x daily ETFs (formerly AXS)
    "US46092D3843": "TSLQ",  # Tradr 2X Short TSLA Daily
    "US46152A4866": "JOBX",  # Tradr 2X Long JOBY Daily
    # Defiance Daily Target 2X Short ETFs
    "US88636W2474": "IONZ",  # Defiance Daily Target 2X Short IONQ
    "US88636W2540": "PLTZ",  # Defiance Daily Target 2X Short PLTR
    "US88636W5519": "BMNZ",  # Defiance Daily Target 2X Short BMNR
}


def lookup_us_ticker(isin: str) -> str | None:
    """Return mapped ticker for a known US ISIN, else None."""
    return US_ISIN_TO_TICKER.get(isin)
