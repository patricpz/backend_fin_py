import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient):
    """Cria um usuário real via auth, obtém token, cria conta + categoria e retorna (headers, account_id, category_id)."""
    user_email = f"parcelada-{uuid.uuid4()}@example.com"

    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "nome": "Usuario Parcelamento",
            "email": user_email,
            "senha": "password123",
        },
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": user_email,
            "senha": "password123",
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
        json={"nome": "Nubank", "tipo": "corrente", "saldo_inicial": "5000.00"},
        headers=headers,
    )
    assert account.status_code == 201, account.text
    account_id = account.json()["id"]

    resp = await client.post(
        "/api/v1/categories",
        json={"nome": "Eletrônicos", "tipo": "despesa"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    category_id = resp.json()["id"]

    return headers, account_id, category_id


@pytest.mark.asyncio
async def test_create_and_read_despesa_parcelada(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    # Cria despesa parcelada: Tablet 10x de R$ 100,00, com 2 parcelas pagas
    payload = {
        "conta_id": account_id,
        "categoria_id": category_id,
        "tipo": "despesa",
        "valor": "1000.00",
        "data": "2026-08-01",
        "descricao": "Tablet",
        "is_installment": True,
        "installment_count": 10,
        "paid_installments": 2,
        "first_due_date": "2026-09-01",
    }

    create_resp = await client.post("/api/v1/transactions", json=payload, headers=headers)
    assert create_resp.status_code == 201, create_resp.text
    data = create_resp.json()

    # Verifica campos base e de progresso (ex: Tablet 20% 2/10)
    assert data["descricao"] == "Tablet"
    assert data["isInstallment"] is True
    assert data["installmentCount"] == 10
    assert data["paidInstallments"] == 2
    assert data["progressPercent"] == 20
    assert data["installmentDisplay"] == "2/10"
    assert data["progressDisplay"] == "20%"
    assert Decimal(data["installmentAmount"]) == Decimal("100.00")
    assert Decimal(data["paidAmount"]) == Decimal("200.00")
    assert Decimal(data["remainingAmount"]) == Decimal("800.00")
    assert data["remainingInstallments"] == 8
    assert data["nextDueDate"] == "2026-11-01"
    assert data["isCompleted"] is False

    tx_id = data["id"]

    # Consulta por ID (GET /transactions/{id})
    get_resp = await client.get(f"/api/v1/transactions/{tx_id}", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == tx_id
    assert get_data["progressPercent"] == 20
    assert get_data["installmentDisplay"] == "2/10"


@pytest.mark.asyncio
async def test_list_installments_and_filter_completed(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    # 1. Parcelamento ativo (Tablet 2/10)
    await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "1000.00",
            "data": "2026-08-01",
            "descricao": "Tablet",
            "is_installment": True,
            "installment_count": 10,
            "paid_installments": 2,
            "first_due_date": "2026-09-01",
        },
        headers=headers,
    )

    # 2. Parcelamento concluído (Celular 5/5)
    await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "500.00",
            "data": "2026-05-01",
            "descricao": "Celular",
            "is_installment": True,
            "installment_count": 5,
            "paid_installments": 5,
            "first_due_date": "2026-06-01",
        },
        headers=headers,
    )

    # 3. Transação normal não parcelada
    await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "50.00",
            "data": "2026-08-05",
            "descricao": "Almoço",
        },
        headers=headers,
    )

    # Listar apenas parceladas
    list_resp = await client.get("/api/v1/transactions/installments", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 2
    items = list_data["items"]
    assert len(items) == 2
    assert all(item["isInstallment"] is True for item in items)

    # Filtrar parceladas ativas (completed=false)
    active_resp = await client.get("/api/v1/transactions/installments?completed=false", headers=headers)
    assert active_resp.status_code == 200
    active_items = active_resp.json()["items"]
    assert len(active_items) == 1
    assert active_items[0]["descricao"] == "Tablet"
    assert active_items[0]["isCompleted"] is False

    # Filtrar parceladas concluídas (completed=true)
    done_resp = await client.get("/api/v1/transactions/installments?completed=true", headers=headers)
    assert done_resp.status_code == 200
    done_items = done_resp.json()["items"]
    assert len(done_items) == 1
    assert done_items[0]["descricao"] == "Celular"
    assert done_items[0]["isCompleted"] is True


@pytest.mark.asyncio
async def test_pay_installment_single_step_and_custom_step(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "600.00",
            "data": "2026-08-01",
            "descricao": "Notebook",
            "is_installment": True,
            "installment_count": 6,
            "paid_installments": 1,
            "first_due_date": "2026-09-01",
        },
        headers=headers,
    )
    tx_id = create_resp.json()["id"]

    # 1. Pagar próxima parcela sem passar body (avança de 1 para 2)
    pay_resp1 = await client.patch(f"/api/v1/transactions/{tx_id}/pay", json={}, headers=headers)
    assert pay_resp1.status_code == 200
    data1 = pay_resp1.json()
    assert data1["paidInstallments"] == 2
    assert data1["installmentDisplay"] == "2/6"
    assert data1["progressPercent"] == 33
    assert Decimal(data1["paidAmount"]) == Decimal("200.00")
    assert Decimal(data1["remainingAmount"]) == Decimal("400.00")

    # 2. Pagar informando paid_installments direto (ex: atualizar para 5 de 6)
    pay_resp2 = await client.patch(
        f"/api/v1/transactions/{tx_id}/pay",
        json={"paidInstallments": 5},
        headers=headers,
    )
    assert pay_resp2.status_code == 200
    data2 = pay_resp2.json()
    assert data2["paidInstallments"] == 5
    assert data2["installmentDisplay"] == "5/6"
    assert data2["progressPercent"] == 83

    # 3. Pagar última parcela (avança de 5 para 6, quitado 100%)
    pay_resp3 = await client.patch(f"/api/v1/transactions/{tx_id}/pay", json={}, headers=headers)
    assert pay_resp3.status_code == 200
    data3 = pay_resp3.json()
    assert data3["paidInstallments"] == 6
    assert data3["installmentDisplay"] == "6/6"
    assert data3["progressPercent"] == 100
    assert data3["isCompleted"] is True
    assert Decimal(data3["paidAmount"]) == Decimal("600.00")
    assert Decimal(data3["remainingAmount"]) == Decimal("0.00")
    assert data3["remainingInstallments"] == 0
    assert data3["nextDueDate"] is None

    # 4. Tentar pagar quando já quitado deve retornar 409 Conflict
    pay_resp4 = await client.patch(f"/api/v1/transactions/{tx_id}/pay", json={}, headers=headers)
    assert pay_resp4.status_code == 409


