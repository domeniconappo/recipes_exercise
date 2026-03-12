from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ingredient schemas
# ---------------------------------------------------------------------------


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["potatoes"])
    quantity: float = Field(gt=0, examples=[500])
    unit: str = Field(min_length=1, max_length=50, examples=["grams"])


class IngredientResponse(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Recipe schemas
# ---------------------------------------------------------------------------


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Potato Gratin"])
    description: Optional[str] = Field(default=None, max_length=1000)
    instructions: str = Field(min_length=1, examples=["Preheat the oven to 180°C..."])
    servings: int = Field(ge=1, examples=[4])
    is_vegetarian: bool = Field(examples=[True])
    ingredients: List[IngredientCreate] = Field(min_length=1)


class RecipeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    instructions: Optional[str] = Field(default=None, min_length=1)
    servings: Optional[int] = Field(default=None, ge=1)
    is_vegetarian: Optional[bool] = None
    ingredients: Optional[List[IngredientCreate]] = Field(default=None, min_length=1)


class RecipeResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    instructions: str
    servings: int
    is_vegetarian: bool
    owner_id: int
    ingredients: List[IngredientResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecipeListResponse(BaseModel):
    items: List[RecipeResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Filter params schema
# ---------------------------------------------------------------------------


class RecipeFilterParams(BaseModel):
    vegetarian: Optional[bool] = None
    servings: Optional[int] = Field(default=None, ge=1)
    include_ingredients: Optional[List[str]] = None
    exclude_ingredients: Optional[List[str]] = None
    instructions_search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
