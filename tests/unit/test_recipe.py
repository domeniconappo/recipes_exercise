"""
Unit tests for Recipe and Ingredient schemas — no DB, no HTTP.

Tests cover:
- Schema validation (valid and invalid inputs)
- RecipeUpdate partial updates
- RecipeFilterParams defaults and bounds
- RecipeListResponse pagination fields
"""
import pytest
from pydantic import ValidationError

from app.schemas.recipe import (
    IngredientCreate,
    RecipeCreate,
    RecipeFilterParams,
    RecipeListResponse,
    RecipeUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_ingredient(**overrides) -> dict:
    return {"name": "potatoes", "quantity": 500.0, "unit": "grams", **overrides}


def make_recipe(**overrides) -> dict:
    return {
        "title": "Potato Gratin",
        "instructions": "Preheat oven to 180°C. Layer potatoes.",
        "servings": 4,
        "is_vegetarian": True,
        "ingredients": [make_ingredient()],
        **overrides,
    }


# ---------------------------------------------------------------------------
# IngredientCreate
# ---------------------------------------------------------------------------


class TestIngredientCreate:
    def test_valid(self):
        ing = IngredientCreate(**make_ingredient())
        assert ing.name == "potatoes"
        assert ing.quantity == 500.0
        assert ing.unit == "grams"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            IngredientCreate(**make_ingredient(name=""))

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            IngredientCreate(**make_ingredient(quantity=0))

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            IngredientCreate(**make_ingredient(quantity=-1))

    def test_empty_unit_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            IngredientCreate(**make_ingredient(unit=""))

    def test_name_too_long_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            IngredientCreate(**make_ingredient(name="x" * 101))

    def test_unit_too_long_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            IngredientCreate(**make_ingredient(unit="x" * 51))

    def test_float_quantity_accepted(self):
        ing = IngredientCreate(**make_ingredient(quantity=1.5))
        assert ing.quantity == 1.5


# ---------------------------------------------------------------------------
# RecipeCreate
# ---------------------------------------------------------------------------


class TestRecipeCreate:
    def test_valid_minimal(self):
        recipe = RecipeCreate(**make_recipe())
        assert recipe.title == "Potato Gratin"
        assert recipe.servings == 4
        assert recipe.is_vegetarian is True
        assert len(recipe.ingredients) == 1
        assert recipe.description is None

    def test_valid_with_description(self):
        recipe = RecipeCreate(**make_recipe(description="A classic French dish"))
        assert recipe.description == "A classic French dish"

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RecipeCreate(**make_recipe(title=""))

    def test_title_too_long_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            RecipeCreate(**make_recipe(title="x" * 201))

    def test_description_too_long_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            RecipeCreate(**make_recipe(description="x" * 1001))

    def test_empty_instructions_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RecipeCreate(**make_recipe(instructions=""))

    def test_zero_servings_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeCreate(**make_recipe(servings=0))

    def test_negative_servings_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeCreate(**make_recipe(servings=-1))

    def test_empty_ingredients_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RecipeCreate(**make_recipe(ingredients=[]))

    def test_multiple_ingredients_accepted(self):
        recipe = RecipeCreate(
            **make_recipe(
                ingredients=[
                    make_ingredient(name="potatoes"),
                    make_ingredient(name="cream", quantity=200, unit="ml"),
                ]
            )
        )
        assert len(recipe.ingredients) == 2

    def test_non_vegetarian(self):
        recipe = RecipeCreate(**make_recipe(is_vegetarian=False))
        assert recipe.is_vegetarian is False


# ---------------------------------------------------------------------------
# RecipeUpdate
# ---------------------------------------------------------------------------


class TestRecipeUpdate:
    def test_all_fields_optional(self):
        # Empty update is valid — all fields are optional
        update = RecipeUpdate()
        assert update.title is None
        assert update.instructions is None
        assert update.servings is None
        assert update.is_vegetarian is None
        assert update.ingredients is None

    def test_partial_update_title_only(self):
        update = RecipeUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.servings is None

    def test_partial_update_vegetarian_only(self):
        update = RecipeUpdate(is_vegetarian=False)
        assert update.is_vegetarian is False
        assert update.title is None

    def test_partial_update_servings(self):
        update = RecipeUpdate(servings=6)
        assert update.servings == 6

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RecipeUpdate(title="")

    def test_zero_servings_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeUpdate(servings=0)

    def test_empty_ingredients_list_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RecipeUpdate(ingredients=[])

    def test_update_with_ingredients(self):
        update = RecipeUpdate(ingredients=[make_ingredient(name="salmon")])
        assert update.ingredients[0].name == "salmon"


# ---------------------------------------------------------------------------
# RecipeFilterParams
# ---------------------------------------------------------------------------


class TestRecipeFilterParams:
    def test_defaults(self):
        params = RecipeFilterParams()
        assert params.vegetarian is None
        assert params.servings is None
        assert params.include_ingredients is None
        assert params.exclude_ingredients is None
        assert params.instructions_search is None
        assert params.page == 1
        assert params.page_size == 20

    def test_vegetarian_filter(self):
        params = RecipeFilterParams(vegetarian=True)
        assert params.vegetarian is True

    def test_servings_filter(self):
        params = RecipeFilterParams(servings=4)
        assert params.servings == 4

    def test_zero_servings_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeFilterParams(servings=0)

    def test_include_ingredients(self):
        params = RecipeFilterParams(include_ingredients=["potatoes", "cream"])
        assert "potatoes" in params.include_ingredients
        assert "cream" in params.include_ingredients

    def test_exclude_ingredients(self):
        params = RecipeFilterParams(exclude_ingredients=["salmon"])
        assert "salmon" in params.exclude_ingredients

    def test_instructions_search(self):
        params = RecipeFilterParams(instructions_search="oven")
        assert params.instructions_search == "oven"

    def test_page_below_minimum_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeFilterParams(page=0)

    def test_page_size_above_maximum_rejected(self):
        with pytest.raises(ValidationError, match="less than or equal to 100"):
            RecipeFilterParams(page_size=101)

    def test_page_size_below_minimum_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RecipeFilterParams(page_size=0)

    def test_combined_filters(self):
        params = RecipeFilterParams(
            vegetarian=True,
            servings=4,
            include_ingredients=["potatoes"],
            instructions_search="oven",
            page=2,
            page_size=10,
        )
        assert params.vegetarian is True
        assert params.servings == 4
        assert params.include_ingredients == ["potatoes"]
        assert params.instructions_search == "oven"
        assert params.page == 2
        assert params.page_size == 10


# ---------------------------------------------------------------------------
# RecipeListResponse
# ---------------------------------------------------------------------------


class TestRecipeListResponse:
    def test_pagination_fields(self):
        response = RecipeListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            pages=0,
        )
        assert response.total == 0
        assert response.pages == 0

    def test_pages_calculation(self):
        # pages field is just stored, caller is responsible for calculating
        response = RecipeListResponse(
            items=[],
            total=45,
            page=1,
            page_size=20,
            pages=3,
        )
        assert response.pages == 3
        assert response.total == 45
