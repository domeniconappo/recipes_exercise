from math import ceil
from typing import List, Optional

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe import Recipe, RecipeIngredient
from app.schemas.recipe import (
    RecipeCreate,
    RecipeFilterParams,
    RecipeListResponse,
    RecipeUpdate,
)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

async def get_recipe_by_id(db: AsyncSession, recipe_id: int) -> Optional[Recipe]:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    return result.scalar_one_or_none()


async def list_recipes(
    db: AsyncSession,
    filters: RecipeFilterParams,
) -> RecipeListResponse:
    query = select(Recipe)

    # --- vegetarian filter ---
    if filters.vegetarian is not None:
        query = query.where(Recipe.is_vegetarian == filters.vegetarian)

    # --- servings filter ---
    if filters.servings is not None:
        query = query.where(Recipe.servings == filters.servings)

    # --- include ingredients: recipe must contain ALL of them ---
    if filters.include_ingredients:
        for ingredient_name in filters.include_ingredients:
            query = query.where(
                Recipe.id.in_(
                    select(RecipeIngredient.recipe_id).where(
                        func.lower(RecipeIngredient.name) == ingredient_name.lower()
                    )
                )
            )

    # --- exclude ingredients: recipe must contain NONE of them ---
    if filters.exclude_ingredients:
        query = query.where(
            Recipe.id.not_in(
                select(RecipeIngredient.recipe_id).where(
                    or_(
                        *[
                            func.lower(RecipeIngredient.name) == name.lower()
                            for name in filters.exclude_ingredients
                        ]
                    )
                )
            )
        )

    # --- full-text search in instructions ---
    if filters.instructions_search:
        query = query.where(
            func.lower(Recipe.instructions).contains(
                filters.instructions_search.lower()
            )
        )

    # --- total count before pagination ---
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # --- pagination ---
    offset = (filters.page - 1) * filters.page_size
    query = query.offset(offset).limit(filters.page_size)

    result = await db.execute(query)
    recipes = result.scalars().all()

    return RecipeListResponse(
        items=list(recipes),
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=ceil(total / filters.page_size) if total else 0,
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

async def create_recipe(
    db: AsyncSession,
    data: RecipeCreate,
    owner_id: int,
) -> Recipe:
    recipe = Recipe(
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        servings=data.servings,
        is_vegetarian=data.is_vegetarian,
        owner_id=owner_id,
    )
    db.add(recipe)
    await db.flush()  # get recipe.id without committing

    for ing in data.ingredients:
        db.add(RecipeIngredient(
            recipe_id=recipe.id,
            name=ing.name,
            quantity=ing.quantity,
            unit=ing.unit,
        ))

    await db.commit()
    await db.refresh(recipe)
    return recipe


async def update_recipe(
    db: AsyncSession,
    recipe: Recipe,
    data: RecipeUpdate,
) -> Recipe:
    """Apply partial update to a recipe. Raises ValueError if recipe not found."""
    update_data = data.model_dump(exclude_unset=True)

    # Handle ingredients separately — replace all on update
    new_ingredients = update_data.pop("ingredients", None)

    for field, value in update_data.items():
        setattr(recipe, field, value)

    if new_ingredients is not None:
        # Delete existing via ORM so SQLAlchemy identity map stays consistent
        existing = await db.execute(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
        for ing_obj in existing.scalars().all():
            await db.delete(ing_obj)
        await db.flush()

        for ing in new_ingredients:
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                name=ing["name"],
                quantity=ing["quantity"],
                unit=ing["unit"],
            ))
        await db.flush()

    await db.commit()
    await db.refresh(recipe)
    return recipe


async def delete_recipe(db: AsyncSession, recipe: Recipe) -> None:
    await db.delete(recipe)
    await db.commit()
