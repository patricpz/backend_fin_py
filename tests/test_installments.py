import uuid

import pytest
from httpx import AsyncClient

from uuid import UUID


async def _setup(client: AsyncClient):
    """Cria um usuário real via auth, obtém token, cria conta + categoria e retorna (headers, account_id, category_id)."""
    user_email = f"parcela-{uuid.uuid4()}@example.com"

    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "nome": "Teste Parcela",
            "email": user_email,
            "senha": "testpass123",
        },
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "senha": "testpass123",
        },
    )
    assert login.status_code == 200, login.text
    access_token = login.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    account = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "1000.00"},
        headers=headers,
    )
    assert account.status_code == 201, account.text
    account_id = account.json()["id"]

    resp = await client.post(
        "/api/v1/categories",
        json={"nome": "Despesa Teste", "tipo": "despesa"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    category_id = resp.json()["id"]

    return headers, account_id, category_id


@pytest.mark.asyncio
async def test_parcelar_despesa(client: AsyncClient):
    headers, account_id, despesa_id = await _setup(client)
    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(despesa_id),
            "tipo": "despesa",
            "valor": "300.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 200

    parcels = await client.get(f"/api/v1/transactions/{tx_id}/parcelas", headers=headers)
    assert parcels.status_code == 200
    assert len(parcels.json()) == 3


@pytest.mark.asyncio
async def test_parcelar_receita(client: AsyncClient):
    headers, account_id, _ = await _setup(client)
    receita_id = (
        await client.post(
            "/api/v1/categories",
            json={"nome": "Receita Teste", "tipo": "receita"},
            headers=headers,
        )
    ).json()["id"]

    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(receita_id),
            "tipo": "receita",
            "valor": "300.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela receita",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 200

    parcels = await client.get(f"/api/v1/transactions/{tx_id}/parcelas", headers=headers)
    assert parcels.status_code == 200
    assert len(parcels.json()) == 3


@pytest.mark.asyncio
async def test_nao_parcelar_transferencia(client: AsyncClient):
    headers, account_id, _ = await _setup(client)

    other_account = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta Destino", "tipo": "corrente", "saldo_inicial": "0.00"},
        headers=headers,
    )
    assert other_account.status_code == 201
    other_account_id = other_account.json()["id"]

    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "conta_destino_id": str(other_account_id),
            "tipo": "transferencia",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Teste transferencia",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ja_parcelada_rejeita_nova_parcela(client: AsyncClient):
    headers, account_id, despesa_id = await _setup(client)
    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(despesa_id),
            "tipo": "despesa",
            "valor": "300.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 200
    resp2 = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 2, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_listar_parcelas(client: AsyncClient):
    headers, account_id, despesa_id = await _setup(client)
    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(despesa_id),
            "tipo": "despesa",
            "valor": "300.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 200

    parcels = await client.get(f"/api/v1/transactions/{tx_id}/parcelas", headers=headers)
    assert parcels.status_code == 200
    assert len(parcels.json()) == 3


@pytest.mark.asyncio
async def test_valor_por_parcela_informado(client: AsyncClient):
    headers, account_id, despesa_id = await _setup(client)
    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(despesa_id),
            "tipo": "despesa",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={
            "numero_parcelas": 3,
            "valor_por_parcela": "30.00",
            "data_inicio": "2026-09-10",
        },
        headers=headers,
    )
    assert resp.status_code == 200

    parcels = await client.get(f"/api/v1/transactions/{tx_id}/parcelas", headers=headers)
    for parcel in parcels.json():
        assert float(parcel["valor"]) == 30.0


@pytest.mark.asyncio
async def test_total_parcelas_excede_valor(client: AsyncClient):
    headers, account_id, despesa_id = await _setup(client)
    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "categoria_id": str(despesa_id),
            "tipo": "despesa",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Teste parcela",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={
            "numero_parcelas": 3,
            "valor_por_parcela": "40.00",
            "data_inicio": "2026-09-10",
        },
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_parcelar_ignorada_com_transferencia(client: AsyncClient):
    headers, account_id, _ = await _setup(client)

    other_account = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta Destino", "tipo": "corrente", "saldo_inicial": "0.00"},
        headers=headers,
    )
    assert other_account.status_code == 201
    other_account_id = other_account.json()["id"]

    tx = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": str(account_id),
            "conta_destino_id": str(other_account_id),
            "tipo": "transferencia",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Teste transferencia",
            "status": "confirmado",
        },
        headers=headers,
    )
    assert tx.status_code == 201
    tx_id = tx.json()["id"]

    resp = await client.post(
        f"/api/v1/transactions/{tx_id}/parcelar",
        json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
        headers=headers,
    )
    assert resp.status_code == 400
