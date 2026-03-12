"""
Unit tests for the recipe service module.

These tests exercise the service layer directly against a real database session,
without going through HTTP. This ensures the SQL queries, filters, and data
mutations behave correctly in isolation from the router layer.
"""
import pytest

from app.models.user import User
from app.schemas.recipe import RecipeCreate, RecipeFilterParams, RecipeUpdate
from app.services.auth import hash_password
from app.services.recipe import (
    create_recipe,
    delete_recipe,
    get_recipe_by_id,
    list_recipes,
    update_recipe,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_recipe_data(**overrides) -> RecipeCreate:
    data = {
        "title": "Potato Gratin",
        "instructions": "Preheat the oven to 180°C. Layer potatoes and cream.",
        "servings": 4,
        "is_vegetarian": True,
        "ingredients": [
            {"name": "potatoes", "quantity": 500, "unit": "grams"},
            {"name": "cream", "quantity": 200, "unit": "ml"},
        ],
        **overrides,
    }
    return RecipeCreate(**data)


async def make_user(db_session, email="chef@example.com") -> User:
    user = User(
        email=email,
        full_name="Test Chef",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# get_recipe_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetRecipeById:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_returns_recipe_when_exists(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        found = await get_recipe_by_id(db_session, recipe.id)

        assert found is not None
        assert found.id == recipe.id
        assert found.title == "Potato Gratin"

    async def test_returns_none_when_not_found(self, db_session):
        found = await get_recipe_by_id(db_session, 99999)
        assert found is None


# ---------------------------------------------------------------------------
# create_recipe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateRecipe:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_creates_recipe_with_ingredients(self, db_session):
        user = await make_user(db_session)
        data = make_recipe_data()

        recipe = await create_recipe(db_session, data, owner_id=user.id)

        assert recipe.id is not None
        assert recipe.title == "Potato Gratin"
        assert recipe.servings == 4
        assert recipe.is_vegetarian is True
        assert recipe.owner_id == user.id
        assert len(recipe.ingredients) == 2

    async def test_ingredients_are_persisted_correctly(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        names = {i.name for i in recipe.ingredients}
        assert "potatoes" in names
        assert "cream" in names

    async def test_description_is_optional(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(
            db_session,
            make_recipe_data(description=None),
            owner_id=user.id,
        )
        assert recipe.description is None

    async def test_description_is_stored(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(
            db_session,
            make_recipe_data(description="A classic French dish"),
            owner_id=user.id,
        )
        assert recipe.description == "A classic French dish"

    async def test_non_vegetarian_recipe(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(
            db_session,
            make_recipe_data(is_vegetarian=False),
            owner_id=user.id,
        )
        assert recipe.is_vegetarian is False

    async def test_timestamps_are_set(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        assert recipe.created_at is not None
        assert recipe.updated_at is not None


# ---------------------------------------------------------------------------
# update_recipe
# ---------------------------------------------------------------------------


# @pytest.mark.asyncio
class TestUpdateRecipe:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_update_title(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        updated = await update_recipe(
            db_session, recipe, RecipeUpdate(title="New Title")
        )

        assert updated.title == "New Title"
        assert updated.servings == 4  # unchanged

    async def test_update_servings(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        updated = await update_recipe(db_session, recipe, RecipeUpdate(servings=6))

        assert updated.servings == 6
        assert updated.title == "Potato Gratin"  # unchanged

    async def test_update_vegetarian_flag(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        updated = await update_recipe(
            db_session, recipe, RecipeUpdate(is_vegetarian=False)
        )

        assert updated.is_vegetarian is False

    async def test_update_replaces_all_ingredients(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        new_ingredients = [{"name": "salmon", "quantity": 300, "unit": "grams"}]
        updated = await update_recipe(
            db_session,
            recipe,
            RecipeUpdate(ingredients=new_ingredients),
        )

        assert len(updated.ingredients) == 1
        assert updated.ingredients[0].name == "salmon"

    async def test_update_without_ingredients_keeps_existing(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)

        updated = await update_recipe(
            db_session, recipe, RecipeUpdate(title="New Title")
        )

        assert len(updated.ingredients) == 2  # original ingredients untouched

    async def test_partial_update_only_changes_given_fields(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(
            db_session,
            make_recipe_data(description="Original description"),
            owner_id=user.id,
        )

        updated = await update_recipe(db_session, recipe, RecipeUpdate(servings=8))

        assert updated.servings == 8
        assert updated.description == "Original description"
        assert updated.title == "Potato Gratin"
        assert updated.is_vegetarian is True


# ---------------------------------------------------------------------------
# delete_recipe
# ---------------------------------------------------------------------------


# @pytest.mark.asyncio
class TestDeleteRecipe:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def test_recipe_is_removed(self, db_session):
        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)
        recipe_id = recipe.id

        await delete_recipe(db_session, recipe)

        found = await get_recipe_by_id(db_session, recipe_id)
        assert found is None

    async def test_ingredients_are_deleted_with_recipe(self, db_session):
        from sqlalchemy import select

        from app.models.recipe import RecipeIngredient

        user = await make_user(db_session)
        recipe = await create_recipe(db_session, make_recipe_data(), owner_id=user.id)
        recipe_id = recipe.id

        await delete_recipe(db_session, recipe)

        result = await db_session.execute(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
        )
        assert result.scalars().all() == []


# ---------------------------------------------------------------------------
# list_recipes — filtering
# ---------------------------------------------------------------------------


# @pytest.mark.asyncio
class TestListRecipes:
    pytestmark = pytest.mark.asyncio(loop_scope="session")

    async def _seed(self, db_session) -> User:
        """Seed db_session with a variety of recipes for filter testing."""
        user = await make_user(db_session)

        await create_recipe(
            db_session,
            RecipeCreate(
                title="Veggie Pasta",
                instructions="Boil pasta. Add tomato sauce in the oven.",
                servings=2,
                is_vegetarian=True,
                ingredients=[
                    {"name": "pasta", "quantity": 200, "unit": "grams"},
                    {"name": "tomato", "quantity": 3, "unit": "pieces"},
                ],
            ),
            owner_id=user.id,
        )

        await create_recipe(
            db_session,
            RecipeCreate(
                title="Salmon Fillet",
                instructions="Season salmon. Pan fry for 4 minutes each side.",
                servings=2,
                is_vegetarian=False,
                ingredients=[
                    {"name": "salmon", "quantity": 300, "unit": "grams"},
                    {"name": "lemon", "quantity": 1, "unit": "piece"},
                ],
            ),
            owner_id=user.id,
        )

        await create_recipe(
            db_session,
            RecipeCreate(
                title="Potato Gratin",
                instructions="Layer potatoes. Bake in the oven at 180°C.",
                servings=4,
                is_vegetarian=True,
                ingredients=[
                    {"name": "potatoes", "quantity": 500, "unit": "grams"},
                    {"name": "cream", "quantity": 200, "unit": "ml"},
                ],
            ),
            owner_id=user.id,
        )

        return user

    async def test_returns_all_when_no_filters(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams())
        assert result.total == 3
        assert len(result.items) == 3

    async def test_filter_vegetarian_true(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams(vegetarian=True))
        assert result.total == 2
        assert all(r.is_vegetarian for r in result.items)

    async def test_filter_vegetarian_false(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams(vegetarian=False))
        assert result.total == 1
        assert result.items[0].title == "Salmon Fillet"

    async def test_filter_by_servings(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams(servings=4))
        assert result.total == 1
        assert result.items[0].title == "Potato Gratin"

    async def test_filter_include_ingredient(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session, RecipeFilterParams(include_ingredients=["potatoes"])
        )
        assert result.total == 1
        assert result.items[0].title == "Potato Gratin"

    async def test_filter_include_multiple_ingredients(self, db_session):
        await self._seed(db_session)
        # Only Potato Gratin has both potatoes AND cream
        result = await list_recipes(
            db_session,
            RecipeFilterParams(include_ingredients=["potatoes", "cream"]),
        )
        assert result.total == 1
        assert result.items[0].title == "Potato Gratin"

    async def test_filter_include_ingredient_no_match(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session, RecipeFilterParams(include_ingredients=["truffles"])
        )
        assert result.total == 0

    async def test_filter_exclude_ingredient(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session, RecipeFilterParams(exclude_ingredients=["salmon"])
        )
        assert result.total == 2
        titles = {r.title for r in result.items}
        assert "Salmon Fillet" not in titles

    async def test_filter_exclude_multiple_ingredients(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session,
            RecipeFilterParams(exclude_ingredients=["salmon", "potatoes"]),
        )
        assert result.total == 1
        assert result.items[0].title == "Veggie Pasta"

    async def test_filter_instructions_search(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session, RecipeFilterParams(instructions_search="oven")
        )
        assert result.total == 2
        titles = {r.title for r in result.items}
        assert "Veggie Pasta" in titles
        assert "Potato Gratin" in titles

    async def test_filter_instructions_search_case_insensitive(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(
            db_session, RecipeFilterParams(instructions_search="OVEN")
        )
        assert result.total == 2

    async def test_combined_filters_from_assignment(self, db_session):
        """
        Assignment example: recipes that can serve 4 persons
        and have 'potatoes' as an ingredient.
        """
        await self._seed(db_session)
        result = await list_recipes(
            db_session,
            RecipeFilterParams(servings=4, include_ingredients=["potatoes"]),
        )
        assert result.total == 1
        assert result.items[0].title == "Potato Gratin"

    async def test_combined_filters_exclude_and_instructions(self, db_session):
        """
        Assignment example: recipes without 'salmon' that have 'oven'
        in the instructions.
        """
        await self._seed(db_session)
        result = await list_recipes(
            db_session,
            RecipeFilterParams(
                exclude_ingredients=["salmon"],
                instructions_search="oven",
            ),
        )
        assert result.total == 2
        titles = {r.title for r in result.items}
        assert "Salmon Fillet" not in titles
        assert "Veggie Pasta" in titles
        assert "Potato Gratin" in titles

    async def test_pagination_page_size(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams(page=1, page_size=2))
        assert len(result.items) == 2
        assert result.total == 3
        assert result.pages == 2

    async def test_pagination_second_page(self, db_session):
        await self._seed(db_session)
        result = await list_recipes(db_session, RecipeFilterParams(page=2, page_size=2))
        assert len(result.items) == 1
        assert result.total == 3

    async def test_empty_db_returns_empty_list(self, db_session):
        result = await list_recipes(db_session, RecipeFilterParams())
        assert result.total == 0
        assert result.items == []
        assert result.pages == 0
