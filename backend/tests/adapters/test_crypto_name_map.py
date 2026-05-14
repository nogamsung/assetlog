"""Unit tests for the crypto base→name lookup."""

from __future__ import annotations

from app.adapters.crypto_name_map import lookup_crypto_name


def test_btc_maps_to_bitcoin() -> None:
    assert lookup_crypto_name("BTC") == "Bitcoin"


def test_eth_maps_to_ethereum() -> None:
    assert lookup_crypto_name("ETH") == "Ethereum"


def test_lowercase_input_is_normalised() -> None:
    assert lookup_crypto_name("btc") == "Bitcoin"


def test_unknown_returns_none() -> None:
    assert lookup_crypto_name("UNKNOWN_COIN") is None


def test_stablecoins_present() -> None:
    assert lookup_crypto_name("USDT") == "Tether"
    assert lookup_crypto_name("USDC") == "USD Coin"
