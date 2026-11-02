import pytest
from httpx import AsyncClient


async def _expense_category(client, headers):
    cat = await client.post(
        "/api/v1/categories", json={"nome": "Alimentação", "tipo": "despesa"}, headers=headers
    )
    return cat.json()["id"]


class TestBudgetCreate:
    @pytest.mark.asyncio
    async def test_create_budget(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        response = await client.post(
            "/api/v1/budgets",
            json={
                "categoria_id": category_id,
                "valor_limite": "2000.00",
                "mes": 8,
                "ano": 2026,
                "alerta_percentual": 80,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["mes"] == 8
        assert data["ano"] == 2026
        assert data["valor_limite"] == "2000.00"

    @pytest.mark.asyncio
    async def test_duplicate_budget_rejected(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        payload = {"categoria_id": category_id, "valor_limite": "2000.00", "mes": 8, "ano": 2026}
        r1 = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/budgets", json=payload, headers=auth_headers)
        assert r2.status_code == 409
        assert r2.json()["code"] == "BUDGET_EXISTS"

    @pytest.mark.asyncio
    async def test_budget_rejects_income_category(self, client: AsyncClient, auth_headers):
        cat = await client.post(
            "/api/v1/categories", json={"nome": "Receita", "tipo": "receita"}, headers=auth_headers
        )
        response = await client.post(
            "/api/v1/budgets",
            json={
                "categoria_id": cat.json()["id"],
                "valor_limite": "100.00",
                "mes": 8,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "BUDGET_INVALID_CATEGORY_TYPE"


class TestBudgetListProgressUpdateDelete:
    @pytest.mark.asyncio
    async def test_list_and_progress(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        created = await client.post(
            "/api/v1/budgets",
            json={"categoria_id": category_id, "valor_limite": "1000.00", "mes": 8, "ano": 2026},
            headers=auth_headers,
        )
        budget_id = created.json()["id"]

        listing = await client.get(
            "/api/v1/budgets", params={"mes": 8, "ano": 2026}, headers=auth_headers
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

        progress = await client.get(f"/api/v1/budgets/{budget_id}/progress", headers=auth_headers)
        assert progress.status_code == 200
        data = progress.json()
        assert data["budget_id"] == budget_id
        assert data["valor_limite"] == "1000.00"
        assert data["valor_gasto"] == "0.00"
        assert data["percentual"] == 0.0
        assert data["alerta"] is False

    @pytest.mark.asyncio
    async def test_progress_reflects_spending(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta", "tipo": "corrente", "saldo_inicial": "0"},
            headers=auth_headers,
        )
        account_id = account.json()["id"]

        created = await client.post(
            "/api/v1/budgets",
            json={"categoria_id": category_id, "valor_limite": "1000.00", "mes": 8, "ano": 2026},
            headers=auth_headers,
        )
        budget_id = created.json()["id"]

        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": category_id,
                "tipo": "despesa",
                "valor": "250.00",
                "data": "2026-08-10",
                "descricao": "Mercado",
                "status": "confirmado",
            },
            headers=auth_headers,
        )

        progress = await client.get(f"/api/v1/budgets/{budget_id}/progress", headers=auth_headers)
        data = progress.json()
        assert data["valor_gasto"] == "250.00"
        assert data["percentual"] == 25.0

    @pytest.mark.asyncio
    async def test_update_and_delete(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        created = await client.post(
            "/api/v1/budgets",
            json={"categoria_id": category_id, "valor_limite": "500.00", "mes": 8, "ano": 2026},
            headers=auth_headers,
        )
        budget_id = created.json()["id"]

        upd = await client.patch(
            f"/api/v1/budgets/{budget_id}",
            json={"valor_limite": "750.00", "alerta_percentual": 90},
            headers=auth_headers,
        )
        assert upd.status_code == 200
        assert upd.json()["valor_limite"] == "750.00"

        delete = await client.delete(f"/api/v1/budgets/{budget_id}", headers=auth_headers)
        assert delete.status_code == 204


class TestBudgetNameAndOptionalCategory:
    @pytest.mark.asyncio
    async def test_create_budget_with_custom_name(self, client: AsyncClient, auth_headers):
        category_id = await _expense_category(client, auth_headers)
        response = await client.post(
            "/api/v1/budgets",
            json={
                "nome": "Supermercado Mensal",
                "categoria_id": category_id,
                "valor_limite": "1500.00",
                "mes": 10,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Supermercado Mensal"
        assert data["name"] == "Supermercado Mensal"
        assert data["categoria_id"] == category_id
        assert data["valor_limite"] == "1500.00"

    @pytest.mark.asyncio
    async def test_create_general_budget_without_category(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/budgets",
            json={
                "nome": "Teto Geral de Gastos",
                "valor_limite": "5000.00",
                "mes": 10,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Teto Geral de Gastos"
        assert data["name"] == "Teto Geral de Gastos"
        assert data["categoria_id"] is None
        assert data["categoria_nome"] is None
        assert data["valor_limite"] == "5000.00"

    @pytest.mark.asyncio
    async def test_create_budget_without_category_and_without_name_defaults_to_geral(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/budgets",
            json={
                "valor_limite": "3000.00",
                "mes": 11,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Orçamento Geral"
        assert data["categoria_id"] is None

    @pytest.mark.asyncio
    async def test_general_budget_progress_reflects_all_expenses(self, client: AsyncClient, auth_headers):
        account = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta Geral", "tipo": "corrente", "saldo_inicial": "10000"},
            headers=auth_headers,
        )
        account_id = account.json()["id"]

        cat1 = await client.post(
            "/api/v1/categories", json={"nome": "Saúde", "tipo": "despesa"}, headers=auth_headers
        )
        cat2 = await client.post(
            "/api/v1/categories", json={"nome": "Lazer", "tipo": "despesa"}, headers=auth_headers
        )

        # Orçamento global de 1000 para mes 10/2026
        budget_res = await client.post(
            "/api/v1/budgets",
            json={
                "nome": "Orçamento Global Outubro",
                "valor_limite": "1000.00",
                "mes": 10,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        budget_id = budget_res.json()["id"]

        # Duas despesas em categorias diferentes
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": cat1.json()["id"],
                "tipo": "despesa",
                "valor": "300.00",
                "data": "2026-10-05",
                "descricao": "Farmácia",
                "status": "confirmado",
            },
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": cat2.json()["id"],
                "tipo": "despesa",
                "valor": "200.00",
                "data": "2026-10-15",
                "descricao": "Cinema",
                "status": "confirmado",
            },
            headers=auth_headers,
        )

        progress = await client.get(f"/api/v1/budgets/{budget_id}/progress", headers=auth_headers)
        assert progress.status_code == 200
        pdata = progress.json()
        # Total gasto deve somar as despesas de ambas as categorias (300 + 200 = 500)
        assert pdata["valor_gasto"] == "500.00"
        assert pdata["percentual"] == 50.0
        assert pdata["nome"] == "Orçamento Global Outubro"
