"""
Unit-level route tests for /api/v1/recipes/*.

Uses ASGITransport (no real network) with the test DB injected via
dependency override — fast, deterministic, no uvicorn needed.
"""
import pytest

from app.schemas.auth import UserRegisterRequest
from app.services.auth import build_token_response, register_user

API = "/api/v1/recipes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_token(client, db_override, email="chef@example.com"):
    """Create a user directly via service and return a bearer token."""
    from app.database import get_db
    from app.main import app

    # Pull a db session out of the override
    async for db in app.dependency_overrides[get_db]():
        user = await register_user(
            db,
            UserRegisterRequest(email=email, password="Str0ngPass!", full_name="Chef"),
        )
        tokens = build_token_response(user.id)
        return user, f"Bearer {tokens.access_token}"


def auth_headers(token: str) -> dict:
    return {"Authorization": token}


RECIPE_PAYLOAD = {
    "title": "Potato Gratin",
    "instructions": "Preheat the oven to 180°C. Layer potatoes.",
    "servings": 4,
    "is_vegetarian": True,
    "ingredients": [
        {"name": "potatoes", "quantity": 500, "unit": "grams"},
        {"name": "cream", "quantity": 200, "unit": "ml"},
    ],
}


@pytest.mark.asyncio
class TestCreateRecipe:
    async def test_create_success(self, client):
        _, token = await _register_and_token(client, None)
        resp = await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Potato Gratin"
        assert body["servings"] == 4
        assert body["is_vegetarian"] is True
        assert len(body["ingredients"]) == 2
        assert "id" in body
        assert "created_at" in body

    async def test_create_unauthenticated_returns_401(self, client):
        resp = await client.post(API, json=RECIPE_PAYLOAD)
        assert resp.status_code == 401

    async def test_create_missing_title_returns_422(self, client):
        _, token = await _register_and_token(client, None, email="a@example.com")
        payload = {**RECIPE_PAYLOAD}
        del payload["title"]
        resp = await client.post(API, json=payload, headers=auth_headers(token))
        assert resp.status_code == 422

    async def test_create_empty_ingredients_returns_422(self, client):
        _, token = await _register_and_token(client, None, email="b@example.com")
        resp = await client.post(
            API, json={**RECIPE_PAYLOAD, "ingredients": []}, headers=auth_headers(token)
        )
        assert resp.status_code == 422

    async def test_create_zero_servings_returns_422(self, client):
        _, token = await _register_and_token(client, None, email="c@example.com")
        resp = await client.post(
            API, json={**RECIPE_PAYLOAD, "servings": 0}, headers=auth_headers(token)
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestGetRecipe:
    async def test_get_existing_recipe(self, client):
        _, token = await _register_and_token(client, None, email="d@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.get(f"{API}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent_returns_404(self, client):
        resp = await client.get(f"{API}/99999")
        assert resp.status_code == 404

    async def test_get_does_not_require_auth(self, client):
        _, token = await _register_and_token(client, None, email="e@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        # No auth header
        resp = await client.get(f"{API}/{created['id']}")
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestListRecipes:
    async def _seed(self, client, token):
        recipes = [
            {
                **RECIPE_PAYLOAD,
                "title": "Veggie Pasta",
                "servings": 2,
                "instructions": "Boil pasta. Add sauce. Bake in oven.",
                "ingredients": [{"name": "pasta", "quantity": 200, "unit": "grams"}],
            },
            {
                **RECIPE_PAYLOAD,
                "title": "Salmon Fillet",
                "is_vegetarian": False,
                "servings": 2,
                "instructions": "Pan fry salmon for 4 minutes.",
                "ingredients": [{"name": "salmon", "quantity": 300, "unit": "grams"}],
            },
            {
                **RECIPE_PAYLOAD,
                "title": "Potato Gratin",
                "servings": 4,
                "instructions": "Layer potatoes. Bake in the oven at 180°C.",
                "ingredients": [
                    {"name": "potatoes", "quantity": 500, "unit": "grams"},
                    {"name": "cream", "quantity": 200, "unit": "ml"},
                ],
            },
        ]
        for r in recipes:
            await client.post(API, json=r, headers=auth_headers(token))

    async def test_list_all(self, client):
        _, token = await _register_and_token(client, None, email="list1@example.com")
        await self._seed(client, token)
        resp = await client.get(API)
        assert resp.status_code == 200
        assert resp.json()["total"] == 3

    async def test_filter_vegetarian(self, client):
        _, token = await _register_and_token(client, None, email="list2@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"vegetarian": True})
        assert resp.json()["total"] == 2

    async def test_filter_servings(self, client):
        _, token = await _register_and_token(client, None, email="list3@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"servings": 4})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Potato Gratin"

    async def test_filter_include_ingredient(self, client):
        _, token = await _register_and_token(client, None, email="list4@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"include_ingredients": "potatoes"})
        assert resp.json()["total"] == 1

    async def test_filter_exclude_ingredient(self, client):
        _, token = await _register_and_token(client, None, email="list5@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"exclude_ingredients": "salmon"})
        data = resp.json()
        assert data["total"] == 2
        titles = {r["title"] for r in data["items"]}
        assert "Salmon Fillet" not in titles

    async def test_filter_instructions_search(self, client):
        _, token = await _register_and_token(client, None, email="list6@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"instructions_search": "oven"})
        assert resp.json()["total"] == 2

    async def test_pagination(self, client):
        _, token = await _register_and_token(client, None, email="list7@example.com")
        await self._seed(client, token)
        resp = await client.get(API, params={"page": 1, "page_size": 2})
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["pages"] == 2

    async def test_list_does_not_require_auth(self, client):
        resp = await client.get(API)
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestUpdateRecipe:
    async def test_update_title(self, client):
        _, token = await _register_and_token(client, None, email="upd1@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.put(
            f"{API}/{created['id']}",
            json={"title": "Updated Title"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["servings"] == 4  # unchanged

    async def test_update_ingredients_replaces_all(self, client):
        _, token = await _register_and_token(client, None, email="upd2@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.put(
            f"{API}/{created['id']}",
            json={
                "ingredients": [{"name": "salmon", "quantity": 300, "unit": "grams"}]
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        ingredients = resp.json()["ingredients"]
        assert len(ingredients) == 1
        assert ingredients[0]["name"] == "salmon"

    async def test_update_requires_auth(self, client):
        _, token = await _register_and_token(client, None, email="upd3@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.put(f"{API}/{created['id']}", json={"title": "Hacked"})
        assert resp.status_code == 401

    async def test_update_by_non_owner_returns_403(self, client):
        _, token_owner = await _register_and_token(
            client, None, email="owner@example.com"
        )
        _, token_other = await _register_and_token(
            client, None, email="other@example.com"
        )
        created = (
            await client.post(
                API, json=RECIPE_PAYLOAD, headers=auth_headers(token_owner)
            )
        ).json()

        resp = await client.put(
            f"{API}/{created['id']}",
            json={"title": "Hacked"},
            headers=auth_headers(token_other),
        )
        assert resp.status_code == 403

    async def test_update_nonexistent_returns_404(self, client):
        _, token = await _register_and_token(client, None, email="upd4@example.com")
        resp = await client.put(
            f"{API}/99999", json={"title": "X"}, headers=auth_headers(token)
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteRecipe:
    async def test_delete_success(self, client):
        _, token = await _register_and_token(client, None, email="del1@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.delete(
            f"{API}/{created['id']}", headers=auth_headers(token)
        )
        assert resp.status_code == 204

        get_resp = await client.get(f"{API}/{created['id']}")
        assert get_resp.status_code == 404

    async def test_delete_requires_auth(self, client):
        _, token = await _register_and_token(client, None, email="del2@example.com")
        created = (
            await client.post(API, json=RECIPE_PAYLOAD, headers=auth_headers(token))
        ).json()

        resp = await client.delete(f"{API}/{created['id']}")
        assert resp.status_code == 401

    async def test_delete_by_non_owner_returns_403(self, client):
        _, token_owner = await _register_and_token(
            client, None, email="delowner@example.com"
        )
        _, token_other = await _register_and_token(
            client, None, email="delother@example.com"
        )
        created = (
            await client.post(
                API, json=RECIPE_PAYLOAD, headers=auth_headers(token_owner)
            )
        ).json()

        resp = await client.delete(
            f"{API}/{created['id']}", headers=auth_headers(token_other)
        )
        assert resp.status_code == 403

    async def test_delete_nonexistent_returns_404(self, client):
        _, token = await _register_and_token(client, None, email="del3@example.com")
        resp = await client.delete(f"{API}/99999", headers=auth_headers(token))
        assert resp.status_code == 404
