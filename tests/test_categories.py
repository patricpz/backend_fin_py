import uuid

import pytest
from httpx import AsyncClient


class TestCategoryCreate:
    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/categories",
            json={"nome": "Restaurante", "tipo": "despesa", "cor": "#EF4444", "icone": "utensils"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Restaurante"
        assert data["tipo"] == "despesa"
        assert data["categoria_pai_id"] is None

    @pytest.mark.asyncio
    async def test_create_subcategory(self, client: AsyncClient, auth_headers):
        parent = await client.post(
            "/api/v1/categories",
            json={"nome": "Alimentação", "tipo": "despesa"},
            headers=auth_headers,
        )
        parent_id = parent.json()["id"]
        response = await client.post(
            "/api/v1/categories",
            json={"nome": "Fast Food", "tipo": "despesa", "categoria_pai_id": parent_id},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["categoria_pai_id"] == parent_id

    @pytest.mark.asyncio
    async def test_create_subcategory_wrong_type(self, client: AsyncClient, auth_headers):
        parent = await client.post(
            "/api/v1/categories", json={"nome": "Salário", "tipo": "receita"}, headers=auth_headers
        )
        response = await client.post(
            "/api/v1/categories",
            json={"nome": "X", "tipo": "despesa", "categoria_pai_id": parent.json()["id"]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_PARENT_TYPE"


class TestCategoryTree:
    @pytest.mark.asyncio
    async def test_default_categories_created_on_register(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"nome": "Novo", "email": "novo@x.com", "senha": "password123"},
        )
        login = await client.post(
            "/api/v1/auth/login", json={"email": "novo@x.com", "senha": "password123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = await client.get("/api/v1/categories/tree", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10  # 7 despesas + 3 receitas

    @pytest.mark.asyncio
    async def test_tree_nested_structure(self, client: AsyncClient, auth_headers):
        parent = await client.post(
            "/api/v1/categories",
            json={"nome": "Alimentação", "tipo": "despesa"},
            headers=auth_headers,
        )
        parent_id = parent.json()["id"]
        await client.post(
            "/api/v1/categories",
            json={"nome": "Fast Food", "tipo": "despesa", "categoria_pai_id": parent_id},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/categories/tree", headers=auth_headers)
        nodes = response.json()
        parent_node = next(n for n in nodes if n["id"] == parent_id)
        assert len(parent_node["children"]) == 1
        assert parent_node["children"][0]["nome"] == "Fast Food"

    @pytest.mark.asyncio
    async def test_tree_filter_by_type(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/categories", json={"nome": "Extra", "tipo": "despesa"}, headers=auth_headers
        )
        response = await client.get(
            "/api/v1/categories/tree", params={"tipo": "receita"}, headers=auth_headers
        )
        assert all(n["tipo"] == "receita" for n in response.json())


class TestCategoryListUpdateDelete:
    @pytest.mark.asyncio
    async def test_list_categories(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/categories", json={"nome": "A", "tipo": "despesa"}, headers=auth_headers
        )
        response = await client.get("/api/v1/categories", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_update_category(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/categories", json={"nome": "Antigo", "tipo": "despesa"}, headers=auth_headers
        )
        cat_id = created.json()["id"]
        response = await client.patch(
            f"/api/v1/categories/{cat_id}",
            json={"nome": "Novo", "ativo": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["nome"] == "Novo"
        assert response.json()["ativo"] is False

    @pytest.mark.asyncio
    async def test_delete_without_references(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/categories",
            json={"nome": "Temporário", "tipo": "despesa"},
            headers=auth_headers,
        )
        cat_id = created.json()["id"]
        response = await client.delete(f"/api/v1/categories/{cat_id}", headers=auth_headers)
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client: AsyncClient, auth_headers):
        response = await client.delete(f"/api/v1/categories/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["code"] == "CATEGORY_NOT_FOUND"
