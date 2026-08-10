"""Schemas para importação de receita a partir de imagem (print)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from api.schemas_recipes_persist import (
    DEFAULT_LANES,
    MAIN_LANE_ID,
    RecipeIngredientLine,
    RecipeLane,
    RecipeStep,
    _ensure_step_lanes,
)

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


class RecipeImageIngredientLine(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(ge=0, default=0)
    unit: IngredientUnit = "g"
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("nome do ingrediente é obrigatório")
        return text


class RecipeImageImportDraft(BaseModel):
    """Saída estruturada do parser vision (nomes de ingredientes, não UUIDs)."""

    title: str = Field(default="Receita", min_length=1, max_length=200)
    notes: str | None = None
    servings: int = Field(default=4, ge=1, le=200)
    ingredients: list[RecipeImageIngredientLine] = Field(default_factory=list, max_length=200)
    lanes: list[RecipeLane] = Field(default_factory=lambda: [RecipeLane(**DEFAULT_LANES[0])])
    steps: list[RecipeStep] = Field(default_factory=list, max_length=200)
    warnings: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        text = value.strip()
        return text or "Receita"

    @model_validator(mode="after")
    def normalize_lanes_and_steps(self) -> RecipeImageImportDraft:
        lanes = _ensure_step_lanes(self.steps, self.lanes)
        steps = [
            step.model_copy(update={"lane_id": step.lane_id or MAIN_LANE_ID})
            for step in self.steps
        ]
        self.lanes = lanes
        self.steps = steps
        return self


class RecipeImageImportResponse(BaseModel):
    """Payload pronto para POST /v1/recipes + metadados da importação."""

    title: str
    notes: str | None = None
    composition_id: uuid.UUID | None = None
    servings: int = 4
    block_ids: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredientLine] = Field(default_factory=list)
    lanes: list[RecipeLane] = Field(default_factory=lambda: [RecipeLane(**DEFAULT_LANES[0])])
    steps: list[RecipeStep] = Field(default_factory=list)
    created_ingredient_names: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RecipeGenerateFromTextRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Descreva a receita que você quer.")
        return text
