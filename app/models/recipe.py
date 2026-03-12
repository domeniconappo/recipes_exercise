from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field, Relationship, SQLModel


class RecipeIngredient(SQLModel, table=True):
    __tablename__ = "recipe_ingredients"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    recipe_id: int = Field(foreign_key="recipes.id", nullable=False, index=True)
    name: str = Field(max_length=100, nullable=False)
    quantity: float = Field(nullable=False)
    unit: str = Field(max_length=50, nullable=False)

    recipe: Optional["Recipe"] = Relationship(back_populates="ingredients")


class Recipe(SQLModel, table=True):
    __tablename__ = "recipes"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    title: str = Field(max_length=200, nullable=False, index=True)
    description: Optional[str] = Field(default=None, max_length=1000)
    instructions: str = Field(nullable=False)
    servings: int = Field(nullable=False, ge=1)
    is_vegetarian: bool = Field(default=False, nullable=False)
    owner_id: int = Field(foreign_key="users.id", nullable=False, index=True)

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            "created_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            "updated_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    ingredients: List[RecipeIngredient] = Relationship(
        back_populates="recipe",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"},
    )
