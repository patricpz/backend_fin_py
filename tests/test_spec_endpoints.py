import pytest
from httpx import AsyncClient
import uuid


class TestSpecErrorFormat:
    @pytest.mark.asyncio
    async def test_error_envelope_matches_spec(self, client: AsyncClient, auth_headers):
        response = await client.get(f"/api/v1/categories/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        data = response.json()
        assert "statusCode" in data
        assert data["statusCode"] == 404
        assert "error" in data
        assert data["error"] == "Not Found"
        assert "message" in data
        assert "timestamp" in data
        # Check backward compatibility fields
        assert "code" in data
        assert "detail" in data


class TestSpecCategories:
    @pytest.mark.asyncio
    async def test_category_crud_and_spec_fields(self, client: AsyncClient, auth_headers):
        # Create category with Portuguese/Spec fields
        res = await client.post(
            "/api/v1/categories",
            json={
                "nome": "Restaurantes",
                "tipo": "despesa",
                "cor": "#F97316",
                "icone": "Coffee",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        cat = res.json()
        cat_id = cat["id"]
        assert cat["name"] == "Restaurantes"
        assert cat["type"] == "despesa"
        assert cat["color"] == "#F97316"
        assert cat["icon"] == "Coffee"
        assert cat["userId"] is not None
        assert cat["active"] is True

        # Duplicate name+type rejected
        dup_res = await client.post(
            "/api/v1/categories",
            json={
                "nome": "Restaurantes",
                "tipo": "despesa",
            },
            headers=auth_headers,
        )
        assert dup_res.status_code in (400, 409)
        dup_data = dup_res.json()
        assert dup_data["statusCode"] in (400, 409)
        assert "exists" in dup_data["message"].lower()

        # Create subcategory
        sub_res = await client.post(
            "/api/v1/categories",
            json={
                "nome": "Cafeterias",
                "tipo": "despesa",
                "categoria_pai_id": cat_id,
            },
            headers=auth_headers,
        )
        assert sub_res.status_code == 201
        sub_cat = sub_res.json()
        assert sub_cat["parentId"] == cat_id

        # Tree endpoint
        tree_res = await client.get("/api/v1/categories/tree?type=despesa", headers=auth_headers)
        assert tree_res.status_code == 200
        tree = tree_res.json()
        parent_node = next((n for n in tree if n["id"] == cat_id), None)
        assert parent_node is not None
        assert len(parent_node["children"]) == 1
        assert parent_node["children"][0]["name"] == "Cafeterias"

        # List with query parameters
        list_res = await client.get(
            "/api/v1/categories?type=despesa&active=true", headers=auth_headers
        )
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(i["id"] == cat_id for i in items)

    @pytest.mark.asyncio
    async def test_category_delete_with_and_without_transactions(
        self, client: AsyncClient, auth_headers
    ):
        # Create an account
        acc = await client.post(
            "/api/v1/accounts",
            json={"nome": "Carteira", "tipo": "carteira", "saldo_inicial": "1000.00"},
            headers=auth_headers,
        )
        acc_id = acc.json()["id"]

        # Create category 1 and category 2
        cat1_res = await client.post(
            "/api/v1/categories",
            json={"nome": "Alimentação Antiga", "tipo": "despesa"},
            headers=auth_headers,
        )
        cat1_id = cat1_res.json()["id"]

        cat2_res = await client.post(
            "/api/v1/categories",
            json={"nome": "Alimentação Nova", "tipo": "despesa"},
            headers=auth_headers,
        )
        cat2_id = cat2_res.json()["id"]

        # Add transaction linked to category 1
        tx_res = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": acc_id,
                "categoria_id": cat1_id,
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-10-25",
                "descricao": "Almoço",
                "status": "confirmado",
            },
            headers=auth_headers,
        )
        assert tx_res.status_code == 201
        tx_id = tx_res.json()["id"]

        # Deleting category 1 without migrar_para_id must fail with 409
        del_fail = await client.delete(f"/api/v1/categories/{cat1_id}", headers=auth_headers)
        assert del_fail.status_code == 409
        data = del_fail.json()
        assert "migrar_para_id" in data["message"]

        # Deleting category 1 with migrar_para_id must succeed (204)
        del_ok = await client.delete(
            f"/api/v1/categories/{cat1_id}",
            params={"migrar_para_id": cat2_id},
            headers=auth_headers,
        )
        assert del_ok.status_code == 204

        # Verify transaction now belongs to category 2
        tx_check = await client.get(f"/api/v1/transactions/{tx_id}", headers=auth_headers)
        assert tx_check.status_code == 200
        assert tx_check.json()["categoria_id"] == cat2_id


class TestSpecBudgets:
    @pytest.mark.asyncio
    async def test_budget_full_spec(self, client: AsyncClient, auth_headers):
        # Create category
        cat = await client.post(
            "/api/v1/categories",
            json={"nome": "Transporte Urbano", "tipo": "despesa"},
            headers=auth_headers,
        )
        cat_id = cat.json()["id"]

        # Create budget using spec field names
        res = await client.post(
            "/api/v1/budgets",
            json={
                "categoria_id": cat_id,
                "valor_limite": 1500.00,
                "mes": 10,
                "ano": 2026,
                "percentual_alerta": 80,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        b_data = res.json()
        budget_id = b_data["id"]
        assert b_data["categoryName"] == "Transporte Urbano"
        assert float(b_data["limitAmount"]) == 1500.00
        assert b_data["alertPercentage"] == 80
        assert b_data["month"] == 10
        assert b_data["year"] == 2026

        # Check list with month/year params
        list_res = await client.get("/api/v1/budgets?month=10&year=2026", headers=auth_headers)
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        b_item = next((i for i in items if i["id"] == budget_id), None)
        assert b_item is not None
        assert b_item["categoryName"] == "Transporte Urbano"
        assert float(b_item["limitAmount"]) == 1500.00

        # Check progress endpoint
        prog_res = await client.get(f"/api/v1/budgets/{budget_id}/progress", headers=auth_headers)
        assert prog_res.status_code == 200
        prog = prog_res.json()
        assert prog["budgetId"] == budget_id
        assert prog["categoryId"] == cat_id
        assert prog["categoryName"] == "Transporte Urbano"
        assert float(prog["limitAmount"]) == 1500.00
        assert float(prog["spent"]) == 0.00
        assert prog["percentage"] == 0.0
        assert prog["alert"] is False

        # Patch budget
        patch_res = await client.patch(
            f"/api/v1/budgets/{budget_id}",
            json={"valor_limite": 1800.00, "percentual_alerta": 85},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        assert float(patch_res.json()["limitAmount"]) == 1800.00
        assert patch_res.json()["alertPercentage"] == 85

        # Delete budget
        del_res = await client.delete(f"/api/v1/budgets/{budget_id}", headers=auth_headers)
        assert del_res.status_code == 204


class TestSpecGoals:
    @pytest.mark.asyncio
    async def test_goals_and_contributions_spec(self, client: AsyncClient, auth_headers):
        # Create goal
        res = await client.post(
            "/api/v1/goals",
            json={
                "nome": "Viagem Japão",
                "descricao": "Férias de 2027",
                "valor_alvo": 25000.00,
                "data_alvo": "2027-09-30",
                "categoria": "Lazer",
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        g = res.json()
        goal_id = g["id"]
        assert g["name"] == "Viagem Japão"
        assert g["description"] == "Férias de 2027"
        assert float(g["targetAmount"]) == 25000.00
        assert g["targetDate"] == "2027-09-30"
        assert g["status"] == "em_andamento"
        assert float(g["currentAmount"]) == 0.00

        # Attempt withdrawal when current balance is 0 -> MUST REJECT WITH 400
        bad_with = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "valor": 100.00,
                "tipo": "retirada",
                "data": "2026-10-25",
                "observacao": "Tentativa de saque sem saldo",
            },
            headers=auth_headers,
        )
        assert bad_with.status_code == 400
        assert "funds" in bad_with.json()["message"].lower()

        # Valid deposit (aporte)
        dep_res = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "valor": 5000.00,
                "tipo": "aporte",
                "data": "2026-10-25",
                "observacao": "Economia do bônus",
            },
            headers=auth_headers,
        )
        assert dep_res.status_code == 201
        dep = dep_res.json()
        assert float(dep["amount"]) == 5000.00
        assert dep["type"] == "aporte"
        assert dep["goalId"] == goal_id

        # Valid withdrawal (retirada <= currentAmount)
        with_res = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "valor": 1000.00,
                "tipo": "retirada",
                "data": "2026-10-26",
            },
            headers=auth_headers,
        )
        assert with_res.status_code == 201

        # Check goal progress
        prog_res = await client.get(f"/api/v1/goals/{goal_id}/progress", headers=auth_headers)
        assert prog_res.status_code == 200
        prog = prog_res.json()
        assert prog["goalId"] == goal_id
        assert float(prog["targetAmount"]) == 25000.00
        assert float(prog["currentAmount"]) == 4000.00  # 5000 - 1000
        assert prog["progressPercentage"] == 16.0  # 4000/25000 * 100

        # List contributions
        contribs = await client.get(
            f"/api/v1/goals/{goal_id}/contributions?page=1&size=10", headers=auth_headers
        )
        assert contribs.status_code == 200
        data = contribs.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


