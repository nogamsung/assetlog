"""Unit tests for UpbitAccountAdapter._map_trade — pure mapping logic."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.adapters.upbit_account import _map_trade
from app.domain.transaction_type import TransactionType
from app.exceptions import ExternalIntegrationError


def _raw(**overrides: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "id": "tx-1",
        "side": "buy",
        "symbol": "BTC/KRW",
        "timestamp": 1714521600000,  # 2024-05-01T00:00:00Z
        "amount": 0.5,
        "price": 50000000.0,
    }
    raw.update(overrides)
    return raw


class TestMapTrade:
    def test_정상_매핑(self) -> None:
        result = _map_trade(_raw())
        assert result is not None
        assert result.external_id == "tx-1"
        assert result.symbol == "BTC"
        assert result.quote_currency == "KRW"
        assert result.side == TransactionType.BUY
        assert result.quantity == Decimal("0.5")
        assert result.price == Decimal("50000000.0")
        assert result.traded_at == datetime(2024, 5, 1, tzinfo=UTC)

    def test_sell_쪽(self) -> None:
        result = _map_trade(_raw(side="sell"))
        assert result is not None
        assert result.side == TransactionType.SELL

    def test_id가_숫자면_None(self) -> None:
        assert _map_trade(_raw(id=123)) is None

    def test_side가_unknown면_None(self) -> None:
        assert _map_trade(_raw(side="cancel")) is None

    def test_symbol_파싱_실패_None(self) -> None:
        assert _map_trade(_raw(symbol="INVALID")) is None

    def test_amount이_str면_None(self) -> None:
        assert _map_trade(_raw(amount="0.5")) is None


class TestUpbitAccountAdapter:
    def test_키_없으면_init_에러(self) -> None:
        from app.adapters.upbit_account import UpbitAccountAdapter

        with pytest.raises(ExternalIntegrationError):
            UpbitAccountAdapter(access_key="", secret_key="x")
        with pytest.raises(ExternalIntegrationError):
            UpbitAccountAdapter(access_key="x", secret_key="")
