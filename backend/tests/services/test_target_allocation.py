"""Integration tests for TargetAllocationService."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.target_allocation import TargetAllocationRepository
from app.schemas.target_allocation import (
    TargetAllocationEntry,
    TargetAllocationUpsertRequest,
)
from app.services.target_allocation import TargetAllocationService


@pytest.fixture()
def service(db_session: AsyncSession) -> TargetAllocationService:
    return TargetAllocationService(TargetAllocationRepository(db_session))


class TestListEmpty:
    async def test_빈_DB_빈_entries(self, service: TargetAllocationService) -> None:
        result = await service.list_targets()
        assert result.entries == []


class TestReplace:
    async def test_신규_저장(self, service: TargetAllocationService) -> None:
        payload = TargetAllocationUpsertRequest(
            entries=[
                TargetAllocationEntry(asset_type="us_stock", target_pct=Decimal("0.6")),
                TargetAllocationEntry(asset_type="crypto", target_pct=Decimal("0.2")),
                TargetAllocationEntry(asset_type="cash", target_pct=Decimal("0.2")),
            ]
        )
        result = await service.replace(payload)
        assert len(result.entries) == 3
        sums = sum((e.target_pct for e in result.entries), Decimal("0"))
        assert sums == Decimal("1.0")

    async def test_빈_리스트_clear(self, service: TargetAllocationService) -> None:
        await service.replace(
            TargetAllocationUpsertRequest(
                entries=[
                    TargetAllocationEntry(
                        asset_type="us_stock", target_pct=Decimal("0.5")
                    )
                ]
            )
        )
        result = await service.replace(TargetAllocationUpsertRequest(entries=[]))
        assert result.entries == []

    async def test_replace_삭제_후_재삽입(
        self, service: TargetAllocationService
    ) -> None:
        await service.replace(
            TargetAllocationUpsertRequest(
                entries=[
                    TargetAllocationEntry(
                        asset_type="us_stock", target_pct=Decimal("0.5")
                    ),
                ]
            )
        )
        # Replace with different content
        result = await service.replace(
            TargetAllocationUpsertRequest(
                entries=[
                    TargetAllocationEntry(
                        asset_type="kr_stock", target_pct=Decimal("0.7")
                    ),
                ]
            )
        )
        assert len(result.entries) == 1
        assert str(result.entries[0].asset_type) == "kr_stock"


class TestSchemaValidation:
    def test_합계_초과_거부(self) -> None:
        with pytest.raises(ValueError):
            TargetAllocationUpsertRequest(
                entries=[
                    TargetAllocationEntry(
                        asset_type="us_stock", target_pct=Decimal("0.6")
                    ),
                    TargetAllocationEntry(
                        asset_type="kr_stock", target_pct=Decimal("0.5")
                    ),
                ]
            )

    def test_중복_asset_type_거부(self) -> None:
        with pytest.raises(ValueError):
            TargetAllocationUpsertRequest(
                entries=[
                    TargetAllocationEntry(
                        asset_type="us_stock", target_pct=Decimal("0.3")
                    ),
                    TargetAllocationEntry(
                        asset_type="us_stock", target_pct=Decimal("0.2")
                    ),
                ]
            )

    def test_범위_초과_거부(self) -> None:
        with pytest.raises(ValueError):
            TargetAllocationEntry(asset_type="us_stock", target_pct=Decimal("1.5"))
