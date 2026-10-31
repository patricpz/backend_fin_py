import uuid
import asyncio
from decimal import Decimal
import pytest
from httpx import AsyncClient
from app.schemas.expense import ExpenseInstallmentResponse


async def _create_user_and_headers(client: AsyncClient, email_prefix: str = "user"):
    email = f"{email_prefix}-{uuid.uuid4()}@teste.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"nome": "Usuário Teste", "email": email, "senha": "password123"},
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "senha": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestExpensesInstallmentsAPI:
    @pytest.mark.asyncio
    async def test_crud_despesa_parcelada_and_contract(self, client: AsyncClient):
        headers = await _create_user_and_headers(client)

        # 1. Criação via POST /expenses/installments
        payload = {
            "description": "Tablet Pro",
            "category": "Eletrônicos",
            "total_amount": 3000.00,
            "installment_count": 10,
            "first_due_date": "2026-09-10",
        }
        res_create = await client.post("/expenses/installments", json=payload, headers=headers)
        assert res_create.status_code == 201, res_create.text
        data = res_create.json()

        # Validação de contrato estrito das chaves retornadas
        expected_keys = {
            "id",
            "description",
            "category",
            "total_amount",
            "installment_count",
            "installment_amount",
            "paid_installments",
            "remaining_installments",
            "progress_percent",
            "paid_amount",
            "remaining_amount",
            "first_due_date",
            "next_due_date",
            "is_completed",
        }
        assert set(data.keys()) == expected_keys

        # Validação dos valores iniciais
        assert data["description"] == "Tablet Pro"
        assert data["category"] == "Eletrônicos"
        assert Decimal(str(data["total_amount"])) == Decimal("3000.00")
        assert data["installment_count"] == 10
        assert Decimal(str(data["installment_amount"])) == Decimal("300.00")
        assert data["paid_installments"] == 0
        assert data["remaining_installments"] == 10
        assert data["progress_percent"] == 0
        assert Decimal(str(data["paid_amount"])) == Decimal("0.00")
        assert Decimal(str(data["remaining_amount"])) == Decimal("3000.00")
        assert data["first_due_date"] == "2026-09-10"
        assert data["next_due_date"] == "2026-09-10"
        assert data["is_completed"] is False

        expense_id = data["id"]

        # 2. Listagem direta sem envelope via GET /expenses/installments
        res_list = await client.get("/expenses/installments", headers=headers)
        assert res_list.status_code == 200
        items = res_list.json()
        assert isinstance(items, list)  # lista direta sem envelope
        assert len(items) == 1
        assert items[0]["id"] == expense_id

        # 3. Pagar primeira parcela via PATCH /expenses/{id}/installments/pay
        res_pay1 = await client.patch(f"/expenses/{expense_id}/installments/pay", headers=headers)
        assert res_pay1.status_code == 200
        pay1_data = res_pay1.json()
        assert pay1_data["paid_installments"] == 1
        assert pay1_data["remaining_installments"] == 9
        assert pay1_data["progress_percent"] == 10
        assert Decimal(str(pay1_data["paid_amount"])) == Decimal("300.00")
        assert Decimal(str(pay1_data["remaining_amount"])) == Decimal("2700.00")
        assert pay1_data["next_due_date"] == "2026-10-10"
        assert pay1_data["is_completed"] is False

        # 4. Correção manual de parcelas pagas via PATCH /expenses/{id}/installments
        res_corr = await client.patch(
            f"/expenses/{expense_id}/installments",
            json={"paid_installments": 9},
            headers=headers,
        )
        assert res_corr.status_code == 200
        corr_data = res_corr.json()
        assert corr_data["paid_installments"] == 9
        assert corr_data["remaining_installments"] == 1
        assert corr_data["progress_percent"] == 90
        assert corr_data["is_completed"] is False

        # 5. Pagar a última parcela (10 de 10)
        res_pay_last = await client.patch(f"/expenses/{expense_id}/installments/pay", headers=headers)
        assert res_pay_last.status_code == 200
        last_data = res_pay_last.json()
        assert last_data["paid_installments"] == 10
        assert last_data["remaining_installments"] == 0
        assert last_data["progress_percent"] == 100
        assert last_data["is_completed"] is True
        assert last_data["next_due_date"] is None
        assert Decimal(str(last_data["paid_amount"])) == Decimal("3000.00")
        assert Decimal(str(last_data["remaining_amount"])) == Decimal("0.00")

        # 6. Tentar pagar parcela adicional em despesa já quitada deve retornar 409
        res_overpay = await client.patch(f"/expenses/{expense_id}/installments/pay", headers=headers)
        assert res_overpay.status_code == 409
        overpay_data = res_overpay.json()
        assert overpay_data["detail"] == "Esta despesa já foi quitada"

        # 7. Listagem sem include_completed não deve retornar a despesa concluída
        res_excl = await client.get("/expenses/installments", headers=headers)
        assert res_excl.status_code == 200
        assert len(res_excl.json()) == 0

        # Listagem com include_completed=true deve retornar
        res_incl = await client.get("/expenses/installments?include_completed=true", headers=headers)
        assert res_incl.status_code == 200
        assert len(res_incl.json()) == 1
        assert res_incl.json()[0]["id"] == expense_id

    @pytest.mark.asyncio
    async def test_validation_errors_and_non_installment(self, client: AsyncClient):
        headers = await _create_user_and_headers(client)

        # 1. Tentativa de enviar paid_installments na criação deve falhar com 422
        res_fail_paid = await client.post(
            "/expenses/installments",
            json={
                "description": "Notebook",
                "total_amount": 2000.00,
                "installment_count": 5,
                "paid_installments": 2,
                "first_due_date": "2026-10-01",
            },
            headers=headers,
        )
        assert res_fail_paid.status_code == 422

        # 2. Correção manual fora do intervalo (ex.: 6 para count 5) deve retornar 422
        res_ok = await client.post(
            "/expenses/installments",
            json={
                "description": "Notebook",
                "total_amount": 2000.00,
                "installment_count": 5,
                "first_due_date": "2026-10-01",
            },
            headers=headers,
        )
        assert res_ok.status_code == 201
        exp_id = res_ok.json()["id"]

        res_out_range = await client.patch(
            f"/expenses/{exp_id}/installments",
            json={"paid_installments": 6},
            headers=headers,
        )
        assert res_out_range.status_code == 422
        assert "paid_installments deve estar entre 0 e 5" in res_out_range.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_isolation(self, client: AsyncClient):
        headers_a = await _create_user_and_headers(client, "user-a")
        headers_b = await _create_user_and_headers(client, "user-b")

        # Usuário A cria uma despesa parcelada
        res_a = await client.post(
            "/expenses/installments",
            json={
                "description": "Despesa Privada A",
                "total_amount": 500.00,
                "installment_count": 2,
                "first_due_date": "2026-10-01",
            },
            headers=headers_a,
        )
        assert res_a.status_code == 201
        exp_a_id = res_a.json()["id"]

        # Usuário B não deve ver na listagem
        res_list_b = await client.get("/expenses/installments", headers=headers_b)
        assert res_list_b.status_code == 200
        assert len(res_list_b.json()) == 0

        # Usuário B não pode pagar nem corrigir despesa de A -> deve retornar 404, nunca 403
        res_pay_b = await client.patch(f"/expenses/{exp_a_id}/installments/pay", headers=headers_b)
        assert res_pay_b.status_code == 404
        assert res_pay_b.json()["detail"] == "Despesa não encontrada"

        res_corr_b = await client.patch(
            f"/expenses/{exp_a_id}/installments",
            json={"paid_installments": 1},
            headers=headers_b,
        )
        assert res_corr_b.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_payments_no_overcounting(self, client: AsyncClient):
        headers = await _create_user_and_headers(client, "user-conc")

        # Cria despesa parcelada de 3 parcelas
        res = await client.post(
            "/expenses/installments",
            json={
                "description": "Curso Online",
                "total_amount": 300.00,
                "installment_count": 3,
                "first_due_date": "2026-10-01",
            },
            headers=headers,
        )
        assert res.status_code == 201
        exp_id = res.json()["id"]

        # Dispara 6 requisições de pagamento simultâneas (mais do que o número de parcelas 3)
        tasks = [client.patch(f"/expenses/{exp_id}/installments/pay", headers=headers) for _ in range(6)]
        results = await asyncio.gather(*tasks)

        status_codes = [r.status_code for r in results]
        # Pelo menos 3 requisições devem ter sido atendidas ou barradas após atingir 3
        # O estado final NUNCA pode ultrapassar 3 parcelas pagas!
        res_final = await client.get("/expenses/installments?include_completed=true", headers=headers)
        assert res_final.status_code == 200
        final_item = res_final.json()[0]
        assert final_item["paid_installments"] <= 3
        assert final_item["is_completed"] is True
