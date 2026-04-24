"""Symbol normalisation utilities — pure functions, no I/O.

Each adapter calls the appropriate normaliser before passing symbols to
the external library.  All rules are derived from PRD §9.
"""

from __future__ import annotations


def normalize_kr_stock_symbol(raw: str) -> str:
    """Return a 6-digit zero-padded KRX ticker.

    Examples::

        normalize_kr_stock_symbol("5930")   -> "005930"
        normalize_kr_stock_symbol(" 005930 ") -> "005930"
        normalize_kr_stock_symbol("005930") -> "005930"  # idempotent
    """
    return raw.strip().zfill(6)


def normalize_us_stock_symbol(raw: str) -> str:
    """Return an upper-cased, whitespace-stripped US ticker.

    Examples::

        normalize_us_stock_symbol(" aapl ") -> "AAPL"
        normalize_us_stock_symbol("AAPL")   -> "AAPL"  # idempotent
        normalize_us_stock_symbol("voo")    -> "VOO"
    """
    return raw.strip().upper()


_US_EXCHANGE_MAP: dict[str, str] = {  # ADDED
    "NMS": "NASDAQ",
    "NAS": "NASDAQ",
    "NGM": "NASDAQ",
    "NYQ": "NYSE",
    "NYS": "NYSE",
    "PCX": "NYSE",
    "ASE": "AMEX",
    "BTS": "BATS",
    "NCM": "NASDAQ",
}


def normalize_us_exchange_code(raw: str) -> str:  # ADDED
    """Map a yfinance exchange code to a human-readable exchange name.

    Examples::

        normalize_us_exchange_code("NMS") -> "NASDAQ"
        normalize_us_exchange_code("NYQ") -> "NYSE"
        normalize_us_exchange_code("XYZ") -> "XYZ"   # unknown codes pass through
    """
    return _US_EXCHANGE_MAP.get(raw.strip().upper(), raw.strip().upper())


def normalize_crypto_pair(raw: str, exchange: str) -> str:
    """Return a ccxt-compatible trading pair string.

    Rules (PRD §9):
    - Input already in ccxt format ``BASE/QUOTE`` → return as-is (uppercased).
    - Upbit legacy format ``QUOTE-BASE`` (e.g. ``KRW-BTC``) → ``BASE/QUOTE``
      (e.g. ``BTC/KRW``).
    - Exchange name is accepted case-insensitively.

    Examples::

        normalize_crypto_pair("KRW-BTC", "upbit")   -> "BTC/KRW"
        normalize_crypto_pair("BTC/USDT", "binance") -> "BTC/USDT"
        normalize_crypto_pair("btc/usdt", "binance") -> "BTC/USDT"
        normalize_crypto_pair("BTC/KRW", "upbit")   -> "BTC/KRW"  # idempotent
    """
    normalised = raw.strip().upper()

    # If the string already contains a slash it is already ccxt-format.
    if "/" in normalised:
        return normalised

    # Handle Upbit legacy ``QUOTE-BASE`` (e.g. KRW-BTC → BTC/KRW).
    if "-" in normalised and exchange.lower() == "upbit":
        parts = normalised.split("-", maxsplit=1)
        if len(parts) == 2:
            quote, base = parts
            return f"{base}/{quote}"

    # Fallback: return as-is (unknown format — adapter will surface the error).
    return normalised
