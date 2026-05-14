"""Crypto base-ticker → display-name shim.

The static table is intentionally empty in production — all crypto display
names are now resolved at import time by ``CryptoNameResolver`` (DB cache +
Upbit ``/v1/market/all`` API). The shim is kept so the resolver interface
still has a static tier that tests / temporary overrides can seed.
"""

from __future__ import annotations

CRYPTO_NAMES: dict[str, str] = {}


def lookup_crypto_name(base: str) -> str | None:
    """Return the static-tier name for *base*, or ``None`` (the default)."""
    return CRYPTO_NAMES.get(base.upper())
