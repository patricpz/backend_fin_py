import uuid

import pytest
from httpx import AsyncClient


def _account_payload(**overrides):
    payload = {
        "nome": "Nubank",
        "tipo": "corrente",
        "saldo_inicial": "100.00",
        "moeda": "BRL",
    }
    payload.update(overrides)
    return payload


class TestAccountCreate:
    @pytest.mark.asyncio
    async def test_create_account(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/accounts", json=_account_payload(), headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Nubank"
        assert data["tipo"] == "corrente"
        assert data["saldo_inicial"] == "100.00"
        assert data["saldo_atual"] == "100.00"
        assert data["ativo"] is True
        assert "id" in data
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_create_account_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/accounts", json=_account_payload())
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_all_account_types(self, client: AsyncClient, auth_headers):
        tipos = ["corrente", "poupanca", "carteira", "investimento", "cartao_credito"]
        for tipo in tipos:
            response = await client.post(
                "/api/v1/accounts",
                json=_account_payload(nome=f"Conta {tipo}", tipo=tipo),
                headers=auth_headers,
            )
            assert response.status_code == 201, f"{tipo}: {response.text}"
            assert response.json()["tipo"] == tipo


class TestAccountRead:
    @pytest.mark.asyncio
    async def test_list_accounts(self, client: AsyncClient, auth_headers):
        await client.post("/api/v1/accounts", json=_account_payload(), headers=auth_headers)
        await client.post(
            "/api/v1/accounts",
            json=_account_payload(nome="Itaú", tipo="poupanca"),
            headers=auth_headers,
        )
        response = await client.get("/api/v1/accounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_get_account(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/accounts", json=_account_payload(), headers=auth_headers
        )
        account_id = created.json()["id"]
        response = await client.get(f"/api/v1/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == account_id

    @pytest.mark.asyncio
    async def test_get_account_not_found(self, client: AsyncClient, auth_headers, test_user):
        response = await client.get(f"/api/v1/accounts/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["code"] == "ACCOUNT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_account_balance(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/accounts", json=_account_payload(saldo_inicial="500.00"), headers=auth_headers
        )
        account_id = created.json()["id"]
        response = await client.get(f"/api/v1/accounts/{account_id}/balance", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["saldo_atual"] == "500.00"


class TestAccountUpdate:
    @pytest.mark.asyncio
    async def test_update_account(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/accounts", json=_account_payload(), headers=auth_headers
        )
        account_id = created.json()["id"]
        response = await client.patch(
            f"/api/v1/accounts/{account_id}",
            json={"nome": "Nubank Atualizado", "ativo": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Nubank Atualizado"
        assert data["ativo"] is False


class TestAccountDelete:
    @pytest.mark.asyncio
    async def test_delete_without_transactions_hard(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/accounts", json=_account_payload(), headers=auth_headers
        )
        account_id = created.json()["id"]
        response = await client.delete(f"/api/v1/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 204
        # listing no longer shows it
        listing = await client.get("/api/v1/accounts", headers=auth_headers)
        assert listing.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_delete_with_transactions_soft(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/accounts", json=_account_payload(), headers=auth_headers
        )
        account_id = created.json()["id"]

        # create a category and transaction linked to the account
        cat = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=auth_headers
        )
        despesa_cat = cat.json()

        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_cat["id"],
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-08-10",
                "descricao": "Mercado",
                "status": "confirmado",
            },
            headers=auth_headers,
        )

        response = await client.delete(f"/api/v1/accounts/{account_id}", headers=auth_headers)
        assert response.status_code == 204


class TestAccountPagination:
    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient, auth_headers):
        for i in range(3):
            await client.post(
                "/api/v1/accounts", json=_account_payload(nome=f"Conta {i}"), headers=auth_headers
            )
        response = await client.get(
            "/api/v1/accounts", params={"page": 2, "size": 2}, headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 3
        assert len(result["items"]) == 1
