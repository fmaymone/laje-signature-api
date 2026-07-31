"""Schemas de ingredientes e estoque."""

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

IngredientStockStatus = Literal["in_stock", "low_stock", "out_of_stock", "on_order"]


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=120)
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(default="outro", max_length=80)
    default_unit: IngredientUnit = "g"
    notes: str | None = None


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    aliases: list[str] | None = None
    category: str | None = Field(default=None, max_length=80)
    default_unit: IngredientUnit | None = None
    notes: str | None = None


class IngredientStockPatch(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    unit: IngredientUnit | None = None
    reorder_level: float | None = Field(default=None, ge=0)
    status_override: IngredientStockStatus | None = None
    clear_status_override: bool = False
    notes: str | None = None


class IngredientRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str
    default_unit: str
    notes: str | None = None
    is_system: bool = False
    # Estoque do usuário autenticado (se houver)
    stock_quantity: float = 0
    stock_unit: str | None = None
    reorder_level: float = 0
    status: IngredientStockStatus = "out_of_stock"
    status_override: IngredientStockStatus | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IngredientListResponse(BaseModel):
    items: list[IngredientRead]
    total: int


class IngredientSeedResponse(BaseModel):
    created: int
    skipped: int
    total: int
