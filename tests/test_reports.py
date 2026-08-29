import pytest
from httpx import AsyncClient


class TestMonthlySummary:
    @pytest.mark.asyncio
    async def test_monthly_summary(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, receita_id = await self._build_dataset(client, auth_headers)
        response = await client.get(
            "/api/v1/reports/monthly-summary", params={"mes": 8, "ano": 2026}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mes"] == 8
        assert data["ano"] == 2026
        assert data["total_receitas"] == "1500.00"
        assert data["total_despesas"] == "250.00"

    async def _build_dataset(self, client, headers):
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "100.00"},
            headers=headers,
        )
        account_id = account.json()["id"]
        despesa = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers
        )
        receita = await client.post(
            "/api/v1/categories", json={"nome": "Receita", "tipo": "receita"}, headers=headers
        )
        despesa_id, receita_id = despesa.json()["id"], receita.json()["id"]

        for payload in [
            {
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "250.00",
                "data": "2026-08-10",
                "descricao": "Mercado",
                "status": "confirmado",
            },
            {
                "conta_id": account_id,
                "categoria_id": receita_id,
                "tipo": "receita",
                "valor": "1500.00",
                "data": "2026-08-05",
                "descricao": "Salário",
                "status": "confirmado",
            },
        ]:
            r = await client.post("/api/v1/transactions", json=payload, headers=headers)
            assert r.status_code == 201, r.text

        return account_id, despesa_id, receita_id


class TestCategorySpending:
    @pytest.mark.asyncio
    async def test_category_spending(self, client: AsyncClient, auth_headers):
        _, despesa_id, _ = await self._setup(client, auth_headers)
        response = await client.get(
            "/api/v1/reports/category-spending",
            params={"mes": 8, "ano": 2026},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mes"] == 8
        assert round(float(data["total_despesas"]), 2) == 250.00
        assert any(c["categoria_id"] == despesa_id for c in data["categorias"])

    async def _setup(self, client, headers):
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "0"},
            headers=headers,
        )
        account_id = account.json()["id"]
        despesa = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers
        )
        despesa_id = despesa.json()["id"]
        await client.post(
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
            headers=headers,
        )
        return account_id, despesa_id, None


class TestBalanceEvolution:
    @pytest.mark.asyncio
    async def test_balance_evolution(self, client: AsyncClient, auth_headers):
        account_id, _, receita_id = await self._setup(client, auth_headers)
        response = await client.get(
            "/api/v1/reports/balance-evolution",
            params={"conta_id": account_id, "mes": 8, "ano": 2026},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conta_id"] == account_id
        assert len(data["pontos"]) >= 1

    async def _setup(self, client, headers):
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "100.00"},
            headers=headers,
        )
        account_id = account.json()["id"]
        receita = await client.post(
            "/api/v1/categories", json={"nome": "Receita", "tipo": "receita"}, headers=headers
        )
        receita_id = receita.json()["id"]
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": receita_id,
                "tipo": "receita",
                "valor": "100.00",
                "data": "2026-08-02",
                "descricao": "Salário",
                "status": "confirmado",
            },
            headers=headers,
        )
        return account_id, None, receita_id


class TestBudgetVsActual:
    @pytest.mark.asyncio
    async def test_budget_vs_actual(self, client: AsyncClient, auth_headers):
        account_id, despesa_id, _, budget_id = await self._setup(client, auth_headers)
        response = await client.get(
            "/api/v1/reports/budget-vs-actual", params={"mes": 8, "ano": 2026}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mes"] == 8
        assert data["ano"] == 2026
        assert any(o["categoria_id"] == despesa_id for o in data["orcamentos"])

    async def _setup(self, client, headers):
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "0"},
            headers=headers,
        )
        account_id = account.json()["id"]
        despesa = await client.post(
            "/api/v1/categories", json={"nome": "Despesa", "tipo": "despesa"}, headers=headers
        )
        despesa_id = despesa.json()["id"]

        budget = await client.post(
            "/api/v1/budgets",
            json={"categoria_id": despesa_id, "valor_limite": "1000.00", "mes": 8, "ano": 2026},
            headers=headers,
        )
        budget_id = budget.json()["id"]

        await client.post(
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
            headers=headers,
        )
        return account_id, despesa_id, None, budget_id