class TestSpecReports:
    @pytest.mark.asyncio
    async def test_reports_spec_formats(self, client: AsyncClient, auth_headers):
        # Create an account
        acc = await client.post(
            "/api/v1/accounts",
            json={"nome": "Banco Principal", "tipo": "corrente", "saldo_inicial": "10000.00"},
            headers=auth_headers,
        )
        acc_id = acc.json()["id"]

        # Create income and expense categories
        cat_rec = await client.post(
            "/api/v1/categories",
            json={"nome": "Salário Mensal", "tipo": "receita"},
            headers=auth_headers,
        )
        rec_id = cat_rec.json()["id"]

        cat_desp = await client.post(
            "/api/v1/categories",
            json={"nome": "Aluguel", "tipo": "despesa"},
            headers=auth_headers,
        )
        desp_id = cat_desp.json()["id"]

        # Add confirmed transactions in October 2026
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": acc_id,
                "categoria_id": rec_id,
                "tipo": "receita",
                "valor": "12500.00",
                "data": "2026-10-05",
                "descricao": "Salário Outubro",
                "status": "confirmado",
            },
            headers=auth_headers,
        )

        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": acc_id,
                "categoria_id": desp_id,
                "tipo": "despesa",
                "valor": "2500.00",
                "data": "2026-10-10",
                "descricao": "Aluguel Outubro",
                "status": "confirmado",
            },
            headers=auth_headers,
        )

        # 1. Monthly Summary
        summary_res = await client.get(
            "/api/v1/reports/monthly-summary?month=10&year=2026", headers=auth_headers
        )
        assert summary_res.status_code == 200
        s = summary_res.json()
        assert s["month"] == 10
        assert s["year"] == 2026
        assert float(s["totalIncome"]) == 12500.00
        assert float(s["totalExpenses"]) == 2500.00
        assert float(s["balance"]) == 10000.00

        # 2. Category Spending
        spending_res = await client.get(
            "/api/v1/reports/category-spending?month=10&year=2026", headers=auth_headers
        )
        assert spending_res.status_code == 200
        sp = spending_res.json()
        assert sp["month"] == 10
        assert sp["year"] == 2026
        assert float(sp["total"]) == 2500.00
        assert len(sp["items"]) >= 1
        item = next((i for i in sp["items"] if i["categoryId"] == desp_id), None)
        assert item is not None
        assert item["categoryName"] == "Aluguel"
        assert float(item["amount"]) == 2500.00

        # 3. Balance Evolution (Yearly trend)
        trend_res = await client.get(
            "/api/v1/reports/balance-evolution?ano=2026", headers=auth_headers
        )
        assert trend_res.status_code == 200
        timeline = trend_res.json()
        assert isinstance(timeline, list)
        oct_data = next((m for m in timeline if m["month"] == 10), None)
        assert oct_data is not None
        assert float(oct_data["totalIncome"]) == 12500.00
        assert float(oct_data["totalExpenses"]) == 2500.00
        assert float(oct_data["balance"]) == 10000.00

        # 4. Budget vs Actual
        b_res = await client.post(
            "/api/v1/budgets",
            json={
                "categoria_id": desp_id,
                "valor_limite": 3000.00,
                "mes": 10,
                "ano": 2026,
            },
            headers=auth_headers,
        )
        assert b_res.status_code == 201

        bva_res = await client.get(
            "/api/v1/reports/budget-vs-actual?month=10&year=2026", headers=auth_headers
        )
        assert bva_res.status_code == 200
        bva = bva_res.json()
        assert bva["month"] == 10
        assert bva["year"] == 2026
        item_bva = next((i for i in bva["items"] if i["categoryId"] == desp_id), None)
        assert item_bva is not None
        assert item_bva["categoryName"] == "Aluguel"
        assert float(item_bva["budgeted"]) == 3000.00
        assert float(item_bva["actual"]) == 2500.00
        assert float(item_bva["difference"]) == 500.00
