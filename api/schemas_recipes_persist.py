"""Schemas da receita persistida (blocos + passos + ingredientes + linhas)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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

MAIN_LANE_ID = "main"
DEFAULT_LANES = [{"id": MAIN_LANE_ID, "name": "Principal"}]


class RecipeLane(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("id", "name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("campo obrigatório")
        return text


class RecipeStep(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    process: str = Field(min_length=1, max_length=200)
    description: str | None = None
    time_before_service_minutes: int = Field(default=0, ge=0, le=60 * 24 * 14)
    duration_minutes: int = Field(default=10, ge=1, le=60 * 24)
    lane_id: str = Field(default=MAIN_LANE_ID, min_length=1, max_length=120)

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

    @field_validator("lane_id", mode="before")
    @classmethod
    def default_lane_id(cls, value: object) -> object:
        if value is None or value == "":
            return MAIN_LANE_ID
        return value


class RecipeIngredientLine(BaseModel):
    ingredient_id: uuid.UUID
    quantity: float = Field(ge=0)
    unit: IngredientUnit = "g"
    notes: str | None = None


def _normalize_lanes(lanes: list[RecipeLane] | None) -> list[RecipeLane]:
    if not lanes:
        return [RecipeLane(id=MAIN_LANE_ID, name="Principal")]

    seen: set[str] = set()
    result: list[RecipeLane] = []
    has_main = False
    for lane in lanes:
        if lane.id in seen:
            continue
        seen.add(lane.id)
        if lane.id == MAIN_LANE_ID:
            has_main = True
            result.insert(0, RecipeLane(id=MAIN_LANE_ID, name=lane.name or "Principal"))
        else:
            result.append(lane)
    if not has_main:
        result.insert(0, RecipeLane(id=MAIN_LANE_ID, name="Principal"))
    return result


def _ensure_step_lanes(steps: list[RecipeStep], lanes: list[RecipeLane]) -> list[RecipeLane]:
    """Garante lane Principal e cria lanes órfãs referenciadas pelos passos."""
    lanes = _normalize_lanes(lanes)
    by_id = {lane.id: lane for lane in lanes}
    for step in steps:
        lane_id = step.lane_id or MAIN_LANE_ID
        if lane_id not in by_id:
            by_id[lane_id] = RecipeLane(
                id=lane_id,
                name="Principal" if lane_id == MAIN_LANE_ID else f"Linha {len(by_id) + 1}",
            )
    ordered = [by_id[MAIN_LANE_ID]]
    ordered.extend(lane for lid, lane in by_id.items() if lid != MAIN_LANE_ID)
    return ordered


class RecipeCreate(BaseModel):
    title: str = Field(default="Receita", min_length=1, max_length=200)
    notes: str | None = None
    composition_id: uuid.UUID | None = None
    servings: int = Field(default=4, ge=1, le=200)
    block_ids: list[str] = Field(default_factory=list, max_length=100)
    ingredients: list[RecipeIngredientLine] = Field(default_factory=list, max_length=200)
    lanes: list[RecipeLane] = Field(default_factory=lambda: [RecipeLane(**DEFAULT_LANES[0])])
    steps: list[RecipeStep] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def normalize_lanes_and_steps(self) -> RecipeCreate:
        lanes = _ensure_step_lanes(self.steps, self.lanes)
        steps = [
            step.model_copy(update={"lane_id": step.lane_id or MAIN_LANE_ID})
            for step in self.steps
        ]
        self.lanes = lanes
        self.steps = steps
        return self


class RecipeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    composition_id: uuid.UUID | None = None
    servings: int | None = Field(default=None, ge=1, le=200)
    block_ids: list[str] | None = Field(default=None, max_length=100)
    ingredients: list[RecipeIngredientLine] | None = Field(default=None, max_length=200)
    lanes: list[RecipeLane] | None = Field(default=None, max_length=40)
    steps: list[RecipeStep] | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def normalize_lanes_and_steps(self) -> RecipeUpdate:
        if self.lanes is None and self.steps is None:
            return self
        steps = self.steps or []
        lanes = self.lanes if self.lanes is not None else []
        if self.lanes is not None or self.steps is not None:
            # Se só steps vieram, ainda normaliza lane_id nos steps.
            if self.steps is not None:
                self.steps = [
                    step.model_copy(update={"lane_id": step.lane_id or MAIN_LANE_ID})
                    for step in steps
                ]
            if self.lanes is not None:
                self.lanes = _ensure_step_lanes(self.steps or [], lanes)
            elif self.steps is not None:
                # Steps sem lanes no patch: garante lane_id default apenas.
                pass
        return self


class RecipeRead(BaseModel):
    id: uuid.UUID
    title: str
    notes: str | None = None
    owner_id: uuid.UUID | None = None
    composition_id: uuid.UUID | None = None
    servings: int = 4
    block_ids: list[str] = Field(default_factory=list)
    ingredients: list[RecipeIngredientLine] = Field(default_factory=list)
    lanes: list[RecipeLane] = Field(default_factory=lambda: [RecipeLane(**DEFAULT_LANES[0])])
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

    @field_validator("lanes", mode="before")
    @classmethod
    def default_lanes(cls, value: object) -> object:
        if value is None or value == []:
            return list(DEFAULT_LANES)
        return value

    @model_validator(mode="after")
    def backfill_lane_ids(self) -> RecipeRead:
        steps = [
            step.model_copy(update={"lane_id": step.lane_id or MAIN_LANE_ID})
            for step in self.steps
        ]
        self.lanes = _ensure_step_lanes(steps, self.lanes)
        self.steps = steps
        return self


class RecipeListResponse(BaseModel):
    items: list[RecipeRead]
    total: int
