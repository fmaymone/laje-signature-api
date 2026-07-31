"""Schemas da receita persistida (blocos + passos + ingredientes)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


IngredientUnit = Literal[
    "g",
    "kg",
    "ml",
    "l",
    "un",
    "xicara",
    "colher_sopa",
    "colher_cha",
    "dente",
    "folha",
    "ramo",
    "a_gosto",
]


class RecipeStep(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    process: str = Field(min_length=1, max_length=200)
    description: str | None = None
    time_before_service_minutes: int = Field(default=0, ge=0, le=60 * 24 * 14)
    duration_minutes: int = Field(default=10, ge=1, le=60 * 24)

    @field_validator("process")
    @classmethod
    def strip_process(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("process é obrigatório")
        return text

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def default_duration(cls, value: object) -> object:
        if value is None or value == "":
            return 10
        return value


class RecipeIngredientLine(BaseModel):
    ingredient_id: uuid.UUID
    quantity: float = Field(ge=0)
    unit: IngredientUnit = "g"
    notes: str | None = None


class RecipeCreate(BaseModel):
    title: str = Field(default="Receita", min_length=1, max_length=200)
    notes: str | None = None
    composition_id: uuid.UUID | None = None
    servings: int = Field(default=4, ge=1, le=200)
    block_ids: list[str] = Field(default_factory=list, max_length=100)
    ingredients: list[RecipeIngredientLine] = Field(default_factory=list, max_length=200)
    steps: list[RecipeStep] = Field(default_factory=list, max_length=200)


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    composition_id: uuid.UUID | None = None
    servings: int | None = Field(default=None, ge=1, le=200)
    block_ids: list[str] | None = Field(default=None, max_length=100)
    ingredients: list[RecipeIngredientLine] | None = Field(default=None, max_length=200)
    steps: list[RecipeStep] | None = Field(default=None, max_length=200)


class RecipeRead(BaseModel):
    id: uuid.UUID
    title: str
    notes: str | None = None
    owner_id: uuid.UUID | None = None
    composition_id: uuid.UUID | None = None
    servings: int = 4
    block_ids: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredientLine] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("servings", mode="before")
    @classmethod
    def default_servings(cls, value: object) -> object:
        if value is None:
            return 4
        return value

    @field_validator("ingredients", mode="before")
    @classmethod
    def default_ingredients(cls, value: object) -> object:
        if value is None:
            return []
        return value


class RecipeListResponse(BaseModel):
    items: list[RecipeRead]
    total: int
