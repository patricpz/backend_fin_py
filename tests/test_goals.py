import uuid

import pytest
from httpx import AsyncClient


class TestGoalCreateRead:
    @pytest.mark.asyncio
    async def test_create_goal(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/goals",
            json={
                "nome": "Reserva de Emergência",
                "descricao": "6 meses",
                "valor_alvo": "30000.00",
                "data_alvo": "2027-06-30",
                "categoria": "Financeiro",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Reserva de Emergência"
        assert data["valor_alvo"] == "30000.00"
        assert data["status"] == "em_andamento"
        assert data["valor_atual"] == "0.00"
        assert data["progresso_percentual"] == 0.0

    @pytest.mark.asyncio
    async def test_get_and_list_goal(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/goals", json={"nome": "Viagem", "valor_alvo": "5000.00"}, headers=auth_headers
        )
        goal_id = created.json()["id"]

        detail = await client.get(f"/api/v1/goals/{goal_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == goal_id

        listing = await client.get("/api/v1/goals", headers=auth_headers)
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, client: AsyncClient, auth_headers):
        response = await client.get(f"/api/v1/goals/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["code"] == "GOAL_NOT_FOUND"


class TestGoalContributions:
    @pytest.mark.asyncio
    async def test_add_contribution_and_progress(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/goals",
            json={"nome": "Reserva", "valor_alvo": "10000.00"},
            headers=auth_headers,
        )
        goal_id = created.json()["id"]

        contrib = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "valor": "5000.00",
                "tipo": "aporte",
                "data": "2026-08-22",
                "observacao": "Mensal",
            },
            headers=auth_headers,
        )
        assert contrib.status_code == 201
        assert contrib.json()["tipo"] == "aporte"

        progress = await client.get(f"/api/v1/goals/{goal_id}/progress", headers=auth_headers)
        assert progress.status_code == 200
        data = progress.json()
        assert float(data["valor_atual"]) == 5000.0
        assert data["progresso_percentual"] == 50.0

        contribs_list = await client.get(
            f"/api/v1/goals/{goal_id}/contributions", headers=auth_headers
        )
        assert contribs_list.status_code == 200
        assert contribs_list.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_auto_complete_on_target_reached(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/goals", json={"nome": "Pequena", "valor_alvo": "1000.00"}, headers=auth_headers
        )
        goal_id = created.json()["id"]
        await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={"valor": "1000.00", "tipo": "aporte", "data": "2026-08-22"},
            headers=auth_headers,
        )
        # reaching target marks goal as concluded
        detail = await client.get(f"/api/v1/goals/{goal_id}", headers=auth_headers)
        assert detail.json()["status"] == "concluida"

    @pytest.mark.asyncio
    async def test_contribution_rejected_on_completed_goal(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/goals", json={"nome": "Completa", "valor_alvo": "100.00"}, headers=auth_headers
        )
        goal_id = created.json()["id"]
        await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={"valor": "100.00", "tipo": "aporte", "data": "2026-08-22"},
            headers=auth_headers,
        )
        response = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={"valor": "50.00", "tipo": "aporte", "data": "2026-08-23"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "GOAL_COMPLETED"


class TestGoalUpdateDelete:
    @pytest.mark.asyncio
    async def test_update_and_delete(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/goals", json={"nome": "Meta", "valor_alvo": "500.00"}, headers=auth_headers
        )
        goal_id = created.json()["id"]

        upd = await client.patch(
            f"/api/v1/goals/{goal_id}", json={"nome": "Meta Nova"}, headers=auth_headers
        )
        assert upd.status_code == 200
        assert upd.json()["nome"] == "Meta Nova"

        delete = await client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)
        assert delete.status_code == 204
