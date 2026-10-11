import uuid
import pytest
from httpx import AsyncClient
from datetime import date
from decimal import Decimal


async def _setup(client, headers):
    """Cria conta + categoria e retorna ids."""
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


def _money(value) -> Decimal:
    return Decimal(str(value))


class TestInstallmentAwareReports:
    @pytest.mark.asyncio
    async def test_monthly_summary_uses_installment_due_dates(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Teste Reports", "email": f"reports-{uuid.uuid4()}@example.com", "senha": "testpass123"},
        )
        assert reg.status_code == 201, reg.text
        user_email = reg.json()["email"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "senha": "testpass123"},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "Content-Type": "application/json",
        }

        account_id, despesa_id, _ = await _setup(client, headers)
        tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "300.00",
                "data": "2026-08-01",
                "descricao": "Despesa parcelada reconhecida por vencimento",
                "status": "confirmado",
            },
            headers=headers,
        )
        tx_id = tx.json()["id"]

        parcelar_resp = await client.post(
            f"/api/v1/transactions/{tx_id}/parcelar",
            json={"numero_parcelas": 3, "data_inicio": "2026-09-10"},
            headers=headers,
        )
        assert parcelar_resp.status_code == 200

        installment_list = await client.get(
            f"/api/v1/transactions/{tx_id}/parcelas",
            headers=headers,
        )
        assert installment_list.status_code == 200
        installments = installment_list.json()
        assert len(installments) == 3

        resp_aug = await client.get(
            "/api/v1/reports/monthly-summary",
            params={"mes": 8, "ano": 2026},
            headers=headers,
        )
        assert resp_aug.status_code == 200
        assert _money(resp_aug.json()["total_despesas"]) == Decimal("0")

        resp_sep = await client.get(
            "/api/v1/reports/monthly-summary",
            params={"mes": 9, "ano": 2026},
            headers=headers,
        )
        assert resp_sep.status_code == 200
        sep_despesas = _money(resp_sep.json()["total_despesas"])

        resp_oct = await client.get(
            "/api/v1/reports/monthly-summary",
            params={"mes": 10, "ano": 2026},
            headers=headers,
        )
        assert resp_oct.status_code == 200
        oct_despesas = _money(resp_oct.json()["total_despesas"])

        expected_by_month = {}
        for inst in installments:
            vencimento = inst["data_vencimento"]
            month = int(vencimento.split("-")[1])
            expected_by_month.setdefault(month, Decimal("0"))
            expected_by_month[month] += Decimal(inst["valor"])

        if 9 in expected_by_month:
            assert sep_despesas == expected_by_month[9]
        if 10 in expected_by_month:
            assert oct_despesas == expected_by_month[10]

    @pytest.mark.asyncio
    async def test_category_spending_uses_installment_due_dates(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Teste Reports", "email": f"reports-{uuid.uuid4()}@example.com", "senha": "testpass123"},
        )
        assert reg.status_code == 201, reg.text
        user_email = reg.json()["email"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "senha": "testpass123"},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "Content-Type": "application/json",
        }

        account_id, despesa_id, _ = await _setup(client, headers)
        tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "600.00",
                "data": "2026-08-01",
                "descricao": "Despesa parcelada por categoria",
                "status": "confirmado",
            },
            headers=headers,
        )
        tx_id = tx.json()["id"]

        await client.post(
            f"/api/v1/transactions/{tx_id}/parcelar",
            json={"numero_parcelas": 3, "data_inicio": "2026-10-05"},
            headers=headers,
        )

        resp = await client.get(
            "/api/v1/reports/category-spending",
            params={"mes": 10, "ano": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        categorias = data["categorias"]

        assert isinstance(categorias, list)
        assert any(c["categoria_nome"] == "Despesa Teste" for c in categorias)

    @pytest.mark.asyncio
    async def test_installment_status_gates_recognition(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Teste Reports", "email": f"reports-{uuid.uuid4()}@example.com", "senha": "testpass123"},
        )
        assert reg.status_code == 201, reg.text
        user_email = reg.json()["email"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "senha": "testpass123"},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "Content-Type": "application/json",
        }

        account_id, despesa_id, _ = await _setup(client, headers)
        tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "400.00",
                "data": "2026-08-01",
                "descricao": "Despesa parcelada com status pendente",
                "status": "confirmado",
            },
            headers=headers,
        )
        tx_id = tx.json()["id"]

        await client.post(
            f"/api/v1/transactions/{tx_id}/parcelar",
            json={"numero_parcelas": 2, "data_inicio": "2026-11-01"},
            headers=headers,
        )

        resp = await client.get(
            "/api/v1/reports/monthly-summary",
            params={"mes": 11, "ano": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        assert _money(resp.json()["total_despesas"]) == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_non_installment_transactions_still_count_by_transaction_date(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Teste Reports", "email": f"reports-{uuid.uuid4()}@example.com", "senha": "testpass123"},
        )
        assert reg.status_code == 201, reg.text
        user_email = reg.json()["email"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "senha": "testpass123"},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "Content-Type": "application/json",
        }

        account_id, despesa_id, _ = await _setup(client, headers)
        tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "150.00",
                "data": "2026-09-15",
                "descricao": "Despesa normal nao parcelada",
                "status": "confirmado",
            },
            headers=headers,
        )
        assert tx.status_code == 201

        resp = await client.get(
            "/api/v1/reports/monthly-summary",
            params={"mes": 9, "ano": 2026},
            headers=headers,
        )
        assert resp.status_code == 200
        assert _money(resp.json()["total_despesas"]) == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_balance_evolution_uses_installment_due_dates(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Teste Reports", "email": f"reports-{uuid.uuid4()}@example.com", "senha": "testpass123"},
        )
        assert reg.status_code == 201, reg.text
        user_email = reg.json()["email"]

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "senha": "testpass123"},
        )
        assert login.status_code == 200, login.text
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "Content-Type": "application/json",
        }

        account_id, despesa_id, _ = await _setup(client, headers)
        tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": account_id,
                "categoria_id": despesa_id,
                "tipo": "despesa",
                "valor": "900.00",
                "data": "2026-08-01",
                "descricao": "Despesa parcelada no saldo",
                "status": "confirmado",
            },
            headers=headers,
        )
        tx_id = tx.json()["id"]

        await client.post(
            f"/api/v1/transactions/{tx_id}/parcelar",
            json={"numero_parcelas": 3, "data_inicio": "2026-12-01"},
            headers=headers,
        )

        balance_resp = await client.get(
            "/api/v1/reports/balance-evolution",
            params={"conta_id": account_id, "mes": 12, "ano": 2026},
            headers=headers,
        )
        if balance_resp.status_code == 200:
            balance_data = balance_resp.json()
            pontos = balance_data["pontos"]

            assert isinstance(pontos, list)
            assert pontos, "balance evolution should have at least one point for the requested period"
            last_point = pontos[-1]
            assert "saldo" in last_point
            assert _money(last_point["saldo"]) == Decimal("400.00")
            assert isinstance(balance_data.get("conta_id"), str) and balance_data["conta_id"]
            assert isinstance(balance_data.get("conta_nome"), str) and balance_data["conta_nome"]
        else:
            assert False, balance_resp.text[:500]
