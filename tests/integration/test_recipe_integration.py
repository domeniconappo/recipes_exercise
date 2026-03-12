"""
Integration tests for /api/v1/recipes/* routes.

Exercises the full stack: real uvicorn server → FastAPI → service → PostgreSQL.
The server is shared across the session (started once by the auth integration
test module); we reuse the same live_server_url and http_client fixtures.
"""
import httpx
import pytest
import pytest_asyncio

API = "/api/v1/recipes"
AUTH = "/api/v1/auth"


# ---------------------------------------------------------------------------
# Session-scoped server (reuse pattern from auth integration tests)
# ---------------------------------------------------------------------------


def _get_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def recipe_server_url():
    import threading
    import time

    import uvicorn

    from app.main import app

    port = _get_free_port()
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except httpx.ConnectError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest_asyncio.fixture
async def http_client(recipe_server_url):
    """Async HTTP client pointed at the live recipe test server."""
    async with httpx.AsyncClient(base_url=recipe_server_url, timeout=10) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Use a module-level counter for unique emails across the session
_counter = 0


def _unique_email():
    global _counter
    _counter += 1
    return f"int_user_{_counter}@example.com"


async def _register_login(rc, email=None):
    email = email or _unique_email()
    await rc.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Str0ngPass!", "full_name": "Int User"},
    )
    login = (
        await rc.post(f"{AUTH}/login", json={"email": email, "password": "Str0ngPass!"})
    ).json()
    return f"Bearer {login['access_token']}"


RECIPE = {
    "title": "Integration Gratin",
    "instructions": "Layer potatoes. Bake in the oven at 180°C for 45 minutes.",
    "servings": 4,
    "is_vegetarian": True,
    "ingredients": [
        {"name": "potatoes", "quantity": 500, "unit": "grams"},
        {"name": "cream", "quantity": 200, "unit": "ml"},
    ],
}


# ---------------------------------------------------------------------------
# Full CRUD lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRecipeCRUDLifecycle:
    async def test_create_get_update_delete(self, http_client):
        token = await _register_login(http_client)
        headers = {"Authorization": token}

        # Create
        create_resp = await http_client.post(API, json=RECIPE, headers=headers)
        assert create_resp.status_code == 201
        recipe = create_resp.json()
        recipe_id = recipe["id"]
        assert recipe["title"] == "Integration Gratin"
        assert len(recipe["ingredients"]) == 2

        # Get
        get_resp = await http_client.get(f"{API}/{recipe_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == recipe_id

        # Update
        upd_resp = await http_client.put(
            f"{API}/{recipe_id}",
            json={"title": "Updated Gratin", "servings": 6},
            headers=headers,
        )
        assert upd_resp.status_code == 200
        updated = upd_resp.json()
        assert updated["title"] == "Updated Gratin"
        assert updated["servings"] == 6
        assert len(updated["ingredients"]) == 2  # unchanged

        # Delete
        del_resp = await http_client.delete(f"{API}/{recipe_id}", headers=headers)
        assert del_resp.status_code == 204

        # Confirm gone
        assert (await http_client.get(f"{API}/{recipe_id}")).status_code == 404


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRecipeFiltersIntegration:
    async def _seed(self, http_client, token):
        headers = {"Authorization": token}
        recipes = [
            {
                "title": "Veggie Pasta",
                "instructions": "Boil pasta. Add tomato sauce. Finish in the oven.",
                "servings": 2,
                "is_vegetarian": True,
                "ingredients": [{"name": "pasta", "quantity": 200, "unit": "grams"}],
            },
            {
                "title": "Salmon Fillet",
                "instructions": "Season salmon. Pan fry for 4 minutes each side.",
                "servings": 2,
                "is_vegetarian": False,
                "ingredients": [{"name": "salmon", "quantity": 300, "unit": "grams"}],
            },
            {
                "title": "Potato Gratin",
                "instructions": "Layer potatoes. Bake in the oven at 180°C.",
                "servings": 4,
                "is_vegetarian": True,
                "ingredients": [
                    {"name": "potatoes", "quantity": 500, "unit": "grams"},
                    {"name": "cream", "quantity": 200, "unit": "ml"},
                ],
            },
        ]
        for r in recipes:
            resp = await http_client.post(API, json=r, headers=headers)
            assert resp.status_code == 201

    async def test_all_vegetarian(self, http_client):
        """Assignment example: all vegetarian recipes."""
        token = await _register_login(http_client)
        await self._seed(http_client, token)
        resp = await http_client.get(API, params={"vegetarian": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert all(r["is_vegetarian"] for r in data["items"])

    async def test_servings_and_ingredient(self, http_client):
        """Assignment example: serve 4 persons and have 'potatoes'."""
        token = await _register_login(http_client)
        await self._seed(http_client, token)
        resp = await http_client.get(
            API, params={"servings": 4, "include_ingredients": "potatoes"}
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert all(r["servings"] == 4 for r in items)
        assert all(
            any(i["name"] == "potatoes" for i in r["ingredients"]) for r in items
        )

    async def test_exclude_salmon_with_oven_instructions(self, http_client):
        """Assignment example: no 'salmon', 'oven' in instructions."""
        token = await _register_login(http_client)
        await self._seed(http_client, token)
        resp = await http_client.get(
            API,
            params={"exclude_ingredients": "salmon", "instructions_search": "oven"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 2
        for r in items:
            names = [i["name"] for i in r["ingredients"]]
            assert "salmon" not in names
            assert "oven" in r["instructions"].lower()


# ---------------------------------------------------------------------------
# Auth & ownership enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRecipeOwnershipIntegration:
    async def test_other_user_cannot_update(self, http_client):
        token_a = await _register_login(http_client)
        token_b = await _register_login(http_client)

        created = (
            await http_client.post(API, json=RECIPE, headers={"Authorization": token_a})
        ).json()
        resp = await http_client.put(
            f"{API}/{created['id']}",
            json={"title": "Stolen"},
            headers={"Authorization": token_b},
        )
        assert resp.status_code == 403

    async def test_other_user_cannot_delete(self, http_client):
        token_a = await _register_login(http_client)
        token_b = await _register_login(http_client)

        created = (
            await http_client.post(API, json=RECIPE, headers={"Authorization": token_a})
        ).json()
        resp = await http_client.delete(
            f"{API}/{created['id']}",
            headers={"Authorization": token_b},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_create(self, http_client):
        resp = await http_client.post(API, json=RECIPE)
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, http_client):
        resp = await http_client.post(
            API, json=RECIPE, headers={"Authorization": "Bearer totallyinvalidtoken"}
        )
        assert resp.status_code == 401
