import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient


async def _criar_setup_financeiro(client: AsyncClient):
    """Cria usuário autenticado, conta corrente e categorias de receita e despesa."""
    email = f"financeiro-{uuid.uuid4()}@teste.com"
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
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Cria conta corrente com saldo zero para testar despesa isolada
    res_conta = await client.post(
        "/api/v1/accounts",
        json={"nome": "Conta Principal", "tipo": "corrente", "saldo_inicial": "0.00"},
        headers=headers,
    )
    assert res_conta.status_code == 201, res_conta.text
    conta_id = res_conta.json()["id"]

    # Cria categorias com nomes únicos
    res_cat_despesa = await client.post(
        "/api/v1/categories",
        json={"nome": f"Despesa-{uuid.uuid4().hex[:6]}", "tipo": "despesa"},
        headers=headers,
    )
    assert res_cat_despesa.status_code == 201, res_cat_despesa.text
    cat_despesa_id = res_cat_despesa.json()["id"]

    res_cat_receita = await client.post(
        "/api/v1/categories",
        json={"nome": f"Receita-{uuid.uuid4().hex[:6]}", "tipo": "receita"},
        headers=headers,
    )
    assert res_cat_receita.status_code == 201, res_cat_receita.text
    cat_receita_id = res_cat_receita.json()["id"]

    return headers, conta_id, cat_despesa_id, cat_receita_id


