"""Router tests for POST /api/integrations/import-file."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURE_TXT = (
    Path(__file__).parent.parent
    / "fixtures"
    / "parsers"
    / "toss_securities"
    / "sample_extracted.txt"
)


class TestAuthGuard:
    async def test_unauthenticated_returns_401(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/integrations/import-file",
            params={"source": "toss_securities", "dry_run": "true"},
            files={"file": ("test.txt", b"dummy", "application/octet-stream")},
        )
        assert response.status_code == 401


class TestValidation:
    async def test_unsupported_source_returns_422(
        self,
        authenticated_client,  # type: ignore[no-untyped-def]
    ) -> None:
        client: AsyncClient = await authenticated_client()
        response = await client.post(
            "/api/integrations/import-file",
            params={"source": "unknown_broker", "dry_run": "true"},
            files={"file": ("test.txt", b"dummy", "application/octet-stream")},
        )
        assert response.status_code == 422

    async def test_empty_file_returns_422(
        self,
        authenticated_client,  # type: ignore[no-untyped-def]
    ) -> None:
        client: AsyncClient = await authenticated_client()
        response = await client.post(
            "/api/integrations/import-file",
            params={"source": "toss_securities", "dry_run": "true"},
            files={"file": ("test.txt", b"", "application/octet-stream")},
        )
        assert response.status_code == 422


class TestDryRunWithFixture:
    async def test_dry_run_returns_200_with_schema(
        self,
        authenticated_client,  # type: ignore[no-untyped-def]
    ) -> None:
        if not FIXTURE_TXT.exists():
            pytest.skip("Fixture file not found")

        from unittest.mock import patch

        from app.adapters.parsers.toss_securities import parse_text

        txt_content = FIXTURE_TXT.read_bytes()

        def fake_parse_pdf(file_bytes: bytes) -> object:
            return parse_text(file_bytes.decode("utf-8"))

        client: AsyncClient = await authenticated_client()
        with patch(
            "app.adapters.parsers.toss_securities.parse_pdf",
            side_effect=fake_parse_pdf,
        ):
            response = await client.post(
                "/api/integrations/import-file",
                params={"source": "toss_securities", "dry_run": "true"},
                files={"file": ("statement.pdf", txt_content, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "inserted_trades" in data
        assert "inserted_dividends" in data
        assert "inserted_cash_txs" in data
        assert "skipped_unsupported" in data
        assert data["dry_run"] is True
        assert isinstance(data["preview"], list)
        assert len(data["preview"]) <= 20

    async def test_dry_run_trade_count(
        self,
        authenticated_client,  # type: ignore[no-untyped-def]
    ) -> None:
        if not FIXTURE_TXT.exists():
            pytest.skip("Fixture file not found")

        from unittest.mock import patch

        from app.adapters.parsers.toss_securities import parse_text

        txt_content = FIXTURE_TXT.read_bytes()

        def fake_parse_pdf(file_bytes: bytes) -> object:
            return parse_text(file_bytes.decode("utf-8"))

        client: AsyncClient = await authenticated_client()
        with patch(
            "app.adapters.parsers.toss_securities.parse_pdf",
            side_effect=fake_parse_pdf,
        ):
            response = await client.post(
                "/api/integrations/import-file",
                params={"source": "toss_securities", "dry_run": "true"},
                files={"file": ("statement.pdf", txt_content, "application/pdf")},
            )

        data = response.json()
        # Should have substantial trades
        assert data["inserted_trades"] >= 100
