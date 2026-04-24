"""Unit tests for FxRateService — mocked repo and adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.fx import FrankfurterAdapter
from app.exceptions import FxFetchError, FxRateNotAvailableError
from app.models.fx_rate import FxRate
from app.repositories.fx_rate import FxRateRepository
from app.services.fx_rate import FxRateService


def _make_fx_rate(
    base: str = "USD",
    quote: str = "KRW",
    rate: str = "1380.25",
) -> FxRate:
    row = FxRate(
        base_currency=base,
        quote_currency=quote,
        rate=Decimal(rate),
        fetched_at=datetime.now(UTC),
    )
    return row


def _make_service(
    repo_rates: dict[tuple[str, str], FxRate | None] | None = None,
    adapter_rates: dict[str, Decimal] | None = None,
    adapter_raises: Exception | None = None,
) -> FxRateService:
    mock_repo = AsyncMock(spec=FxRateRepository)
    mock_adapter = AsyncMock(spec=FrankfurterAdapter)

    async def _get_latest(base: str, quote: str) -> FxRate | None:
        if repo_rates is None:
            return None
        return repo_rates.get((base, quote))

    mock_repo.get_latest.side_effect = _get_latest
    mock_repo.upsert = AsyncMock()
    mock_repo.list_all = AsyncMock(return_value=list((repo_rates or {}).values()))

    if adapter_raises is not None:
        mock_adapter.fetch_rates.side_effect = adapter_raises
    else:
        mock_adapter.fetch_rates = AsyncMock(return_value=adapter_rates or {})

    return FxRateService(repo=mock_repo, adapter=mock_adapter)


# ---------------------------------------------------------------------------
# refresh_all
# ---------------------------------------------------------------------------


class TestFxRateServiceRefreshAll:
    async def test_정상_갱신_upsert_횟수(self) -> None:
        """refresh_all should upsert N*(N-1) pairs for supported currencies."""
        # USD/KRW/EUR = 6 pairs total
        adapter_rates = {"KRW": Decimal("1380.25"), "EUR": Decimal("0.92")}
        svc = _make_service(adapter_rates=adapter_rates)
        count = await svc.refresh_all()
        # Each base fetches 2 quotes → 3 bases × 2 = 6
        assert count == 6

    async def test_어댑터_실패시_로깅하고_계속(self) -> None:
        """Single adapter failure should not abort — count should be 0."""
        svc = _make_service(adapter_raises=FxFetchError("network fail"))
        count = await svc.refresh_all()
        assert count == 0

    async def test_반환값_양수(self) -> None:
        adapter_rates = {"KRW": Decimal("1380.25"), "EUR": Decimal("0.92")}
        svc = _make_service(adapter_rates=adapter_rates)
        count = await svc.refresh_all()
        assert count > 0


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


class TestFxRateServiceConvert:
    async def test_같은_통화_그대로_반환(self) -> None:
        svc = _make_service()
        result = await svc.convert(Decimal("1000"), "USD", "USD")
        assert result == Decimal("1000")

    async def test_정상_환산(self) -> None:
        rate_row = _make_fx_rate("USD", "KRW", "1380.25")
        svc = _make_service(repo_rates={("USD", "KRW"): rate_row})
        result = await svc.convert(Decimal("10"), "USD", "KRW")
        assert result == Decimal("10") * Decimal("1380.25")

    async def test_rate_없으면_FxRateNotAvailableError(self) -> None:
        svc = _make_service(repo_rates={})
        with pytest.raises(FxRateNotAvailableError):
            await svc.convert(Decimal("100"), "USD", "JPY")

    async def test_Decimal_타입_보장(self) -> None:
        rate_row = _make_fx_rate("USD", "KRW", "1380.25")
        svc = _make_service(repo_rates={("USD", "KRW"): rate_row})
        result = await svc.convert(Decimal("1"), "USD", "KRW")
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# get_all_rates_for_conversion
# ---------------------------------------------------------------------------


class TestFxRateServiceGetAllRatesForConversion:
    async def test_모든_rate_있으면_dict_반환(self) -> None:
        rate_usd_to_krw = _make_fx_rate("USD", "KRW", "1380.25")
        rate_eur_to_krw = _make_fx_rate("EUR", "KRW", "1500.00")
        svc = _make_service(
            repo_rates={
                ("USD", "KRW"): rate_usd_to_krw,
                ("EUR", "KRW"): rate_eur_to_krw,
            }
        )
        result = await svc.get_all_rates_for_conversion(["USD", "EUR"], "KRW")
        assert result is not None
        assert result["USD"] == Decimal("1380.25")
        assert result["EUR"] == Decimal("1500.00")

    async def test_같은_통화_rate_1_반환(self) -> None:
        svc = _make_service(repo_rates={})
        result = await svc.get_all_rates_for_conversion(["KRW"], "KRW")
        assert result is not None
        assert result["KRW"] == Decimal("1")

    async def test_하나라도_없으면_None_반환(self) -> None:
        rate_usd_to_krw = _make_fx_rate("USD", "KRW", "1380.25")
        svc = _make_service(
            repo_rates={
                ("USD", "KRW"): rate_usd_to_krw,
                # EUR rate missing
            }
        )
        result = await svc.get_all_rates_for_conversion(["USD", "EUR"], "KRW")
        assert result is None

    async def test_빈_currencies_빈_dict(self) -> None:
        svc = _make_service()
        result = await svc.get_all_rates_for_conversion([], "KRW")
        assert result == {}


# ---------------------------------------------------------------------------
# list_all_rates
# ---------------------------------------------------------------------------


class TestFxRateServiceListAllRates:
    async def test_모든_행_반환(self) -> None:
        rate1 = _make_fx_rate("USD", "KRW", "1380.25")
        rate2 = _make_fx_rate("USD", "EUR", "0.92")
        mock_repo = AsyncMock(spec=FxRateRepository)
        mock_repo.list_all = AsyncMock(return_value=[rate1, rate2])
        svc = FxRateService(repo=mock_repo, adapter=MagicMock())
        rows = await svc.list_all_rates()
        assert len(rows) == 2

    async def test_빈_리스트(self) -> None:
        mock_repo = AsyncMock(spec=FxRateRepository)
        mock_repo.list_all = AsyncMock(return_value=[])
        svc = FxRateService(repo=mock_repo, adapter=MagicMock())
        rows = await svc.list_all_rates()
        assert rows == []
