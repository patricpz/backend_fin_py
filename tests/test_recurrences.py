import uuid

import pytest
from httpx import AsyncClient


async def _setup(client, headers):
    account = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "1000.00"},
        headers=headers,
    )
    account_id = account.json()["id"]
    cat = await client.post(
        "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers
    )
    return account_id, cat.json()["id"]


class TestRecurrenceCreate:
    @pytest.mark.asyncio
    async def test_create_monthly_recurrence(self, client: AsyncClient, auth_headers):
        account_id, despesa_id = await _setup(client, auth_headers)
        response = await client.post(
            "/api/v1/recurrences",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "89.90",
                "frequencia": "mensal",
                "dia_do_mes": 15,
                "data_inicio": "2026-09-01",
                "descricao": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["frequencia"] == "mensal"
        assert data["ativo"] is True
        assert data["proxima_execucao"] == "2026-09-01"

    @pytest.mark.asyncio
    async def test_create_requires_valid_account(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/recurrences",
            json={
                "conta_id": str(uuid.uuid4()),
                "tipo": "despesa",
                "valor": "10.00",
                "frequencia": "diaria",
                "data_inicio": "2026-09-01",
                "descricao": "X",
            },
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["code"] == "ACCOUNT_NOT_FOUND"


class TestRecurrenceListUpdateDeleteGenerate:
    @pytest.mark.asyncio
    async def test_list_update_delete(self, client: AsyncClient, auth_headers):
        account_id, despesa_id = await _setup(client, auth_headers)
        created = await client.post(
            "/api/v1/recurrences",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "89.90",
                "frequencia": "mensal",
                "dia_do_mes": 15,
                "data_inicio": "2026-09-01",
                "descricao": "Netflix",
            },
            headers=auth_headers,
        )
        rec_id = created.json()["id"]

        listing = await client.get("/api/v1/recurrences", headers=auth_headers)
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        upd = await client.patch(
            f"/api/v1/recurrences/{rec_id}",
            json={"valor": "99.90", "ativo": False},
            headers=auth_headers,
        )
        assert upd.status_code == 200
        assert upd.json()["valor"] == "99.90"
        assert upd.json()["ativo"] is False

        detail = await client.get(f"/api/v1/recurrences/{rec_id}", headers=auth_headers)
        assert detail.status_code == 200

        delete = await client.delete(f"/api/v1/recurrences/{rec_id}", headers=auth_headers)
        assert delete.status_code == 204

    @pytest.mark.asyncio
    async def test_generate_all_pending(self, client: AsyncClient, auth_headers):
        account_id, despesa_id = await _setup(client, auth_headers)
        await client.post(
            "/api/v1/recurrences",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "50.00",
                "frequencia": "diaria",
                "data_inicio": "2026-08-01",
                "descricao": "Diária",
            },
            headers=auth_headers,
        )
        response = await client.post(
            "/api/v1/recurrences/generate",
            params={"data_limite": "2026-08-03"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["geradas"] == 3

        tx_list = await client.get("/api/v1/transactions", headers=auth_headers)
        assert tx_list.json()["total"] == 3

    @pytest.mark.asyncio
    async def test_generate_by_id(self, client: AsyncClient, auth_headers):
        account_id, despesa_id = await _setup(client, auth_headers)
        created = await client.post(
            "/api/v1/recurrences",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "50.00",
                "frequencia": "diaria",
                "data_inicio": "2026-08-01",
                "descricao": "Diária",
            },
            headers=auth_headers,
        )
        rec_id = created.json()["id"]
        response = await client.post(
            f"/api/v1/recurrences/{rec_id}/generate",
            params={"data_limite": "2026-08-02"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["geradas"] == 2
