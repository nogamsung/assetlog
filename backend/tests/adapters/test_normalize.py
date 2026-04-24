"""Unit tests for symbol normalisation utilities."""

from __future__ import annotations

import pytest

from app.adapters.normalize import (
    normalize_crypto_pair,
    normalize_kr_stock_symbol,
    normalize_us_stock_symbol,
)


class TestNormalizeKrStockSymbol:
    def test_zero_pads_short_code(self) -> None:
        assert normalize_kr_stock_symbol("5930") == "005930"

    def test_already_padded_is_idempotent(self) -> None:
        assert normalize_kr_stock_symbol("005930") == "005930"

    def test_strips_whitespace(self) -> None:
        assert normalize_kr_stock_symbol(" 005930 ") == "005930"

    def test_single_digit_padded_to_six(self) -> None:
        assert normalize_kr_stock_symbol("1") == "000001"

    def test_exact_six_digits_unchanged(self) -> None:
        assert normalize_kr_stock_symbol("123456") == "123456"

    def test_leading_zeros_preserved_when_already_six(self) -> None:
        assert normalize_kr_stock_symbol("000660") == "000660"


class TestNormalizeUsStockSymbol:
    def test_uppercases_lowercase(self) -> None:
        assert normalize_us_stock_symbol("aapl") == "AAPL"

    def test_strips_whitespace_and_uppercases(self) -> None:
        assert normalize_us_stock_symbol(" aapl ") == "AAPL"

    def test_already_upper_idempotent(self) -> None:
        assert normalize_us_stock_symbol("AAPL") == "AAPL"

    def test_mixed_case(self) -> None:
        assert normalize_us_stock_symbol("vOo") == "VOO"

    def test_only_whitespace_stripped(self) -> None:
        assert normalize_us_stock_symbol("  TSLA  ") == "TSLA"


class TestNormalizeCryptoPair:
    def test_upbit_legacy_krw_btc_converted(self) -> None:
        assert normalize_crypto_pair("KRW-BTC", "upbit") == "BTC/KRW"

    def test_already_ccxt_format_is_idempotent(self) -> None:
        assert normalize_crypto_pair("BTC/USDT", "binance") == "BTC/USDT"

    def test_lowercase_ccxt_uppercased(self) -> None:
        assert normalize_crypto_pair("btc/usdt", "binance") == "BTC/USDT"

    def test_upbit_ccxt_format_already_correct(self) -> None:
        assert normalize_crypto_pair("BTC/KRW", "upbit") == "BTC/KRW"

    def test_binance_eth_usdt(self) -> None:
        assert normalize_crypto_pair("ETH/USDT", "binance") == "ETH/USDT"

    def test_upbit_lowercase_exchange(self) -> None:
        assert normalize_crypto_pair("KRW-ETH", "upbit") == "ETH/KRW"

    def test_upbit_exchange_uppercase_accepted(self) -> None:
        # exchange param is lowercased internally — UPBIT treated same as upbit
        assert normalize_crypto_pair("KRW-BTC", "UPBIT") == "BTC/KRW"

    @pytest.mark.parametrize(
        ("raw", "exchange", "expected"),
        [
            ("KRW-BTC", "upbit", "BTC/KRW"),
            ("BTC/USDT", "binance", "BTC/USDT"),
            ("btc/krw", "upbit", "BTC/KRW"),
        ],
    )
    def test_parametrized(self, raw: str, exchange: str, expected: str) -> None:
        assert normalize_crypto_pair(raw, exchange) == expected
