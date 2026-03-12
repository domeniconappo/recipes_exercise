"""Integration tests for /api/v1/auth/* routes."""
import pytest

API = "/api/v1/auth"


class TestRegister:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_register_success(self, client):
        resp = await client.post(
            f"{API}/register",
            json={
                "email": "alice@example.com",
                "password": "Str0ngPass!",
                "full_name": "Alice",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "alice@example.com"
        assert body["full_name"] == "Alice"
        assert "id" in body
        assert "hashed_password" not in body

    async def test_register_duplicate_email(self, client):
        payload = {
            "email": "bob@example.com",
            "password": "Str0ngPass!",
            "full_name": "Bob",
        }
        await client.post(f"{API}/register", json=payload)
        resp = await client.post(f"{API}/register", json=payload)
        assert resp.status_code == 409

    async def test_register_short_password(self, client):
        resp = await client.post(
            f"{API}/register",
            json={
                "email": "c@example.com",
                "password": "short",
                "full_name": "C",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            f"{API}/register",
            json={
                "email": "not-an-email",
                "password": "Str0ngPass!",
                "full_name": "D",
            },
        )
        assert resp.status_code == 422


# @pytest.mark.asyncio
class TestLogin:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_login_success(self, client):
        await client.post(
            f"{API}/register",
            json={
                "email": "login@example.com",
                "password": "Str0ngPass!",
                "full_name": "Login User",
            },
        )
        resp = await client.post(
            f"{API}/login",
            json={"email": "login@example.com", "password": "Str0ngPass!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        await client.post(
            f"{API}/register",
            json={
                "email": "wrong@example.com",
                "password": "Str0ngPass!",
                "full_name": "W",
            },
        )
        resp = await client.post(
            f"{API}/login",
            json={"email": "wrong@example.com", "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            f"{API}/login",
            json={"email": "nobody@example.com", "password": "Str0ngPass!"},
        )
        assert resp.status_code == 401


# @pytest.mark.asyncio
class TestRefresh:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_refresh_success(self, client):
        await client.post(
            f"{API}/register",
            json={
                "email": "refresh@example.com",
                "password": "Str0ngPass!",
                "full_name": "R",
            },
        )
        login = (
            await client.post(
                f"{API}/login",
                json={"email": "refresh@example.com", "password": "Str0ngPass!"},
            )
        ).json()

        resp = await client.post(
            f"{API}/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_with_access_token_fails(self, client):
        await client.post(
            f"{API}/register",
            json={
                "email": "bad_refresh@example.com",
                "password": "Str0ngPass!",
                "full_name": "BR",
            },
        )
        login = (
            await client.post(
                f"{API}/login",
                json={"email": "bad_refresh@example.com", "password": "Str0ngPass!"},
            )
        ).json()

        # Passing access token where refresh is expected should fail
        resp = await client.post(
            f"{API}/refresh", json={"refresh_token": login["access_token"]}
        )
        assert resp.status_code == 401


# @pytest.mark.asyncio
class TestMe:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_me_authenticated(self, client):
        await client.post(
            f"{API}/register",
            json={
                "email": "me@example.com",
                "password": "Str0ngPass!",
                "full_name": "Me User",
            },
        )
        login = (
            await client.post(
                f"{API}/login",
                json={"email": "me@example.com", "password": "Str0ngPass!"},
            )
        ).json()

        resp = await client.get(
            f"{API}/me", headers={"Authorization": f"Bearer {login['access_token']}"}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    async def test_me_unauthenticated(self, client):
        resp = await client.get(f"{API}/me")
        assert resp.status_code == 401
