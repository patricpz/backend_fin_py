import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Test User", "email": "new@example.com", "senha": "testpass123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["nome"] == "Test User"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/register",
            json={"nome": "Another", "email": "test@example.com", "senha": "testpass123"},
        )
        assert response.status_code == 409
        assert response.json()["code"] == "EMAIL_EXISTS"

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "senha": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "senha": "wrongpass"},
        )
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, test_user):
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "senha": "testpass123"},
        )
        refresh_token = login.json()["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_me(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers, test_user):
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 204

        from app.core.security import create_refresh_token
        refresh = create_refresh_token({"sub": str(test_user.id)})
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 401