@pytest.mark.asyncio
async def test_update_and_delete_installment(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    create_resp = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "1200.00",
            "data": "2026-08-01",
            "descricao": "Monitor Gamer",
            "is_installment": True,
            "installment_count": 12,
            "paid_installments": 0,
            "first_due_date": "2026-09-10",
        },
        headers=headers,
    )
    tx_id = create_resp.json()["id"]

    # Atualiza dados (PATCH /transactions/{id})
    update_resp = await client.patch(
        f"/api/v1/transactions/{tx_id}",
        json={"descricao": "Monitor UltraWide 34", "paid_installments": 3},
        headers=headers,
    )
    assert update_resp.status_code == 200
    up_data = update_resp.json()
    assert up_data["descricao"] == "Monitor UltraWide 34"
    assert up_data["paidInstallments"] == 3
    assert up_data["installmentDisplay"] == "3/12"
    assert up_data["progressPercent"] == 25

    # Deleta a transação (DELETE /transactions/{id})
    del_resp = await client.delete(f"/api/v1/transactions/{tx_id}", headers=headers)
    assert del_resp.status_code == 204

    # Confirma que não existe mais
    check_resp = await client.get(f"/api/v1/transactions/{tx_id}", headers=headers)
    assert check_resp.status_code == 404


@pytest.mark.asyncio
async def test_installments_summary_metrics(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    # Criação de 2 despesas parceladas
    # Item 1: R$ 1000, 10x, 2 pagas -> R$ 200 pago, R$ 800 restante
    await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "1000.00",
            "data": "2026-08-01",
            "descricao": "Tablet",
            "is_installment": True,
            "installment_count": 10,
            "paid_installments": 2,
            "first_due_date": "2026-09-01",
        },
        headers=headers,
    )

    # Item 2: R$ 300, 3x, 3 pagas (concluída) -> R$ 300 pago, R$ 0 restante
    await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "300.00",
            "data": "2026-06-01",
            "descricao": "Fone Bluetooth",
            "is_installment": True,
            "installment_count": 3,
            "paid_installments": 3,
            "first_due_date": "2026-07-01",
        },
        headers=headers,
    )

    summary_resp = await client.get("/api/v1/transactions/installments/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # Total de parcelamentos
    assert summary["totalInstallmentsCount"] == 2
    assert summary["activeCount"] == 1
    assert summary["completedCount"] == 1

    # Valores financeiros
    assert Decimal(summary["totalAmount"]) == Decimal("1300.00")
    assert Decimal(summary["totalPaidAmount"]) == Decimal("500.00")
    assert Decimal(summary["totalRemainingAmount"]) == Decimal("800.00")

    # Contagem de parcelas
    assert summary["totalInstallments"] == 13
    assert summary["totalPaidInstallments"] == 5
    assert summary["totalRemainingInstallments"] == 8

    # Percentual geral
    # 500 / 1300 = 38.46% -> 38%
    assert summary["overallProgressPercent"] == 38

    # Próximo vencimento do item ativo (first_due_date + 2 meses = 2026-11-01)
    assert summary["nextDueDate"] == "2026-11-01"


@pytest.mark.asyncio
async def test_validation_errors_for_installments(client: AsyncClient):
    headers, account_id, category_id = await _setup(client)

    # 1. is_installment com installment_count < 2 deve falhar (422)
    resp1 = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Invalido 1",
            "is_installment": True,
            "installment_count": 1,
            "first_due_date": "2026-09-01",
        },
        headers=headers,
    )
    assert resp1.status_code in (400, 422)

    # 2. is_installment sem first_due_date deve falhar (422)
    resp2 = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": category_id,
            "tipo": "despesa",
            "valor": "100.00",
            "data": "2026-08-01",
            "descricao": "Invalido 2",
            "is_installment": True,
            "installment_count": 3,
        },
        headers=headers,
    )
    assert resp2.status_code in (400, 422)

    # 3. is_installment com tipo 'receita' deve falhar (400 ou 422)
    receita_cat = (
        await client.post(
            "/api/v1/categories",
            json={"nome": "Salario", "tipo": "receita"},
            headers=headers,
        )
    ).json()["id"]

    resp3 = await client.post(
        "/api/v1/transactions",
        json={
            "conta_id": account_id,
            "categoria_id": receita_cat,
            "tipo": "receita",
            "valor": "1000.00",
            "data": "2026-08-01",
            "descricao": "Receita Parcelada",
            "is_installment": True,
            "installment_count": 3,
            "first_due_date": "2026-09-01",
        },
        headers=headers,
    )
    assert resp3.status_code in (400, 422)
