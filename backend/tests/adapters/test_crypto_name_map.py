"""Unit tests for the crypto static-name shim.

Production keeps the table empty (resolution flows through ``CryptoNameResolver``
backed by Upbit + DB cache). The shim is retained only as a hook for tests
and temporary overrides.
"""

from __future__ import annotations

from app.adapters import crypto_name_map
from app.adapters.crypto_name_map import lookup_crypto_name


def test_static_map_is_empty_in_production() -> None:
    assert crypto_name_map.CRYPTO_NAMES == {}


def test_lookup_returns_none_when_empty() -> None:
    assert lookup_crypto_name("BTC") is None
    assert lookup_crypto_name("ETH") is None


def test_lookup_respects_runtime_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setitem(crypto_name_map.CRYPTO_NAMES, "BTC", "비트코인")
    assert lookup_crypto_name("BTC") == "비트코인"
    assert lookup_crypto_name("btc") == "비트코인"
