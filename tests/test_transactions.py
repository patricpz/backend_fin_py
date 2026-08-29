import uuid

import pytest
from httpx import AsyncClient


async def _setup(client, headers):
    """Create an account + a category and return their ids."""
    account = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "1000.00"},
        headers=headers,
    )
    account_id = account.json()["id"]
    despesa_id = (
        await client.post(
            "/api/v1/categories", json={"nome": "Despesa Teste", "tipo": "despesa"}, headers=headers
        )
    ).json()["id"]
    receita_id = (
        await client.post(
            "/api/v1/categories", json={"nome": "Receita Teste", "tipo": "receita"}, headers=headers
        )
    ).json()["id"]
    return account_id, despesa_id, receita_id


async def _build_dataset(client, headers):
    account_id, despesa_id, receita_id = await _setup(client, headers)
    for payload in [
        {
            "conta_id": account_id,
            "categoria_id": despesa_id,
            "tipo": "despesa",
            "valor": "50.00",
            "data": "2026-08-01",
            "descricao": "Mercado",
            "status": "confirmado",
        },
        {
            "conta_id": account_id,
            "categoria_id": receita_id,
            "tipo": "receita",
            "valor": "1000.00",
            "data": "2026-08-02",
            "descricao": "Salário",
            "status": "confirmado",
        },
    ]:
        r = await client.post("/api/v1/transactions", json=payload, headers=headers)
        assert r.status_code == 201, r.text
    return account_id, despesa_id, receita_id


class TestTransactionCreate:
    @pytest.mark.asyncio
    async def test_create_despesa(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _setup(client, auth_headers)
        response = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "250.00",
                "data": "2026-08-10",
                "descricao": "Mercado",
                "status": "confirmado",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tipo"] == "despesa"
        assert data["valor"] == "250.00"
        assert data["user_id"]

    @pytest.mark.asyncio
    async def test_create_receita(self, client: AsyncClient, auth_headers):
        account_id, _, receita_id = await _setup(client, auth_headers)
        response = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": receita_id,
                "tipo": "receita",
                "valor": "1500.00",
                "data": "2026-08-05",
                "descricao": "Salário",
                "status": "confirmado",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["tipo"] == "receita"

    @pytest.mark.asyncio
    async def test_create_transferencia(self, client: AsyncClient, auth_headers):
        account_id, _, _ = await _setup(client, auth_headers)
        destino = await client.post(
            "/api/v1/accounts", json={"nome": "Poupança", "tipo": "poupanca"}, headers=auth_headers
        )
        destino_id = destino.json()["id"]
        response = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "conta_destino_id": destino_id,
                "tipo": "transferencia",
                "valor": "300.00",
                "data": "2026-08-12",
                "descricao": "Guardar",
                "status": "confirmado",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["tipo"] == "transferencia"

    @pytest.mark.asyncio
    async def test_transfer_same_account_rejected(self, client: AsyncClient, auth_headers):
        account_id, _, _ = await _setup(client, auth_headers)
        response = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "conta_destino_id": account_id,
                "tipo": "transferencia",
                "valor": "100.00",
                "data": "2026-08-12",
                "descricao": "Erro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "SAME_ACCOUNT_TRANSFER"

    @pytest.mark.asyncio
    async def test_wrong_category_type_rejected(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _setup(client, auth_headers)
        # using a despesa category for a receita transaction
        response = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "receita",
                "valor": "100.00",
                "data": "2026-08-12",
                "descricao": "Erro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_CATEGORY_TYPE"

    @pytest.mark.asyncio
    async def test_idempotency_header(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _setup(client, auth_headers)
        key = str(uuid.uuid4())
        payload = {
            "conta_id": account_id,
            "categoria_id": despesa_id,
            "tipo": "despesa",
            "valor": "99.00",
            "data": "2026-08-15",
            "descricao": "Compra",
            "status": "confirmado",
        }
        r1 = await client.post(
            "/api/v1/transactions", json=payload, headers={**auth_headers, "Idempotency-Key": key}
        )
        assert r1.status_code == 201
        r2 = await client.post(
            "/api/v1/transactions", json=payload, headers={**auth_headers, "Idempotency-Key": key}
        )
        assert r2.status_code == 201
        listing = await client.get("/api/v1/transactions", headers=auth_headers)
        assert listing.json()["total"] == 1


class TestTransactionReadFilters:
    @pytest.mark.asyncio
    async def test_list_and_filters(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _build_dataset(client, auth_headers)
        # filter by tipo
        response = await client.get(
            "/api/v1/transactions", params={"tipo": "despesa"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        # filter by account
        response = await client.get(
            "/api/v1/transactions", params={"conta_id": account_id}, headers=auth_headers
        )
        assert response.json()["total"] == 2
        # filter by description substring
        response = await client.get(
            "/api/v1/transactions", params={"descricao": "Mercado"}, headers=auth_headers
        )
        assert response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_period_filter(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _build_dataset(client, auth_headers)
        response = await client.get(
            "/api/v1/transactions",
            params={"data_inicio": "2026-08-01", "data_fim": "2026-08-01"},
            headers=auth_headers,
        )
        assert response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_status_filter(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _setup(client, auth_headers)
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-08-01",
                "descricao": "Pendente",
                "status": "pendente",
            },
            headers=auth_headers,
        )
        response = await client.get(
            "/api/v1/transactions", params={"status": "pendente"}, headers=auth_headers
        )
        assert response.json()["total"] == 1


class TestTransactionUpdateConfirmDelete:
    @pytest.mark.asyncio
    async def test_get_update_confirm_delete(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _ = await _setup(client, auth_headers)
        created = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-08-01",
                "descricao": "Pendente",
                "status": "pendente",
            },
            headers=auth_headers,
        )
        tx_id = created.json()["id"]

        # get
        get_r = await client.get(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
        assert get_r.status_code == 200
        assert get_r.json()["status"] == "pendente"

        # update
        upd_r = await client.patch(
            f"/api/v1/transactions/{tx_id}", json={"descricao": "Atualizado"}, headers=auth_headers
        )
        assert upd_r.status_code == 200
        assert upd_r.json()["descricao"] == "Atualizado"

        # confirm
        conf_r = await client.post(f"/api/v1/transactions/{tx_id}/confirm", headers=auth_headers)
        assert conf_r.status_code == 200
        assert conf_r.json()["status"] == "confirmado"

        # delete
        del_r = await client.delete(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
        assert del_r.status_code == 204

        # get after delete -> 404
        gone = await client.get(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
        assert gone.status_code == 404
        assert gone.json()["code"] == "TRANSACTION_NOT_FOUND"
