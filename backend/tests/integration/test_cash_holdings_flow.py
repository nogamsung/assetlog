"""Integration tests for cash holdings — full POST→GET→PATCH→summary→DELETE flow.

Uses in-memory SQLite via the standard conftest fixtures (db_session + authenticated_client).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from httpx import AsyncClient


class TestCashHoldingsFlow:
    async def test_생성_후_목록에서_확인(self, authenticated_client: Any) -> None:
        """POST → GET flow."""
        client: AsyncClient = await authenticated_client()

        # --- POST: create ---
        create_response = await client.post(
            "/api/cash-accounts",
            json={"label": "My KRW Account", "currency": "KRW", "balance": "1000000"},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["label"] == "My KRW Account"
        assert created["currency"] == "KRW"
        assert Decimal(created["balance"]) == Decimal("1000000")
        account_id: int = created["id"]

        # --- GET: list contains new account ---
        list_response = await client.get("/api/cash-accounts")
        assert list_response.status_code == 200
        body = list_response.json()
        ids = [a["id"] for a in body]
        assert account_id in ids

    async def test_balance_업데이트(self, authenticated_client: Any) -> None:
        """POST → PATCH balance → 200 flow."""
        client: AsyncClient = await authenticated_client()

        create_r = await client.post(
            "/api/cash-accounts",
            json={"label": "Balance Test", "currency": "KRW", "balance": "1000000"},
        )
        assert create_r.status_code == 201
        account_id = create_r.json()["id"]

        patch_response = await client.patch(
            f"/api/cash-accounts/{account_id}",
            json={"balance": "2000000"},
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert Decimal(patched["balance"]) == Decimal("2000000")
        assert patched["label"] == "Balance Test"

    async def test_label_업데이트(self, authenticated_client: Any) -> None:
        """POST → PATCH label → 200 flow."""
        client: AsyncClient = await authenticated_client()

        create_r = await client.post(
            "/api/cash-accounts",
            json={"label": "Old Label", "currency": "USD", "balance": "500"},
        )
        assert create_r.status_code == 201
        account_id = create_r.json()["id"]

        patch_r = await client.patch(
            f"/api/cash-accounts/{account_id}",
            json={"label": "New Label"},
        )
        assert patch_r.status_code == 200
        assert patch_r.json()["label"] == "New Label"

    async def test_삭제_후_목록에서_제거(self, authenticated_client: Any) -> None:
        """POST → DELETE → GET (not in list) flow."""
        client: AsyncClient = await authenticated_client()

        create_r = await client.post(
            "/api/cash-accounts",
            json={"label": "To Delete", "currency": "KRW", "balance": "100"},
        )
        assert create_r.status_code == 201
        account_id = create_r.json()["id"]

        delete_r = await client.delete(f"/api/cash-accounts/{account_id}")
        assert delete_r.status_code == 204

        list_r = await client.get("/api/cash-accounts")
        ids = [a["id"] for a in list_r.json()]
        assert account_id not in ids

    async def test_삭제된_id_재삭제_404(self, authenticated_client: Any) -> None:
        client: AsyncClient = await authenticated_client()

        create_r = await client.post(
            "/api/cash-accounts",
            json={"label": "Temp", "currency": "USD", "balance": "100"},
        )
        assert create_r.status_code == 201
        account_id = create_r.json()["id"]

        first_delete = await client.delete(f"/api/cash-accounts/{account_id}")
        assert first_delete.status_code == 204

        second_delete = await client.delete(f"/api/cash-accounts/{account_id}")
        assert second_delete.status_code == 404

    async def test_삭제된_id_수정_404(self, authenticated_client: Any) -> None:
        client: AsyncClient = await authenticated_client()

        create_r = await client.post(
            "/api/cash-accounts",
            json={"label": "To Delete", "currency": "EUR", "balance": "500"},
        )
        assert create_r.status_code == 201
        account_id = create_r.json()["id"]

        await client.delete(f"/api/cash-accounts/{account_id}")

        patch_r = await client.patch(
            f"/api/cash-accounts/{account_id}",
            json={"balance": "999"},
        )
        assert patch_r.status_code == 404

    async def test_다중_통화_계정_생성(self, authenticated_client: Any) -> None:
        client: AsyncClient = await authenticated_client()

        ids: list[int] = []
        for label, currency, balance in [
            ("KRW Account", "KRW", "1000000"),
            ("USD Account", "USD", "500"),
            ("USDT Wallet", "USDT", "250"),
        ]:
            r = await client.post(
                "/api/cash-accounts",
                json={"label": label, "currency": currency, "balance": balance},
            )
            assert r.status_code == 201
            ids.append(r.json()["id"])

        list_r = await client.get("/api/cash-accounts")
        body = list_r.json()
        currencies = {a["currency"] for a in body}
        assert {"KRW", "USD", "USDT"}.issubset(currencies)
