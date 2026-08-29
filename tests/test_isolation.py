"""Verifica o isolamento de dados entre usuários: cada usuário só acessa seus próprios dados."""

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_auth(client, nome, email):
    r = await client.post(
        "/api/v1/auth/register", json={"nome": nome, "email": email, "senha": "password123"}
    )
    assert r.status_code == 201, r.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "senha": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class TestUserIsolation:
    @pytest.mark.asyncio
    async def test_accounts_are_isolated(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b@x.com")

        await client.post(
            "/api/v1/accounts",
            json={"nome": "Ana Nubank", "tipo": "corrente", "saldo_inicial": "100.00"},
            headers=headers_a,
        )

        a_list = await client.get("/api/v1/accounts", headers=headers_a)
        b_list = await client.get("/api/v1/accounts", headers=headers_b)
        assert a_list.json()["total"] == 1
        assert b_list.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_account_not_accessible_across_users(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a2@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b2@x.com")

        created = await client.post(
            "/api/v1/accounts", json={"nome": "Conta Ana", "tipo": "corrente"}, headers=headers_a
        )
        account_id = created.json()["id"]

        # B trying to read A's account -> 404
        response = await client.get(f"/api/v1/accounts/{account_id}", headers=headers_b)
        assert response.status_code == 404
        assert response.json()["code"] == "ACCOUNT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_categories_are_isolated_and_seeded_per_user(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a3@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b3@x.com")

        a_tree = await client.get("/api/v1/categories/tree", headers=headers_a)
        b_tree = await client.get("/api/v1/categories/tree", headers=headers_b)
        assert len(a_tree.json()) == 10
        assert len(b_tree.json()) == 10
        a_ids = {c["id"] for c in a_tree.json()}
        b_ids = {c["id"] for c in b_tree.json()}
        assert a_ids.isdisjoint(b_ids)

    @pytest.mark.asyncio
    async def test_transactions_are_isolated(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a4@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b4@x.com")

        # Ana: account + despesa category + transaction
        acc = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta Ana", "tipo": "corrente", "saldo_inicial": "0"},
            headers=headers_a,
        )
        acc_id = acc.json()["id"]
        cat = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers_a
        )
        cat_id = cat.json()["id"]
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": acc_id,
                "categoria_id": cat_id,
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-08-10",
                "descricao": "Mercado",
                "status": "confirmado",
            },
            headers=headers_a,
        )

        a_tx = await client.get("/api/v1/transactions", headers=headers_a)
        b_tx = await client.get("/api/v1/transactions", headers=headers_b)
        assert a_tx.json()["total"] == 1
        assert b_tx.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_goal_not_accessible_across_users(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a5@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b5@x.com")

        created = await client.post(
            "/api/v1/goals", json={"nome": "Meta Ana", "valor_alvo": "1000.00"}, headers=headers_a
        )
        goal_id = created.json()["id"]

        response = await client.get(f"/api/v1/goals/{goal_id}", headers=headers_b)
        assert response.status_code == 404
        assert response.json()["code"] == "GOAL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_budget_not_accessible_across_users(self, client: AsyncClient):
        headers_a = await _register_and_auth(client, "Ana", "a6@x.com")
        headers_b = await _register_and_auth(client, "Bia", "b6@x.com")

        # B reads a random, non-existent budget (B has none) -> 404
        response = await client.get(f"/api/v1/budgets/{uuid.uuid4()}", headers=headers_b)
        assert response.status_code == 404

        # A creates and B cannot read
        cat = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers_a
        )
        created = await client.post(
            "/api/v1/budgets",
            json={
                "categoria_id": cat.json()["id"],
                "valor_limite": "100.00",
                "mes": 8,
                "ano": 2026,
            },
            headers=headers_a,
        )
        budget_id = created.json()["id"]
        response = await client.get(f"/api/v1/budgets/{budget_id}", headers=headers_b)
        assert response.status_code == 404
        assert response.json()["code"] == "BUDGET_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client: AsyncClient):
        await _register_and_auth(client, "Ana", "dup@x.com")
        r = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Outra", "email": "dup@x.com", "senha": "password123"},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "EMAIL_EXISTS"
