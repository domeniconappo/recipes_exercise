from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import CurrentUser
from app.schemas.recipe import (
    RecipeCreate,
    RecipeFilterParams,
    RecipeListResponse,
    RecipeResponse,
    RecipeUpdate,
)
from app.services import recipe as recipe_service

router = APIRouter(prefix="/recipes", tags=["Recipes"])

DB = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_recipe_or_404(db: AsyncSession, recipe_id: int):
    recipe = await recipe_service.get_recipe_by_id(db, recipe_id)
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )
    return recipe


def _require_owner(recipe, current_user):
    if recipe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not the recipe owner"
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=RecipeListResponse, summary="List and filter recipes")
async def list_recipes(
    db: DB,
    vegetarian: Optional[bool] = Query(
        default=None, description="Filter by vegetarian status"
    ),
    servings: Optional[int] = Query(
        default=None, ge=1, description="Filter by exact number of servings"
    ),
    include_ingredients: Optional[List[str]] = Query(
        default=None, description="Include recipes with ALL of these ingredients"
    ),
    exclude_ingredients: Optional[List[str]] = Query(
        default=None, description="Exclude recipes with ANY of these ingredients"
    ),
    instructions_search: Optional[str] = Query(
        default=None, description="Case-insensitive text search within instructions"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
) -> RecipeListResponse:
    filters = RecipeFilterParams(
        vegetarian=vegetarian,
        servings=servings,
        include_ingredients=include_ingredients,
        exclude_ingredients=exclude_ingredients,
        instructions_search=instructions_search,
        page=page,
        page_size=page_size,
    )
    return await recipe_service.list_recipes(db, filters)


@router.post(
    "",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recipe",
)
async def create_recipe(
    data: RecipeCreate,
    db: DB,
    current_user: CurrentUser,
) -> RecipeResponse:
    recipe = await recipe_service.create_recipe(db, data, owner_id=current_user.id)
    return recipe


@router.get("/{recipe_id}", response_model=RecipeResponse, summary="Get a recipe by ID")
async def get_recipe(
    recipe_id: int,
    db: DB,
) -> RecipeResponse:
    return await _get_recipe_or_404(db, recipe_id)


@router.put(
    "/{recipe_id}", response_model=RecipeResponse, summary="Update a recipe (partial)"
)
async def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    db: DB,
    current_user: CurrentUser,
) -> RecipeResponse:
    recipe = await _get_recipe_or_404(db, recipe_id)
    _require_owner(recipe, current_user)
    return await recipe_service.update_recipe(db, recipe, data)


@router.delete(
    "/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a recipe"
)
async def delete_recipe(
    recipe_id: int,
    db: DB,
    current_user: CurrentUser,
) -> None:
    recipe = await _get_recipe_or_404(db, recipe_id)
    _require_owner(recipe, current_user)
    await recipe_service.delete_recipe(db, recipe)