class TestRelacaoContaTransacaoSaldo:
    @pytest.mark.asyncio
    async def test_despesa_nao_deve_deixar_saldo_positivo(self, client: AsyncClient):
        """
        Garante que quando uma conta tem saldo inicial 0 e uma despesa de R$ 50,
        o saldo resultante seja negativo (-50.00) e NUNCA positivo (+50.00).
        """
        headers, conta_id, cat_despesa_id, _ = await _criar_setup_financeiro(client)

        # Cadastra transação de despesa de R$ 50,00
        res_tx = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_id,
                "categoria_id": cat_despesa_id,
                "tipo": "despesa",
                "valor": "50.00",
                "data": "2026-10-15",
                "descricao": "Lanche da Tarde",
                "status": "confirmado",
            },
            headers=headers,
        )
        assert res_tx.status_code == 201
        tx_data = res_tx.json()

        # Valida que a transação informa tipo explícito e sinal coerente
        assert tx_data["tipo"] == "despesa"
        assert tx_data["type"] == "despesa"
        assert Decimal(str(tx_data["valor"])) == Decimal("50.00")
        assert Decimal(str(tx_data["signed_amount"])) == Decimal("-50.00")
        assert Decimal(str(tx_data["signedAmount"])) == Decimal("-50.00")
        assert Decimal(str(tx_data["amount"])) == Decimal("-50.00")
        assert Decimal(str(tx_data["valor_com_sinal"])) == Decimal("-50.00")

        # Consulta saldo da conta via /accounts/{id}/balance
        res_bal = await client.get(f"/api/v1/accounts/{conta_id}/balance", headers=headers)
        assert res_bal.status_code == 200
        bal_data = res_bal.json()

        # O saldo_atual e o balance DEVEM ser -50.00, jamais +50.00
        assert Decimal(str(bal_data["saldo_atual"])) == Decimal("-50.00")
        assert Decimal(str(bal_data["balance"])) == Decimal("-50.00")

        # Consulta conta individual via GET /accounts/{id}
        res_acc = await client.get(f"/api/v1/accounts/{conta_id}", headers=headers)
        assert res_acc.status_code == 200
        assert Decimal(str(res_acc.json()["saldo_atual"])) == Decimal("-50.00")
        assert Decimal(str(res_acc.json()["balance"])) == Decimal("-50.00")

    @pytest.mark.asyncio
    async def test_calculo_saldo_completo_com_receitas_despesas_e_transferencias(self, client: AsyncClient):
        """
        Valida a fórmula do saldo:
        saldo = saldo_inicial + receitas - despesas - transferências_enviadas + transferências_recebidas.
        Transações pendentes não devem alterar o saldo.
        """
        headers, conta_a_id, cat_despesa_id, cat_receita_id = await _criar_setup_financeiro(client)

        # Atualiza saldo inicial da Conta A para 1000.00
        await client.patch(
            f"/api/v1/accounts/{conta_a_id}",
            json={"saldo_inicial": "1000.00"},
            headers=headers,
        )

        # Cria Conta B com saldo inicial 200.00
        res_conta_b = await client.post(
            "/api/v1/accounts",
            json={"nome": "Conta Poupança", "tipo": "poupanca", "saldo_inicial": "200.00"},
            headers=headers,
        )
        assert res_conta_b.status_code == 201
        conta_b_id = res_conta_b.json()["id"]

        # 1. Receita na Conta A de 500.00 (confirmada) -> Saldo esperado Conta A: 1500.00
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_a_id,
                "categoria_id": cat_receita_id,
                "tipo": "receita",
                "valor": "500.00",
                "data": "2026-10-01",
                "descricao": "Salário",
                "status": "confirmado",
            },
            headers=headers,
        )

        # 2. Despesa na Conta A de 200.00 (confirmada) -> Saldo esperado Conta A: 1300.00
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_a_id,
                "categoria_id": cat_despesa_id,
                "tipo": "despesa",
                "valor": "200.00",
                "data": "2026-10-02",
                "descricao": "Supermercado",
                "status": "confirmado",
            },
            headers=headers,
        )

        # 3. Transferência de Conta A para Conta B de 300.00 (confirmada)
        # -> Saldo esperado Conta A: 1300 - 300 = 1000.00
        # -> Saldo esperado Conta B: 200 + 300 = 500.00
        res_transf = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_a_id,
                "conta_destino_id": conta_b_id,
                "tipo": "transferencia",
                "valor": "300.00",
                "data": "2026-10-03",
                "descricao": "Transferência para Reserva",
                "status": "confirmado",
            },
            headers=headers,
        )
        assert res_transf.status_code == 201
        transf_data = res_transf.json()
        assert transf_data["tipo"] == "transferencia"
        assert transf_data["type"] == "transferencia"

        # 4. Despesa PENDENTE de 900.00 na Conta A (não deve afetar saldo)
        await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_a_id,
                "categoria_id": cat_despesa_id,
                "tipo": "despesa",
                "valor": "900.00",
                "data": "2026-10-04",
                "descricao": "Boleto Pendente",
                "status": "pendente",
            },
            headers=headers,
        )

        # Validação do saldo da Conta A
        bal_a = await client.get(f"/api/v1/accounts/{conta_a_id}/balance", headers=headers)
        assert bal_a.status_code == 200
        assert Decimal(str(bal_a.json()["saldo_atual"])) == Decimal("1000.00")
        assert Decimal(str(bal_a.json()["balance"])) == Decimal("1000.00")

        # Validação do saldo da Conta B
        bal_b = await client.get(f"/api/v1/accounts/{conta_b_id}/balance", headers=headers)
        assert bal_b.status_code == 200
        assert Decimal(str(bal_b.json()["saldo_atual"])) == Decimal("500.00")
        assert Decimal(str(bal_b.json()["balance"])) == Decimal("500.00")

        # Validação de que transferência NÃO conta como receita ou despesa no relatório mensal
        rep_res = await client.get("/api/v1/reports/monthly-summary?mes=10&ano=2026", headers=headers)
        assert rep_res.status_code == 200
        rep = rep_res.json()
        assert Decimal(str(rep["total_receitas"])) == Decimal("500.00")
        assert Decimal(str(rep["total_despesas"])) == Decimal("200.00")
        assert Decimal(str(rep["saldo"])) == Decimal("300.00")  # 500 - 200
        assert Decimal(str(rep["total_transferencias_enviadas"])) == Decimal("300.00")

    @pytest.mark.asyncio
    async def test_transacao_tipos_explicitos_e_sinais_em_todas_operacoes(self, client: AsyncClient):
        """
        Garante que todas as transações retornem campos em português e inglês:
        tipo e type, valor e amount (com sinal adequado ao impacto no balanço).
        """
        headers, conta_id, cat_despesa_id, cat_receita_id = await _criar_setup_financeiro(client)

        # Receita
        r_rec = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_id,
                "categoria_id": cat_receita_id,
                "tipo": "receita",
                "valor": "1200.50",
                "descricao": "Freelance",
            },
            headers=headers,
        )
        assert r_rec.status_code == 201
        d_rec = r_rec.json()
        assert d_rec["tipo"] == "receita"
        assert d_rec["type"] == "receita"
        assert Decimal(str(d_rec["amount"])) == Decimal("1200.50")
        assert Decimal(str(d_rec["signed_amount"])) == Decimal("1200.50")

        # Despesa
        r_desp = await client.post(
            "/api/v1/transactions",
            json={
                "conta_id": conta_id,
                "categoria_id": cat_despesa_id,
                "tipo": "despesa",
                "valor": "350.25",
                "descricao": "Manutenção",
            },
            headers=headers,
        )
        assert r_desp.status_code == 201
        d_desp = r_desp.json()
        assert d_desp["tipo"] == "despesa"
        assert d_desp["type"] == "despesa"
        assert Decimal(str(d_desp["amount"])) == Decimal("-350.25")
        assert Decimal(str(d_desp["signed_amount"])) == Decimal("-350.25")

        # Listagem de transações
        r_list = await client.get("/api/v1/transactions", headers=headers)
        assert r_list.status_code == 200
        items = r_list.json()["items"]
        assert len(items) == 2
        for item in items:
            assert "tipo" in item
            assert "type" in item
            assert item["tipo"] in ("receita", "despesa")
            assert item["type"] in ("receita", "despesa")
            if item["type"] == "despesa":
                assert Decimal(str(item["amount"])) < 0
            elif item["type"] == "receita":
                assert Decimal(str(item["amount"])) > 0
